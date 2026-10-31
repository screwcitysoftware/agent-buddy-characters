# Concept and master artwork

Use this reference whenever a new character needs visual development.

## Identity brief

Before generating, define the character's:

- name and lowercase filesystem-safe ID;
- species or form, silhouette, proportions, and default pose;
- primary and accent colors with distinctive markings;
- materials and rendering style;
- personality and expression range;
- small-screen signature detail, such as a collar, badge, light, or accessory;
- motions that should communicate working, completion, attention, and directional movement.

Keep the brief original. General style language is acceptable; requests to reproduce a protected character are not.

## Concept sheet

Generate a single high-resolution concept sheet first. It should show consistent full-body views and enough information to build animation:

- front neutral view;
- three-quarter view;
- side view;
- expression or blink studies;
- close detail of important markings, materials, or accessories;
- a coherent palette.

Use a simple neutral presentation with clear separation between views. Do not rely on generated labels for essential information. Reject sheets with cropped anatomy, changing markings, inconsistent accessories, extra limbs, or conflicting proportions.

Store the approved sheet and its exact prompt as:

```text
characters/<id>/assets/source/<id>-concept-sheet.png
characters/<id>/assets/source/<id>-concept-prompt.txt
```

## Master render

Use the approved sheet as the primary visual reference and generate one production master:

- square image, preferably 1024 × 1024 or larger;
- one centered, front-facing character in a neutral readable pose;
- entire silhouette visible with generous black margin on every side;
- pure `#000000` background, without scenery, floor, border, text, watermark, or external cast shadow;
- stable, high-contrast edges that remain legible on a small AMOLED display;
- exact preservation of the approved palette, markings, proportions, and signature detail.

Store the approved master and prompt as:

```text
characters/<id>/assets/source/<id>-master-original.png
characters/<id>/assets/source/<id>-master-prompt.txt
```

Record any supplied-art provenance alongside the source assets and set `artworkLicense` accurately. Generated artwork owned by this project normally uses the repository's CC BY 4.0 artwork license; do not assume that license for third-party input.

Visually inspect both files at full resolution. The master is also the gallery card image, so it must present the complete character without relying on CSS cropping.
