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
counts, and compatibility data to `dist/catalog.json` and
`dist/validation.json`. `dist/SHA256SUMS` is published beside every released
pack.

CI additionally compiles the pinned Agent Buddy Character Lab native renderer,
loads each generated pack, renders all six runtime modes, rejects blank or
errored frames, and uploads screenshots for the required maintainer visual
review.

Physical-device installation is not a release requirement.
