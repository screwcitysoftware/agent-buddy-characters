#!/usr/bin/env python3
"""Plan independent character releases by comparing published pack digests."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = ROOT / "characters"
SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:[.-][0-9A-Za-z.-]+)?")
SHARED_PACK_INPUTS = {
    "scripts/release_plan.py",
    "tools/character_pack.py",
    "tools/sprite_codec.py",
}


def command(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments, cwd=ROOT, check=check, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def changed_ids_from_paths(paths: list[str], known: set[str]) -> list[str]:
    changed = {
        parts[1]
        for value in paths
        if len(parts := Path(value).parts) >= 2 and parts[0] == "characters"
        and parts[1] in known
    }
    if SHARED_PACK_INPUTS.intersection(paths):
        changed.update(known)
    return sorted(changed)


def previous_catalog(base: str, pack_id: str) -> dict[str, object] | None:
    result = command(
        "git", "show", f"{base}:characters/{pack_id}/catalog.json", check=False
    )
    if result.returncode:
        return None
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError(f"Previous catalog for {pack_id} is not an object")
    return value


def release_asset_digest(tag: str, filename: str, *, missing_asset_ok: bool = False) -> str | None:
    result = command("gh", "release", "view", tag, "--json", "assets", check=False)
    if result.returncode:
        return None
    for asset in json.loads(result.stdout).get("assets", []):
        if asset.get("name") == filename:
            digest = asset.get("digest") or ""
            if digest.startswith("sha256:"):
                return digest.removeprefix("sha256:")
            raise ValueError(f"Release {tag} asset {filename} has no SHA-256 digest")
    if missing_asset_ok:
        return None
    raise ValueError(f"Release {tag} does not contain {filename}")


def remote_tag_target(tag: str) -> str | None:
    peeled = command(
        "git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}^{{}}", check=False
    )
    if peeled.returncode == 0 and peeled.stdout.strip():
        return peeled.stdout.split()[0]
    direct = command(
        "git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}", check=False
    )
    return direct.stdout.split()[0] if direct.returncode == 0 and direct.stdout.strip() else None


def evaluate(
    pack_id: str,
    current: dict[str, object],
    previous: dict[str, object] | None,
    current_digest: str,
    previous_digest: str | None,
    proposed_digest: str | None,
) -> dict[str, str] | None:
    version = current.get("version")
    tag = current.get("releaseTag")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValueError(f"{pack_id}: version must be semantic without a v prefix")
    if not isinstance(tag, str) or not tag:
        raise ValueError(f"{pack_id}: releaseTag is required")

    previous_version = previous.get("version") if previous else None
    previous_tag = previous.get("releaseTag") if previous else None
    migration = previous is not None and (previous_version is None or previous_tag is None)
    if migration:
        previous_version, previous_tag = version, tag

    if previous_digest == current_digest:
        if previous and not migration and (version != previous_version or tag != previous_tag):
            raise ValueError(f"{pack_id}: pack is unchanged; do not bump version or releaseTag")
        return None

    expected_tag = f"{pack_id}-v{version}"
    if tag != expected_tag:
        raise ValueError(f"{pack_id}: changed pack must use releaseTag {expected_tag}")
    # A failed planning run can leave the bumped version in the immediately
    # previous commit without ever publishing its tag. Treat that as continued
    # preparation of the same unreleased version. Once a release asset exists,
    # further pack changes still require another version bump.
    if previous and version == previous_version and previous_digest is not None:
        raise ValueError(f"{pack_id}: changed pack requires a new version")
    if proposed_digest is not None:
        if proposed_digest != current_digest:
            raise ValueError(f"{pack_id}: existing release {tag} has different pack bytes")
        return None
    return {"id": pack_id, "version": version, "tag": tag}


def plan(base: str) -> list[dict[str, str]]:
    known = {
        path.name for path in CHARACTERS.iterdir()
        if path.is_dir() and (path / "character.json").is_file()
    }
    paths = command("git", "diff", "--name-only", base, "HEAD").stdout.splitlines()
    changed = changed_ids_from_paths(paths, known)
    if not changed:
        return []

    arguments = [sys.executable, "scripts/build.py"]
    for pack_id in changed:
        arguments.extend(("--character", pack_id))
    subprocess.run(arguments, cwd=ROOT, check=True)

    releases: list[dict[str, str]] = []
    for pack_id in changed:
        current = json.loads((CHARACTERS / pack_id / "catalog.json").read_text(encoding="utf-8"))
        previous = previous_catalog(base, pack_id)
        current_digest = hashlib.sha256((ROOT / "dist" / f"{pack_id}.acpk").read_bytes()).hexdigest()
        previous_tag = previous.get("releaseTag") if previous else None
        if previous is not None and previous_tag is None:
            previous_tag = current.get("releaseTag")
        previous_digest = (
            release_asset_digest(str(previous_tag), f"{pack_id}.acpk")
            if previous_tag else None
        )
        proposed_tag = current.get("releaseTag")
        proposed_digest = (
            release_asset_digest(
                str(proposed_tag), f"{pack_id}.acpk", missing_asset_ok=True
            )
            if proposed_tag and proposed_tag != previous_tag else None
        )
        candidate = evaluate(
            pack_id, current, previous, current_digest, previous_digest, proposed_digest
        )
        if candidate:
            tag_target = remote_tag_target(candidate["tag"])
            head = command("git", "rev-parse", "HEAD").stdout.strip()
            if tag_target and tag_target != head:
                raise ValueError(
                    f"{pack_id}: tag {candidate['tag']} points to a different commit"
                )
            candidate["tagExists"] = "true" if tag_target else "false"
            releases.append(candidate)
    return releases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Git commit before the main-branch push")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    releases = plan(args.base)
    matrix = json.dumps({"include": releases}, separators=(",", ":"))
    result = {"matrix": json.loads(matrix), "hasReleases": bool(releases)}
    print(json.dumps(result, indent=2))
    output = args.github_output or (Path(os.environ["GITHUB_OUTPUT"]) if os.getenv("GITHUB_OUTPUT") else None)
    if output:
        with output.open("a", encoding="utf-8") as stream:
            stream.write(f"matrix={matrix}\n")
            stream.write(f"has_releases={'true' if releases else 'false'}\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Release plan error: {error}", file=sys.stderr)
        raise SystemExit(1)
