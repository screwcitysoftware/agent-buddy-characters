from __future__ import annotations

import importlib.util
import json
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "export_web_animation", ROOT / "scripts/export_web_animation.py"
)
EXPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORTER)


class WebAnimationTests(unittest.TestCase):
    def test_sheet_has_expected_dimensions_and_reasonable_size(self):
        catalog = json.loads((ROOT / "_site/catalog.json").read_text(encoding="utf-8"))
        scout = next(record for record in catalog["characters"] if record["id"] == "scout")
        path = ROOT / "_site" / scout["animation"]["sheetUrl"]
        raw = path.read_bytes()
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack_from(">II", raw, 16)
        self.assertEqual(width, EXPORTER.COLUMNS * EXPORTER.FRAME_WIDTH)
        self.assertEqual(height, 4 * EXPORTER.FRAME_HEIGHT)
        self.assertLess(path.stat().st_size, 3 * 1024 * 1024)

    def test_each_animation_frame_preserves_black_canvas_margin(self):
        character = ROOT / "characters/scout"
        metadata = json.loads((character / "frames.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(metadata["minimumCanvasMarginPixels"], 8)
        self.assertEqual(metadata["width"] / metadata["height"], 412 / 352)


if __name__ == "__main__":
    unittest.main()
