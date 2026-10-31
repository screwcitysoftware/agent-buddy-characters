---
name: create-agent-buddy-character
description: Create a new original Agent Buddy character in this repository, including concept-sheet and master artwork, deterministic animation frames, an ACPK pack, gallery integration, and validation. Use when asked to design, add, or implement a new character; do not use for routine edits to an existing character.
---

# Create Agent Buddy Character

Take a character from an approved idea to a reproducible, release-ready repository entry. Preserve the repository's independent-project positioning and the user's creative direction.

## Before implementation

- Read [references/concept-art.md](references/concept-art.md) before generating any artwork.
- Read [references/repository-contract.md](references/repository-contract.md) before creating files or selecting animation states.
- Inspect the current `characters/scout/` implementation for structure and encoding patterns, but do not copy Scout-specific anatomy, coordinates, motion, colors, or identity.
- Confirm the character is original or that the supplied artwork can legally be redistributed under its declared license. Do not imitate a copyrighted character.

## Workflow

1. Turn the brief into a compact identity specification: name and lowercase ID, silhouette, proportions, palette, materials, personality, signature details, and motion cues. Resolve only choices that would materially change the character.
2. Generate and visually inspect a concept sheet. Iterate until identity, proportions, colors, and important details remain consistent across views.
3. Generate an isolated master render using the approved concept sheet as the primary reference. Inspect the actual output at full resolution; require the complete character, true-black background, clean silhouette, and generous animation-safe margins.
4. Create the self-contained character directory, manifests, deterministic generator, validator, source prompts, generated frame payload, contact sheet, and blink sheet. Use character-specific motion and measured feature geometry.
5. Build the character pack and gallery. Inspect the contact sheet, blink progression, static master card, and native-resolution website animation. Fix source or generator defects rather than patching built artifacts.
6. Run every repository validation command in the contract reference. Add focused tests for new character-specific invariants and keep generated outputs current.

## Boundaries

- Use an image-generation or image-editing capability for bitmap concept and master artwork. If none is available, ask for source artwork instead of synthesizing it with drawing code.
- Keep all generation prompts and approved source art under `characters/<id>/assets/source/` so the result is reproducible and auditable.
- Do not modify another character merely to make the new one pass.
- Do not push, merge, publish a release, or change repository visibility unless the user asked for that external action.
- A new character starts at version `1.0.0` with release tag `<id>-v1.0.0`; later pack-byte changes require an explicit version bump.

## Completion

Report the character identity, concept/master assets, pack size and checksum, animation/frame coverage, tests run, visual checks performed, and any validation that still depends on CI or physical hardware.
