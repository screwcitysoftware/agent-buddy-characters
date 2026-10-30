#!/usr/bin/env python3
"""Render every character mode with Agent Buddy's native Character Lab engine."""
from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 412, 466
FRAME_BYTES = WIDTH * HEIGHT * 2
MODES = {
    0: "idle",
    1: "surprise",
    2: "working",
    3: "complete",
    4: "attention",
    5: "sleep",
}


def read_exact(stream, count: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < count:
        chunk = stream.read(count - len(chunks))
        if not chunk:
            raise RuntimeError(f"Character Lab ended after {len(chunks):,} of {count:,} frame bytes")
        chunks.extend(chunk)
    return bytes(chunks)


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    import zlib
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def write_png(path: Path, frame: bytes) -> None:
    import zlib
    rgb = bytearray(WIDTH * HEIGHT * 3)
    for index in range(WIDTH * HEIGHT):
        word = struct.unpack_from("<H", frame, index * 2)[0]
        target = index * 3
        rgb[target] = round(((word >> 11) & 31) * 255 / 31)
        rgb[target + 1] = round(((word >> 5) & 63) * 255 / 63)
        rgb[target + 2] = round((word & 31) * 255 / 31)
    scanlines = b"".join(b"\0" + rgb[row * WIDTH * 3:(row + 1) * WIDTH * 3]
                         for row in range(HEIGHT))
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    path.write_bytes(signature + png_chunk(b"IHDR", ihdr)
                     + png_chunk(b"IDAT", zlib.compress(scanlines, 9))
                     + png_chunk(b"IEND", b""))


def render(process: subprocess.Popen, character: str, requested_mode: int, delta: float) -> tuple[list[str], bytes]:
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(f"{delta} {requested_mode} 1 {character} -1\n".encode("ascii"))
    process.stdin.flush()
    header = process.stdout.readline().decode("utf-8", errors="replace").strip()
    if not header.startswith("OK "):
        raise RuntimeError(f"Character Lab rejected {character}: {header}")
    fields = header.split()
    if int(fields[1]) != FRAME_BYTES:
        raise RuntimeError(f"Character Lab returned an unexpected frame size: {header}")
    return fields, read_exact(process.stdout, FRAME_BYTES)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path, help="Pinned Agent Buddy checkout")
    args = parser.parse_args()
    upstream = args.upstream.resolve()
    executable = upstream / "build" / "character-preview"
    if not executable.is_file():
        raise RuntimeError(f"Character Lab executable does not exist: {executable}")

    upstream_packs = upstream / "build" / "characters"
    for pack in (ROOT / "dist").glob("*.acpk"):
        shutil.copy2(pack, upstream_packs / pack.name)

    characters = sorted(pack.stem for pack in (ROOT / "dist").glob("*.acpk"))
    output = ROOT / "test-results" / "character-lab"
    output.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [str(executable)], cwd=upstream, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, bufsize=0,
    )
    try:
        for character in characters:
            for mode, name in MODES.items():
                fields, frame = render(process, character, mode, 0.0)
                selected = None
                for _ in range(180):
                    visible_mode = int(fields[5])
                    blink = int(fields[4])
                    if visible_mode == mode and (mode != 5 or blink == 4):
                        selected = frame
                        break
                    fields, frame = render(process, character, -1, 1 / 30)
                if selected is None:
                    raise RuntimeError(f"{character}: {name} did not become visible")
                if len(set(selected)) < 8:
                    raise RuntimeError(f"{character}: {name} produced a blank-looking frame")
                write_png(output / f"{character}-{name}.png", selected)
            print(f"Rendered {character}: {', '.join(MODES.values())}")
    finally:
        if process.stdin:
            process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        stderr = process.stderr.read() if process.stderr else b""
        if process.returncode not in (0, None):
            raise RuntimeError(stderr.decode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

