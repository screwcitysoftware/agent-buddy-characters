# Contributing

This repository currently accepts maintenance fixes for its existing characters,
build tooling, documentation, and gallery. It is not accepting external character
submissions yet.

## Development checks

Python 3.10 or newer is required. The character build has no third-party Python
dependencies.

```text
python scripts/build.py
python scripts/build_site.py
python -m unittest discover -s tests -v
python tools/character_pack.py validate dist/scout.acpk
```

Generated frame payloads, metadata, and previews are checked in. After running a
build, inspect `git diff` and include intentional generated changes in the same
commit as their source change. Do not commit `build/`, `dist/`, or `_site/`.

Any artwork change must preserve clear provenance and its declared license.

## Character versions

Each `characters/<id>/catalog.json` owns that character's semantic `version` and
`releaseTag`. When a change alters the generated ACPK, bump the version explicitly
and set the tag to `<id>-v<version>`. Do not bump either field for descriptions,
previews, documentation, or other changes that leave the pack bytes unchanged.
Merges to `main` publish changed packs automatically after validation.

