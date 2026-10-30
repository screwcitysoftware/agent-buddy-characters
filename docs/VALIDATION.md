# Validation

Character validation is executable rather than a hand-maintained snapshot.
Run the same core checks used by CI:

```text
python scripts/build.py
python scripts/build_site.py
python -m unittest discover -s tests -v
python tools/character_pack.py validate dist/scout.acpk
```

The build writes current sizes, whole-file hashes, embedded ACPK hashes, frame
counts, compatibility data, independent versions, and immutable release URLs to
`dist/catalog.json` and `dist/validation.json`. `dist/SHA256SUMS` is published
beside each independently released pack.

CI additionally compiles the pinned Agent Buddy Character Lab native renderer,
loads each generated pack, renders all six runtime modes, rejects blank or
errored frames, and uploads screenshots as visual-review evidence. The publish
workflow compares each affected pack's SHA-256 digest with its current GitHub
release asset. Unchanged packs are never republished.

Physical-device installation is not a release requirement.
