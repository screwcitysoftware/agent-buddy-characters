from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARACTER = ROOT / "characters" / "scout"


class ScoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "tools"))
        spec = importlib.util.spec_from_file_location("character_pack", ROOT / "tools/character_pack.py")
        cls.pack_tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.pack_tool)

    def test_source_and_generator_are_pinned(self):
        metadata = json.loads((CHARACTER / "frames.json").read_text(encoding="utf-8"))
        for key in ("source", "generator"):
            record = metadata[key]
            data = (ROOT / record["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])

    def test_pack_passes_official_decoder(self):
        pack = (ROOT / "dist/scout.acpk").read_bytes()
        info = self.pack_tool.decode(pack, 12_451_840)
        self.assertEqual(info["id"], "scout")
        self.assertEqual(info["name"], "Scout")
        self.assertEqual(info["layout"], self.pack_tool.LAYOUT_BASE_PATCH)
        self.assertEqual(info["frame_count"], 288)

    def test_frame_contract(self):
        metadata = json.loads((CHARACTER / "frames.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["width"], 412)
        self.assertEqual(metadata["height"], 352)
        self.assertEqual(metadata["frameCount"], 288)
        self.assertEqual(metadata["blinkLevels"], [1.0, 0.75, 0.5, 0.25, 0.0])
        self.assertGreaterEqual(metadata["minimumCanvasMarginPixels"], 8)
        self.assertLess((ROOT / "dist/scout.acpk").stat().st_size, 12_451_840)

    def test_closed_blink_covers_eyes_with_textured_fur(self):
        sys.path.insert(0, str(CHARACTER))
        spec = importlib.util.spec_from_file_location("scout_build", CHARACTER / "build.py")
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        width, _, master = generator.read_png(generator.PREPARED)
        closed = generator.blink(master, 0.0)

        def color(image, x, y):
            index = (y * width + x) * 3
            return tuple(image[index:index + 3])

        for cx, cy, rx, ry in ((99, 81, 12, 15), (143, 80, 12, 15)):
            core = [
                (x, y)
                for y in range(cy - ry, cy + ry + 1)
                for x in range(cx - rx, cx + rx + 1)
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 0.82
            ]
            open_dark = sum(max(color(master, x, y)) < 70 for x, y in core)
            closed_dark = sum(max(color(closed, x, y)) < 70 for x, y in core)
            lid_colors = {color(closed, x, y) for x, y in core}
            self.assertLess(closed_dark, open_dark * 0.25)
            self.assertGreater(len(lid_colors), 300)


if __name__ == "__main__":
    unittest.main()

