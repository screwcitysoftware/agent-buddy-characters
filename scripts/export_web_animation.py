#!/usr/bin/env python3
"""Export a compact web sprite sheet from a generated character payload."""
from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import sprite_codec

FRAME_WIDTH = 206
FRAME_HEIGHT = 176
COLUMNS = 5
FPS = 8


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def png(width: int, height: int, rgb: bytes) -> bytes:
    rows = b"".join(b"\0" + rgb[y * width * 3:(y + 1) * width * 3] for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(rows, 9)) + png_chunk(b"IEND", b""))


def decode_frame(metadata: dict, data: bytes, frame: dict, blink: int = 0) -> bytes:
    base = frame["base"]
    canvas = bytearray(sprite_codec.decode_base(
        data[base["offset"]:base["offset"] + base["size"]], metadata
    ))
    if blink:
        block = frame["blinks"][blink - 1]
        width, height = frame["patchWidth"], frame["patchHeight"]
        patch = sprite_codec.decode_pixels(
            data[block["offset"]:block["offset"] + block["size"]], width
        )
        if len(patch) != width * height * 2:
            raise ValueError("Blink patch dimensions do not match its decoded bytes")
        for row in range(height):
            target = ((frame["patchY"] + row) * metadata["width"] + frame["patchX"]) * 2
            source = row * width * 2
            canvas[target:target + width * 2] = patch[source:source + width * 2]
    return bytes(canvas)


def downsample_rgb565(raw: bytes, width: int, height: int) -> bytes:
    if width != FRAME_WIDTH * 2 or height != FRAME_HEIGHT * 2:
        raise ValueError(f"Web animation exporter expects {FRAME_WIDTH * 2}x{FRAME_HEIGHT * 2} frames")
    output = bytearray(FRAME_WIDTH * FRAME_HEIGHT * 3)
    for y in range(FRAME_HEIGHT):
        for x in range(FRAME_WIDTH):
            red = green = blue = 0
            for dy in range(2):
                for dx in range(2):
                    index = (((y * 2 + dy) * width + x * 2 + dx) * 2)
                    value = raw[index] << 8 | raw[index + 1]
                    red += ((value >> 11) & 31) * 255 // 31
                    green += ((value >> 5) & 63) * 255 // 63
                    blue += (value & 31) * 255 // 31
            target = (y * FRAME_WIDTH + x) * 3
            output[target:target + 3] = bytes((red // 4, green // 4, blue // 4))
    return bytes(output)


def export(character_dir: Path, track: str, destination: Path) -> dict[str, int | str]:
    manifest = json.loads((character_dir / "character.json").read_text(encoding="utf-8"))
    metadata = json.loads((character_dir / manifest["metadata"]).read_text(encoding="utf-8"))
    if metadata.get("layout") != "base-patch":
        raise ValueError(f"{character_dir.name}: web animation requires base-patch layout")
    data = (character_dir / manifest["frames"]).read_bytes()
    frames = [frame for frame in metadata["frames"] if frame["direction"] == track]
    if len(frames) < 24:
        raise ValueError(f"{character_dir.name}: track {track!r} needs at least 24 frames")

    motion_steps = (0, 4, 8, 12, 16, 20, 23, 20, 16, 12, 8, 4, 0)
    sequence = [(frames[step], 0) for step in motion_steps]
    sequence.extend((frames[0], blink) for blink in (1, 2, 3, 4, 3, 2, 1))
    rendered = [
        downsample_rgb565(decode_frame(metadata, data, frame, blink), metadata["width"], metadata["height"])
        for frame, blink in sequence
    ]
    rows = (len(rendered) + COLUMNS - 1) // COLUMNS
    sheet_width, sheet_height = COLUMNS * FRAME_WIDTH, rows * FRAME_HEIGHT
    sheet = bytearray(sheet_width * sheet_height * 3)
    for index, frame in enumerate(rendered):
        column, row = index % COLUMNS, index // COLUMNS
        for y in range(FRAME_HEIGHT):
            source = y * FRAME_WIDTH * 3
            target = ((row * FRAME_HEIGHT + y) * sheet_width + column * FRAME_WIDTH) * 3
            sheet[target:target + FRAME_WIDTH * 3] = frame[source:source + FRAME_WIDTH * 3]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(png(sheet_width, sheet_height, sheet))
    return {
        "sheetUrl": f"assets/{destination.name}",
        "frameWidth": FRAME_WIDTH,
        "frameHeight": FRAME_HEIGHT,
        "columns": COLUMNS,
        "frameCount": len(rendered),
        "fps": FPS,
        "track": track,
    }


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("usage: export_web_animation.py CHARACTER_DIR TRACK OUTPUT.png")
    result = export(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
