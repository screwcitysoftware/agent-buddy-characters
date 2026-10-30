#!/usr/bin/env python3
"""Build the dependency-free GitHub Pages character gallery."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUTPUT = ROOT / "_site"


def main() -> int:
    catalog_path = DIST / "catalog.json"
    if not catalog_path.is_file():
        raise RuntimeError("Run python scripts/build.py first.")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(ROOT / "site", OUTPUT)
    assets = OUTPUT / "assets"
    assets.mkdir()
    for character in catalog["characters"]:
        source = ROOT / "characters" / character["id"] / character["preview"]
        suffix = source.suffix.lower()
        destination = assets / f"{character['id']}{suffix}"
        shutil.copy2(source, destination)
        character["previewUrl"] = f"assets/{destination.name}"
        character.setdefault(
            "downloadUrl",
            f"https://github.com/{catalog['repository']}/releases/latest/download/{character['file']}",
        )
    (OUTPUT / "catalog.json").write_text(
        json.dumps(catalog, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (OUTPUT / ".nojekyll").write_text("", encoding="ascii")
    print(f"Built Pages site in {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

