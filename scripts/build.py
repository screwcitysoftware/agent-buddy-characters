#!/usr/bin/env python3
"""Regenerate, package, validate, and catalog every character."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = ROOT / "characters"
BUILD_PACKS = ROOT / "build" / "characters"
DIST = ROOT / "dist"
REPOSITORY = "ScrewCitySoftware/agent-buddy-characters"


def run(*arguments: str) -> None:
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover() -> list[Path]:
    found = [path for path in sorted(CHARACTERS.iterdir())
             if path.is_dir() and (path / "character.json").is_file()]
    if not found:
        raise RuntimeError("No characters were found.")
    return found


def character_record(path: Path, release_version: str) -> dict[str, object]:
    manifest = load_json(path / "character.json")
    catalog = load_json(path / "catalog.json")
    if not isinstance(manifest, dict) or not isinstance(catalog, dict):
        raise ValueError(f"{path.name}: character.json and catalog.json must contain objects")
    pack_id = manifest.get("id")
    if pack_id != path.name:
        raise ValueError(f"{path.name}: manifest id must match the directory name")
    required = {
        "description", "preview", "artworkLicense", "minimumAgentBuddyVersion",
        "testedAgentBuddyVersion", "status",
    }
    missing = sorted(required - catalog.keys())
    if missing:
        raise ValueError(f"{path.name}: catalog.json is missing {', '.join(missing)}")
    preview = path / str(catalog["preview"])
    if not preview.is_file():
        raise ValueError(f"{path.name}: preview does not exist: {catalog['preview']}")
    pack = BUILD_PACKS / f"{pack_id}.acpk"
    if not pack.is_file():
        raise ValueError(f"{path.name}: pack was not produced")
    info = json.loads(subprocess.check_output(
        [sys.executable, "tools/character_pack.py", "validate", str(pack)],
        cwd=ROOT, text=True,
    ))
    filename = pack.name
    record: dict[str, object] = {
        "id": pack_id,
        "name": manifest.get("name"),
        "description": catalog["description"],
        "layout": manifest.get("layout"),
        "artworkLicense": catalog["artworkLicense"],
        "minimumAgentBuddyVersion": catalog["minimumAgentBuddyVersion"],
        "testedAgentBuddyVersion": catalog["testedAgentBuddyVersion"],
        "status": catalog["status"],
        "preview": catalog["preview"],
        "file": filename,
        "bytes": pack.stat().st_size,
        "sha256": sha256(pack),
        "embeddedSha256": info["sha256"],
        "frameCount": info["frame_count"],
    }
    if release_version != "development":
        record["downloadUrl"] = (
            f"https://github.com/{REPOSITORY}/releases/download/"
            f"v{release_version}/{filename}"
        )
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-version", default="development")
    args = parser.parse_args(argv)

    version = args.release_version.removeprefix("v")
    characters = discover()
    for character in characters:
        generator = character / "build.py"
        if not generator.is_file():
            raise ValueError(f"{character.name}: build.py is required")
        run(str(generator.relative_to(ROOT)))

    run("tools/character_pack.py", "build")
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)
    records = [character_record(path, version) for path in characters]
    for record in records:
        source = BUILD_PACKS / str(record["file"])
        shutil.copy2(source, DIST / source.name)

    catalog = {
        "schemaVersion": 1,
        "releaseVersion": version,
        "repository": REPOSITORY,
        "characters": records,
    }
    (DIST / "catalog.json").write_text(
        json.dumps(catalog, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (DIST / "validation.json").write_text(
        json.dumps({"schemaVersion": 1, "characters": records}, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    checksums = "".join(f"{record['sha256']}  {record['file']}\n" for record in records)
    (DIST / "SHA256SUMS").write_text(checksums, encoding="ascii", newline="\n")
    print(f"Built {len(records)} character pack(s) in {DIST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

