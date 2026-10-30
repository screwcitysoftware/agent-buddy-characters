# Upstream investigation

Investigation was performed against the local `DanWahlin/agent-buddy` clone at commit `c87463a0f07c36ae9efec60ab9a5444d7b97a584` (`main`, release v0.16.2, 2026-10-29).

## Source-of-truth files

- `README.md`: supported hardware, runtime modes, installation workflows, and Character Lab.
- `characters/README.md`: add-on character policy, manifest schema, layouts, partition constraints, and build commands.
- `docs/character-art-notes.md`: canonical track order, image-generation workflow, blink synthesis, and processing guidance.
- `tools/character_pack.py`: exact ACPK v1 binary format and firmware-equivalent validation.
- `tools/sprite_codec.py`: RGB565 word-up zlib decoding.
- `firmware/AgentCompanion/src/CharacterModel.h`: sprite geometry and track step counts.
- `firmware/AgentCompanion/src/CharacterMotion.cpp`: state-to-track behavior and sleep/wake synthesis.
- `firmware/AgentCompanion/src/boards/waveshare_amoled_175/BoardConfig.h`: 1.75-B/-C CO5300 466×466 board target.
- `characters/claude`, `characters/grok`, and `characters/openclaw`: deterministic renderer/exporter examples.

## Verified character model

Every pack has 13 canonical tracks and five blink levels. Base-patch packs have 288 pose records because the up and down tracks use 12 poses; other tracks use 24.

Canonical order:

1. `right` — 24
2. `left` — 24
3. `up` — 12
4. `down` — 12
5. `up_right` — 24
6. `up_left` — 24
7. `down_right` — 24
8. `down_left` — 24
9. `surprise` — 24
10. `working` — 24
11. `complete` — 24
12. `attention` — 24
13. `attention_alternate` — 24

Each pose has an open frame plus blink levels 0.75, 0.5, 0.25, and 0. The logical sprite canvas is 412×352. Pack pixels are big-endian RGB565 compressed as independent zlib streams after a vertical 16-bit word-up predictor.

Frame zero must be byte-identical across all tracks. Surprise pose 23 must also be neutral because the motion engine hands directly from the end of the spring reaction to another track.

## ACPK v1

An ACPK file contains:

- A fixed 256-byte little-endian header beginning with `ACPK`.
- Format version, total length, layout, model dimensions, track counts, motion options, and section offsets.
- A frame table: 48-byte pose records for base-patch or 8-byte blocks for full-frame.
- An optional PNG thumbnail up to 256 KiB.
- Compressed frame data.
- A SHA-256 stored in the header, calculated with the SHA field zeroed.

The exact manifest used by Scout is:

```json
{
  "id": "scout",
  "name": "Scout",
  "layout": "base-patch",
  "frames": "frames.bin",
  "metadata": "frames.json",
  "motionSpeed": 0.92,
  "walk": null,
  "validator": "tools/validate_frames.py"
}
```

The device character partition is 12,451,840 bytes (11.875 MiB). The pack builder validates the model, table bounds, data references, partition size, walk configuration, thumbnail, and embedded SHA-256.

## Runtime modes

Firmware exposes only `Idle`, `Surprise`, `Working`, `Complete`, `Attention`, and `Sleep`.

- Idle uses tracks 0–7 and independent blink timing.
- Surprise uses track 8 as a forward spring and must end neutral.
- Working uses track 9 and occasionally looks away through idle tracks.
- Complete uses track 10 and returns to idle after its hold.
- Attention alternates tracks 11 and 12.
- Sleep reuses the current idle track and drives blink level to fully closed. Waking reverses that transition.

Consequently, Scout does not invent separate Thinking, Waiting, Error, or Waking states.

## Chosen implementation

Scout uses the official base-patch architecture because its photographic 3D master compresses efficiently when quantized poses are reused, while blink differences remain localized. The generator is deterministic and dependency-free:

1. Crop and normalize the approved master render to 240×224.
2. Split the head from the anchored torso with a feathered premultiplied mask, then apply quantized head and body poses independently.
3. Synthesize five blink levels and state-dependent tag illumination.
4. Map the art to the official 412×352 canvas and RGB565 format.
5. Deduplicate and zlib-compress base crops and blink patches.
6. Write official base-patch metadata and payload.
7. Invoke the unmodified upstream ACPK builder and decoder.

This is an add-on pack in a standalone repository. Upstream explicitly recommends keeping non-built-in character sources separate. No Agent Buddy firmware changes are necessary.

