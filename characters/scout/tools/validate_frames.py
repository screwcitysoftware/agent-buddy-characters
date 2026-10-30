"""Standard-library validation run by the official Agent Buddy pack builder."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CHARACTER = Path(__file__).resolve().parents[1]
ROOT = CHARACTER.parents[1]
FRAMES = CHARACTER / "frames.bin"
METADATA = CHARACTER / "frames.json"
TRACKS = (
    "right", "left", "up", "down", "up_right", "up_left", "down_right", "down_left",
    "surprise", "working", "complete", "attention", "attention_alternate",
)
TRACK_STEPS = [24, 24, 12, 12, 24, 24, 24, 24, 24, 24, 24, 24, 24]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate(root: Path) -> None:
    data = FRAMES.read_bytes()
    metadata = json.loads(METADATA.read_text())
    if not data or metadata.get("dataBytes") != len(data) or metadata.get("dataSha256") != digest(data):
        raise ValueError("Scout frames.bin does not match frames.json; run python characters/scout/build.py.")
    if metadata.get("directions") != list(TRACKS) or metadata.get("trackSteps") != TRACK_STEPS:
        raise ValueError("Scout metadata does not match Agent Buddy's canonical 13-track model.")
    expected = [(track, step) for track, count in zip(TRACKS, TRACK_STEPS) for step in range(count)]
    actual = [(frame.get("direction"), frame.get("step")) for frame in metadata.get("frames", [])]
    if actual != expected or metadata.get("frameCount") != len(expected):
        raise ValueError("Scout frame table is incomplete or out of order.")
    if metadata.get("width") != 412 or metadata.get("height") != 352:
        raise ValueError("Scout frames must target the 412x352 Agent Buddy canvas.")
    if metadata.get("blinkLevels") != [1.0, 0.75, 0.5, 0.25, 0.0]:
        raise ValueError("Scout must provide all five blink levels.")
    source = metadata.get("source", {})
    source_path = root / source.get("path", "")
    if not source_path.is_file() or digest(source_path.read_bytes()) != source.get("sha256"):
        raise ValueError("Scout's source master differs from the exported payload.")
    generator = metadata.get("generator", {})
    generator_path = root / generator.get("path", "")
    if not generator_path.is_file() or digest(generator_path.read_bytes()) != generator.get("sha256"):
        raise ValueError("Scout's generator differs from the exported payload; regenerate it.")
    partition = 12_451_840
    if len(data) >= partition:
        raise ValueError("Scout frame data exceeds the target character partition.")
    if not 0 < metadata.get("maxPatchPixels", 0) <= 412 * 352:
        raise ValueError("Scout blink patch bounds are invalid.")
    if metadata.get("minimumCanvasMarginPixels", 0) < 8:
        raise ValueError("Scout animation frames do not have an eight-pixel clipping safety margin.")

