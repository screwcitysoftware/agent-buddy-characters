# Repository character contract

Use this reference while implementing and validating a character.

## Required layout

Create a self-contained directory:

```text
characters/<id>/
  assets/source/                 Approved concept, master, prompts, provenance
  assets/generated/              Prepared master, contact sheet, blink sheet
  tools/validate_frames.py       Character-specific frame checks
  build.py                       Deterministic generator
  character.json                 Upstream pack manifest
  catalog.json                   Gallery and release metadata
  frames.bin                     Generated encoded pixels
  frames.json                    Generated layout and frame metadata
```

Generated payloads and visual review sheets are checked in. `build/`, `dist/`, and `_site/` are not.

## Manifests

`character.json` must use an ID matching the directory, a display name, the `base-patch` layout, `frames.bin`, `frames.json`, a deliberate motion speed, and the validator path.

`catalog.json` must contain:

- `description`;
- semantic `version`, initially `1.0.0`;
- `releaseTag`, initially `<id>-v1.0.0`;
- `preview` pointing to the approved master;
- accurate `artworkLicense`;
- `minimumAgentBuddyVersion` and `testedAgentBuddyVersion` based on the pinned upstream version;
- `status`;
- `websiteAnimationTrack` for a representative live preview, normally `working`.

## Generator invariants

- Produce `412 × 352` RGB565 frames using the repository's base-patch encoding.
- Provide the runtime's directional and mode tracks. Use `characters/scout/frames.json` and `docs/INVESTIGATION.md` to confirm current names, ordering, and metadata rather than relying on memory.
- Provide five blink levels: `1.0`, `0.75`, `0.5`, `0.25`, and `0.0`.
- Measure eyes and articulated features on the prepared master. Feature masks must fit the visible anatomy; never reuse Scout's coordinates.
- Preserve at least eight black pixels of animation-safe canvas margin in every rendered state.
- Keep source and generator SHA-256 hashes in generated metadata.
- Build deterministically: unchanged inputs must produce unchanged `frames.bin`, `frames.json`, previews, and ACPK bytes.
- Generate contact and blink sheets that make cropping, identity drift, oversized masks, and broken states easy to see.

Prefer subtle transforms of the approved master over separately generated animation frames; this maintains identity and reproducibility. Character-specific motion is expected, but the pack must remain below the upstream partition limit.

## Website integration

The root build discovers valid character directories automatically. The gallery card uses the source master and must show the complete character with `object-fit: contain`. The dedicated device preview uses the first catalog character with animation metadata and renders its sprite at the native `412 × 352` source resolution. Keep animation metadata generic so a future selector can swap characters without changing the player.

## Validation

Run, at minimum:

```text
python scripts/build.py --character <id>
python scripts/build.py
python scripts/build_site.py
python -m unittest discover -s tests -v
python tools/character_pack.py validate dist/<id>.acpk
python characters/<id>/tools/validate_frames.py
node --check site/app.js
git diff --check
```

Inspect the concept sheet, master, generated contact sheet, blink sheet, and full-resolution web sprite. Confirm the card contains the complete character and the device preview does not upscale a reduced source.

CI additionally compiles the pinned native Character Lab renderer, exercises all runtime modes, and uploads screenshots. Treat that as required release evidence. Physical-device testing is optional unless the user requests it.

If pack bytes change after a release, bump `version` and use `<id>-v<version>`. Do not bump for website-only or descriptive changes that leave the ACPK unchanged.
