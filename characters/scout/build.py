#!/usr/bin/env python3
"""Generate Scout's deterministic animation payload from one approved master render."""
from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

CHARACTER = Path(__file__).resolve().parent
ROOT = CHARACTER.parents[1]
sys.path.insert(0, str(CHARACTER))
from png_tools import read_png, write_png

SOURCE = CHARACTER / "assets/source/scout-master-original.png"
PREPARED = CHARACTER / "assets/generated/scout-master-240x224.png"
CONTACT = CHARACTER / "assets/generated/scout-contact-sheet.png"
BLINK_CONTACT = CHARACTER / "assets/generated/scout-blinks.png"
FRAMES = CHARACTER / "frames.bin"
METADATA = CHARACTER / "frames.json"

SOURCE_WIDTH, SOURCE_HEIGHT = 240, 224
WIDTH, HEIGHT = 412, 352
TRACKS = (
    "right", "left", "up", "down", "up_right", "up_left", "down_right", "down_left",
    "surprise", "working", "complete", "attention", "attention_alternate",
)
TRACK_STEPS = (24, 24, 12, 12, 24, 24, 24, 24, 24, 24, 24, 24, 24)
BLINKS = (1.0, 0.75, 0.5, 0.25, 0.0)
FRAME_RECORD_BYTES = 48


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_if_changed(path: Path, data: bytes | str) -> None:
    if isinstance(data, str):
        data = data.encode("utf-8")
    if not path.exists() or path.read_bytes() != data:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def pixel(rgb: bytes, width: int, x: int, y: int) -> tuple[int, int, int]:
    index = (y * width + x) * 3
    return rgb[index], rgb[index + 1], rgb[index + 2]


def resize_bilinear(rgb: bytes, width: int, height: int, out_width: int, out_height: int) -> bytearray:
    output = bytearray(out_width * out_height * 3)
    for y in range(out_height):
        sy = (y + 0.5) * height / out_height - 0.5
        y0 = max(0, min(height - 1, int(math.floor(sy))))
        y1 = min(height - 1, y0 + 1)
        fy = max(0.0, sy - y0)
        for x in range(out_width):
            sx = (x + 0.5) * width / out_width - 0.5
            x0 = max(0, min(width - 1, int(math.floor(sx))))
            x1 = min(width - 1, x0 + 1)
            fx = max(0.0, sx - x0)
            target = (y * out_width + x) * 3
            for channel in range(3):
                a = rgb[(y0 * width + x0) * 3 + channel]
                b = rgb[(y0 * width + x1) * 3 + channel]
                c = rgb[(y1 * width + x0) * 3 + channel]
                d = rgb[(y1 * width + x1) * 3 + channel]
                top = a + (b - a) * fx
                bottom = c + (d - c) * fx
                output[target + channel] = round(top + (bottom - top) * fy)
    return output


def prepare_master() -> bytearray:
    width, height, source = read_png(SOURCE)
    occupied = []
    for y in range(height):
        for x in range(width):
            if max(pixel(source, width, x, y)) > 8:
                occupied.append((x, y))
    if not occupied:
        raise ValueError("The Scout master render is empty.")
    left = max(0, min(x for x, _ in occupied) - 10)
    right = min(width, max(x for x, _ in occupied) + 11)
    top = max(0, min(y for _, y in occupied) - 10)
    bottom = min(height, max(y for _, y in occupied) + 11)
    crop_width, crop_height = right - left, bottom - top
    crop = bytearray(crop_width * crop_height * 3)
    for y in range(crop_height):
        start = ((top + y) * width + left) * 3
        crop[y * crop_width * 3:(y + 1) * crop_width * 3] = source[start:start + crop_width * 3]
    # Leave motion-safe room for the articulated side glances, tag glow,
    # and the 240x224-to-412x352 display mapping, which crops a few source rows.
    scale = min(202 / crop_width, 184 / crop_height)
    resized_width, resized_height = round(crop_width * scale), round(crop_height * scale)
    resized = resize_bilinear(crop, crop_width, crop_height, resized_width, resized_height)
    canvas = bytearray(SOURCE_WIDTH * SOURCE_HEIGHT * 3)
    offset_x = (SOURCE_WIDTH - resized_width) // 2
    offset_y = SOURCE_HEIGHT - resized_height - 10
    for y in range(resized_height):
        target = ((offset_y + y) * SOURCE_WIDTH + offset_x) * 3
        canvas[target:target + resized_width * 3] = resized[y * resized_width * 3:(y + 1) * resized_width * 3]
    write_png(PREPARED, SOURCE_WIDTH, SOURCE_HEIGHT, canvas)
    return canvas


def mix_at(image: bytearray, x: int, y: int, color: tuple[int, int, int], alpha: float) -> None:
    if not (0 <= x < SOURCE_WIDTH and 0 <= y < SOURCE_HEIGHT) or alpha <= 0:
        return
    index = (y * SOURCE_WIDTH + x) * 3
    for channel in range(3):
        image[index + channel] = round(image[index + channel] * (1 - alpha) + color[channel] * alpha)


def blink(master: bytes, openness: float, asymmetric: float = 0.0) -> bytearray:
    if openness >= 0.999 and not asymmetric:
        return bytearray(master)
    result = bytearray(master)
    # Eye geometry is measured on the prepared 240x224 master. Keep it here,
    # rather than in display coordinates, so the lids are transformed with the
    # rest of the head. The previous values predated the latest master resize
    # and left the lower/inside edges of both eyes visible at full closure.
    #
    # Each lid borrows a narrow strip of real brow fur and stretches it over the
    # eye. That retains the master render's strand detail, lighting, and white
    # blaze instead of painting a flat brown ellipse over the face.
    eyes = (
        (99, 80, 21, 22, 51, 68),
        (147, 79, 21, 22, 49, 66),
    )
    for eye_number, (cx, cy, rx, ry, brow_top, brow_bottom) in enumerate(eyes):
        local_open = max(0.0, min(1.0, openness + (asymmetric if eye_number == 0 else -asymmetric)))
        closure = 1.0 - local_open
        eye_top = cy - ry
        eye_height = ry * 2
        for y in range(eye_top - 2, cy + ry + 3):
            for x in range(cx - rx - 2, cx + rx + 3):
                nx = (x - cx) / rx
                ny = (y - cy) / ry
                ellipse = nx * nx + ny * ny
                if ellipse > 1.12:
                    continue

                # A small downward curve at the corners follows the rounded eye
                # socket and prevents the partial-blink edge looking ruler-flat.
                boundary = eye_top + closure * eye_height + 1.8 * nx * nx
                lid_edge = max(0.0, min(1.0, (boundary + 1.5 - y) / 3.0))
                socket_edge = max(0.0, min(1.0, (1.12 - ellipse) / 0.12))
                alpha = 0.98 * lid_edge * socket_edge
                if alpha <= 0:
                    continue

                texture_t = max(0.0, min(1.0, (y - eye_top) / eye_height))
                texture_y = round(brow_top + texture_t * (brow_bottom - brow_top))
                # Keep the central white blaze between the eyes instead of
                # stretching it across the inner lids. Reflect the nearby brown
                # brow texture at that boundary so it still varies pixel by
                # pixel and does not turn into a flat fill.
                texture_x = x
                if eye_number == 0 and texture_x > cx + 7:
                    texture_x = 2 * (cx + 7) - texture_x
                elif eye_number == 1 and texture_x < cx - 7:
                    texture_x = 2 * (cx - 7) - texture_x
                texture_x = max(0, min(SOURCE_WIDTH - 1, texture_x))
                fur = pixel(master, SOURCE_WIDTH, texture_x, texture_y)
                mix_at(result, x, y, fur, alpha)

        if local_open < 0.12:
            for x in range(cx - rx + 3, cx + rx - 2):
                nx = (x - cx) / rx
                curve_y = round(cy + 2 + 2.2 * nx * nx)
                base = pixel(result, SOURCE_WIDTH, x, curve_y)
                crease = tuple(round(channel * 0.31) for channel in base)
                mix_at(result, x, curve_y, crease, 0.76)
                mix_at(result, x, curve_y + 1, crease, 0.26)
    return result


def tag_center(master: bytes) -> tuple[int, int]:
    points = []
    for y in range(95, 180):
        for x in range(70, 170):
            red, green, blue = pixel(master, SOURCE_WIDTH, x, y)
            if blue > 120 and green > 90 and blue > red * 1.25:
                points.append((x, y))
    if not points:
        return 120, 139
    return round(sum(x for x, _ in points) / len(points)), round(sum(y for _, y in points) / len(points))


def add_tag_glow(image: bytearray, center: tuple[int, int], strength: float) -> None:
    cx, cy = center
    for y in range(cy - 19, cy + 20):
        for x in range(cx - 19, cx + 20):
            distance = math.hypot(x - cx, y - cy)
            if distance < 19:
                alpha = max(0.0, 1 - distance / 19) ** 2 * strength * 0.42
                mix_at(image, x, y, (38, 190, 255), alpha)


def dim_tag(image: bytearray, center: tuple[int, int], amount: float) -> None:
    """Dim the baked tag illumination as eyelids close (sleep uses blink level 4)."""
    cx, cy = center
    for y in range(cy - 13, cy + 14):
        for x in range(cx - 13, cx + 14):
            distance = math.hypot(x - cx, y - cy)
            if distance < 13:
                mix_at(image, x, y, (4, 18, 25), amount * max(0.0, 1 - distance / 16))


def affine(source: bytes, *, angle=0.0, scale_x=1.0, scale_y=1.0, dx=0.0, dy=0.0) -> bytearray:
    output = bytearray(len(source))
    radians = math.radians(angle)
    cosine, sine = math.cos(radians), math.sin(radians)
    cx, cy = SOURCE_WIDTH / 2, SOURCE_HEIGHT / 2
    for y in range(SOURCE_HEIGHT):
        for x in range(SOURCE_WIDTH):
            px, py = x - cx - dx, y - cy - dy
            sx = (cosine * px + sine * py) / scale_x + cx
            sy = (-sine * px + cosine * py) / scale_y + cy
            ix, iy = round(sx), round(sy)
            if 0 <= ix < SOURCE_WIDTH and 0 <= iy < SOURCE_HEIGHT:
                source_index = (iy * SOURCE_WIDTH + ix) * 3
                target = (y * SOURCE_WIDTH + x) * 3
                output[target:target + 3] = source[source_index:source_index + 3]
    return output


def articulate_head(source: bytes, *, angle=0.0, scale_x=1.0, scale_y=1.0,
                     dx=0.0, dy=0.0) -> bytearray:
    """Move Scout's head independently while preserving an anchored torso.

    The feathered, premultiplied split reconstructs the source exactly at the
    neutral pose and avoids a hard seam through the neck during motion.
    """
    pivot_x, pivot_y = 120.0, 108.0

    def head_weight(y: int) -> float:
        if y <= 111:
            return 1.0
        if y >= 135:
            return 0.0
        value = (135 - y) / 24
        return value * value * (3 - 2 * value)

    output = bytearray(len(source))
    for y in range(SOURCE_HEIGHT):
        weight = head_weight(y)
        for x in range(SOURCE_WIDTH):
            index = (y * SOURCE_WIDTH + x) * 3
            for channel in range(3):
                output[index + channel] = round(source[index + channel] * (1 - weight))

    radians = math.radians(angle)
    cosine, sine = math.cos(radians), math.sin(radians)
    for y in range(SOURCE_HEIGHT):
        for x in range(SOURCE_WIDTH):
            px, py = x - pivot_x - dx, y - pivot_y - dy
            sx = (cosine * px + sine * py) / scale_x + pivot_x
            sy = (-sine * px + cosine * py) / scale_y + pivot_y
            ix, iy = round(sx), round(sy)
            if not (0 <= ix < SOURCE_WIDTH and 0 <= iy < SOURCE_HEIGHT):
                continue
            weight = head_weight(iy)
            if weight <= 0:
                continue
            source_index = (iy * SOURCE_WIDTH + ix) * 3
            target = (y * SOURCE_WIDTH + x) * 3
            for channel in range(3):
                output[target + channel] = min(
                    255, output[target + channel] + round(source[source_index + channel] * weight)
                )
    return output


def quantize(value: float) -> float:
    return round(max(0.0, min(1.0, value)) * 4) / 4


def smooth(value: float) -> float:
    return value * value * (3 - 2 * value)


def state_for(track: str, step: int, count: int) -> tuple:
    t = step / (count - 1)
    if step == 0:
        return ("neutral", 0.0)
    if track == "surprise":
        amplitude = quantize(math.sin(math.pi * (t ** 0.7)))
        return ("neutral", 0.0) if step == count - 1 else (track, amplitude)
    return track, quantize(smooth(t))


def render_source(master: bytes, center: tuple[int, int], state: tuple, blink_level: float) -> bytearray:
    track, amplitude = state
    if track == "neutral" or amplitude == 0:
        face = blink(master, blink_level)
        dim_tag(face, center, (1 - blink_level) * 0.58)
        add_tag_glow(face, center, 0.28 * (0.35 + 0.65 * blink_level))
        return face
    angle = dx = dy = 0.0
    scale_x = scale_y = 1.0
    body_angle = body_dx = body_dy = 0.0
    body_scale = 1.0
    eye_open = blink_level
    asymmetric = 0.0
    glow = 0.28
    directions = {
        "right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1),
        "up_right": (1, -1), "up_left": (-1, -1),
        "down_right": (1, 1), "down_left": (-1, 1),
    }
    if track in directions:
        horizontal, vertical = directions[track]
        # The source is a single front-facing render, so rotation, vertical
        # travel, and non-uniform scaling visibly warp the face. Keep every
        # directional look as a restrained horizontal translation instead.
        horizontal_pose = horizontal if horizontal else vertical * 0.5
        dx = horizontal_pose * 5 * amplitude
        body_dx = horizontal_pose * 0.75 * amplitude
    elif track == "surprise":
        dx = 3 * amplitude
        body_dx = 0.45 * amplitude
        glow = 0.55
    elif track == "working":
        dx = -2 * amplitude
        body_dx = -0.3 * amplitude
        eye_open *= 1 - 0.12 * amplitude
        glow = 0.48 + 0.18 * amplitude
    elif track == "complete":
        dx = 3 * amplitude
        body_dx = 0.45 * amplitude
        glow = 0.82
    elif track == "attention":
        dx = -5 * amplitude
        body_dx = -0.75 * amplitude
        asymmetric = 0.08 * amplitude
        glow = 0.48
    elif track == "attention_alternate":
        dx = 5 * amplitude
        body_dx = 0.75 * amplitude
        asymmetric = -0.08 * amplitude
        glow = 0.48
    face = blink(master, eye_open, asymmetric)
    dim_tag(face, center, (1 - blink_level) * 0.58)
    add_tag_glow(face, center, glow * (0.35 + 0.65 * blink_level))
    articulated = articulate_head(
        face, angle=angle, scale_x=scale_x, scale_y=scale_y, dx=dx, dy=dy
    )
    return affine(
        articulated, angle=body_angle, scale_x=body_scale, scale_y=body_scale,
        dx=body_dx, dy=body_dy,
    )


def display_rgb565(source: bytes) -> bytes:
    factor = 396 / SOURCE_WIDTH
    offset_x = (WIDTH - 396) / 2
    offset_y = (HEIGHT - SOURCE_HEIGHT * factor) / 2
    output = bytearray(WIDTH * HEIGHT * 2)
    for y in range(HEIGHT):
        sy = round((y + 0.5 - offset_y) / factor - 0.5)
        sy = max(0, min(SOURCE_HEIGHT - 1, sy))
        for x in range(WIDTH):
            if x + 0.5 < offset_x or x + 0.5 >= offset_x + 396:
                continue
            sx = round((x + 0.5 - offset_x) / factor - 0.5)
            sx = max(0, min(SOURCE_WIDTH - 1, sx))
            source_index = (sy * SOURCE_WIDTH + sx) * 3
            red, green, blue = source[source_index:source_index + 3]
            value = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
            target = (y * WIDTH + x) * 2
            output[target] = value >> 8
            output[target + 1] = value & 255
    return bytes(output)


def word_up(raw: bytes, width: int) -> bytes:
    row_bytes = width * 2
    residual = bytearray(raw)
    for index in range(row_bytes, len(raw), 2):
        value = (raw[index] << 8) | raw[index + 1]
        above = (raw[index - row_bytes] << 8) | raw[index - row_bytes + 1]
        difference = (value - above) & 0xFFFF
        residual[index] = difference >> 8
        residual[index + 1] = difference & 255
    return bytes(residual)


class BlockStore:
    def __init__(self):
        self.data = bytearray()
        self.blocks: dict[tuple[int, str], dict[str, int]] = {}
        self.references = 0

    def add(self, raw: bytes, width: int) -> dict[str, int]:
        self.references += 1
        key = (width, sha256(raw))
        if key not in self.blocks:
            compressed = zlib.compress(word_up(raw, width), 9)
            self.blocks[key] = {"offset": len(self.data), "size": len(compressed)}
            self.data.extend(compressed)
        return dict(self.blocks[key])


def patch_bounds(base: bytes, variants: list[bytes]) -> tuple[int, int, int, int]:
    left, top, right, bottom = WIDTH, HEIGHT, -1, -1
    for variant in variants:
        for y in range(HEIGHT):
            row = y * WIDTH * 2
            for x in range(WIDTH):
                index = row + x * 2
                if variant[index:index + 2] != base[index:index + 2]:
                    left, top = min(left, x), min(top, y)
                    right, bottom = max(right, x), max(bottom, y)
    return (0, 0, 0, 0) if right < 0 else (left, top, right - left + 1, bottom - top + 1)


def crop565(raw: bytes, x: int, y: int, width: int, height: int) -> bytes:
    output = bytearray()
    for row in range(y, y + height):
        start = (row * WIDTH + x) * 2
        output.extend(raw[start:start + width * 2])
    return bytes(output)


def rgb565_to_rgb(raw: bytes, width: int, height: int) -> bytearray:
    output = bytearray(width * height * 3)
    for index in range(width * height):
        value = raw[index * 2] << 8 | raw[index * 2 + 1]
        output[index * 3] = ((value >> 11) & 31) * 255 // 31
        output[index * 3 + 1] = ((value >> 5) & 63) * 255 // 63
        output[index * 3 + 2] = (value & 31) * 255 // 31
    return output


def make_contact_sheet(rendered: dict[tuple, bytes], track_states: dict[str, list[tuple]]) -> None:
    thumb_width, thumb_height = 103, 88
    columns, rows = 6, len(TRACKS)
    sheet = bytearray(columns * thumb_width * rows * thumb_height * 3)
    for row, track in enumerate(TRACKS):
        states = track_states[track]
        for column in range(columns):
            state = states[round(column * (len(states) - 1) / (columns - 1))]
            frame = rgb565_to_rgb(rendered[(state, 0)], WIDTH, HEIGHT)
            for y in range(thumb_height):
                sy = y * HEIGHT // thumb_height
                for x in range(thumb_width):
                    sx = x * WIDTH // thumb_width
                    source = (sy * WIDTH + sx) * 3
                    target = ((row * thumb_height + y) * columns * thumb_width + column * thumb_width + x) * 3
                    sheet[target:target + 3] = frame[source:source + 3]
    write_png(CONTACT, columns * thumb_width, rows * thumb_height, sheet)

    blinks = bytearray(5 * 160 * 138 * 3)
    neutral = ("neutral", 0.0)
    for column in range(5):
        frame = rgb565_to_rgb(rendered[(neutral, column)], WIDTH, HEIGHT)
        for y in range(138):
            sy = y * HEIGHT // 138
            for x in range(160):
                sx = x * WIDTH // 160
                source = (sy * WIDTH + sx) * 3
                target = (y * 800 + column * 160 + x) * 3
                blinks[target:target + 3] = frame[source:source + 3]
    write_png(BLINK_CONTACT, 800, 138, blinks)


def export() -> dict:
    master = prepare_master()
    center = tag_center(master)
    track_states = {
        track: [state_for(track, step, count) for step in range(count)]
        for track, count in zip(TRACKS, TRACK_STEPS)
    }
    unique_states = sorted({state for states in track_states.values() for state in states})
    rendered: dict[tuple, bytes] = {}
    for state in unique_states:
        for blink_index, openness in enumerate(BLINKS):
            rendered[(state, blink_index)] = display_rgb565(render_source(master, center, state, openness))

    left, top, right, bottom = WIDTH, HEIGHT, -1, -1
    for raw in rendered.values():
        for y in range(HEIGHT):
            for x in range(WIDTH):
                index = (y * WIDTH + x) * 2
                if raw[index] or raw[index + 1]:
                    left, top = min(left, x), min(top, y)
                    right, bottom = max(right, x), max(bottom, y)
    base_width, base_height = right - left + 1, bottom - top + 1
    canvas_margin = min(left, top, WIDTH - 1 - right, HEIGHT - 1 - bottom)
    if canvas_margin < 8:
        raise ValueError(
            f"Animation-safe canvas margin is {canvas_margin}px; expected at least 8px."
        )
    store = BlockStore()
    frames = []
    max_patch = 0
    for track in TRACKS:
        for step, state in enumerate(track_states[track]):
            levels = [rendered[(state, blink_index)] for blink_index in range(5)]
            x, y, width, height = patch_bounds(levels[0], levels[1:])
            max_patch = max(max_patch, width * height)
            frames.append({
                "direction": track,
                "step": step,
                "base": store.add(crop565(levels[0], left, top, base_width, base_height), base_width),
                "patchX": x,
                "patchY": y,
                "patchWidth": width,
                "patchHeight": height,
                "blinks": [store.add(crop565(level, x, y, width, height), width) for level in levels[1:]],
            })
    data = bytes(store.data)
    source_bytes = SOURCE.read_bytes()
    generator_bytes = Path(__file__).read_bytes()
    metadata = {
        "layout": "base-patch",
        "encoding": "zlib-rgb565-word-up-be",
        "width": WIDTH,
        "height": HEIGHT,
        "baseBounds": [left, top, base_width, base_height],
        "minimumCanvasMarginPixels": canvas_margin,
        "steps": 24,
        "directions": list(TRACKS),
        "trackSteps": list(TRACK_STEPS),
        "trackOffsets": [sum(TRACK_STEPS[:index]) for index in range(len(TRACKS))],
        "frameCount": len(frames),
        "blinkLevels": list(BLINKS),
        "maxPatchPixels": max_patch,
        "maxPatchBytes": max_patch * 2,
        "dataBytes": len(data),
        "dataSha256": sha256(data),
        "metadataBytes": len(frames) * FRAME_RECORD_BYTES + len(TRACKS) * 3 + 4 + 32,
        "partitionBytes": 12451840,
        "uniqueBlocks": len(store.blocks),
        "blockReferences": store.references,
        "source": {"path": SOURCE.relative_to(ROOT).as_posix(), "sha256": sha256(source_bytes)},
        "generator": {"path": Path(__file__).relative_to(ROOT).as_posix(), "sha256": sha256(generator_bytes)},
        "frames": frames,
    }
    write_if_changed(FRAMES, data)
    write_if_changed(METADATA, json.dumps(metadata, indent=2) + "\n")
    make_contact_sheet(rendered, track_states)
    print(f"Scout frames: {len(data):,} bytes; {len(store.blocks)} unique blocks; "
          f"max blink patch {max_patch:,} pixels; {len(frames)} poses")
    print(f"SHA256 {metadata['dataSha256']}")
    return metadata


if __name__ == "__main__":
    try:
        export()
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        raise SystemExit(f"Scout generation failed: {error}")

