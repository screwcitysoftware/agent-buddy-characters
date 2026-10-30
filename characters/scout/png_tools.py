"""Small dependency-free PNG reader/writer used by Scout's reproducible build."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def read_png(path: str | Path) -> tuple[int, int, bytearray]:
    data = Path(path).read_bytes()
    if not data.startswith(SIGNATURE):
        raise ValueError(f"Not a PNG: {path}")
    position = len(SIGNATURE)
    width = height = color_type = None
    compressed = bytearray()
    while position < len(data):
        length = struct.unpack_from(">I", data, position)[0]
        kind = data[position + 4:position + 8]
        body = data[position + 8:position + 8 + length]
        position += 12 + length
        if kind == b"IHDR":
            width, height, depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", body
            )
            if depth != 8 or color_type not in (2, 6) or compression or filtering or interlace:
                raise ValueError("Scout sources must be non-interlaced 8-bit RGB/RGBA PNG files.")
        elif kind == b"IDAT":
            compressed.extend(body)
        elif kind == b"IEND":
            break
    if width is None or height is None:
        raise ValueError("PNG is missing IHDR.")
    channels = 3 if color_type == 2 else 4
    stride = width * channels
    raw = zlib.decompress(compressed)
    if len(raw) != height * (stride + 1):
        raise ValueError("PNG scanline size is invalid.")
    decoded = bytearray(height * stride)
    source = 0
    for y in range(height):
        filter_type = raw[source]
        source += 1
        row = raw[source:source + stride]
        source += stride
        target = y * stride
        for x, value in enumerate(row):
            left = decoded[target + x - channels] if x >= channels else 0
            above = decoded[target + x - stride] if y else 0
            upper_left = decoded[target + x - stride - channels] if y and x >= channels else 0
            if filter_type == 0:
                decoded[target + x] = value
            elif filter_type == 1:
                decoded[target + x] = (value + left) & 255
            elif filter_type == 2:
                decoded[target + x] = (value + above) & 255
            elif filter_type == 3:
                decoded[target + x] = (value + ((left + above) >> 1)) & 255
            elif filter_type == 4:
                decoded[target + x] = (value + _paeth(left, above, upper_left)) & 255
            else:
                raise ValueError(f"Unsupported PNG filter {filter_type}.")
    if channels == 3:
        return width, height, decoded
    rgb = bytearray(width * height * 3)
    for pixel in range(width * height):
        alpha = decoded[pixel * 4 + 3]
        for channel in range(3):
            rgb[pixel * 3 + channel] = decoded[pixel * 4 + channel] * alpha // 255
    return width, height, rgb


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(
        ">I", zlib.crc32(kind + body) & 0xFFFFFFFF
    )


def png_bytes(width: int, height: int, rgb: bytes) -> bytes:
    if len(rgb) != width * height * 3:
        raise ValueError("RGB byte count does not match PNG dimensions.")
    rows = bytearray()
    stride = width * 3
    for y in range(height):
        rows.append(0)
        rows.extend(rgb[y * stride:(y + 1) * stride])
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return SIGNATURE + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(rows, 9)) + _chunk(b"IEND", b"")


def write_png(path: str | Path, width: int, height: int, rgb: bytes) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(png_bytes(width, height, rgb))

