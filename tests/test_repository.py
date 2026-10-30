from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_catalog_matches_distributable_packs(self):
        catalog = json.loads((ROOT / "dist/catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["schemaVersion"], 2)
        self.assertEqual(catalog["repository"], "ScrewCitySoftware/agent-buddy-characters")
        folders = sorted(path.name for path in (ROOT / "characters").iterdir()
                         if (path / "character.json").is_file())
        records = catalog["characters"]
        self.assertEqual([record["id"] for record in records], folders)
        for record in records:
            pack = ROOT / "dist" / record["file"]
            self.assertTrue(pack.is_file())
            self.assertEqual(hashlib.sha256(pack.read_bytes()).hexdigest(), record["sha256"])
            self.assertRegex(record["version"], r"^\d+\.\d+\.\d+")
            self.assertIn(f"/{record['releaseTag']}/{record['file']}", record["downloadUrl"])

    def test_checksum_manifest_matches_catalog(self):
        catalog = json.loads((ROOT / "dist/catalog.json").read_text(encoding="utf-8"))
        expected = "".join(
            f"{record['sha256']}  {record['file']}\n" for record in catalog["characters"]
        )
        self.assertEqual((ROOT / "dist/SHA256SUMS").read_text(encoding="ascii"), expected)

    def test_pages_catalog_has_downloads_and_previews(self):
        catalog = json.loads((ROOT / "_site/catalog.json").read_text(encoding="utf-8"))
        for record in catalog["characters"]:
            self.assertTrue(record["downloadUrl"].startswith("https://github.com/"))
            self.assertTrue((ROOT / "_site" / record["previewUrl"]).is_file())
            if record["id"] == "scout":
                animation = record["animation"]
                self.assertEqual(animation["frameCount"], 20)
                self.assertEqual((animation["frameWidth"], animation["frameHeight"]), (206, 176))
                self.assertTrue((ROOT / "_site" / animation["sheetUrl"]).is_file())

    def test_public_site_links_attribution_and_uses_master_art(self):
        html = (ROOT / "_site/index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('href="https://getagentbuddy.com/"'), 1)
        app = (ROOT / "_site/app.js").read_text(encoding="utf-8")
        self.assertNotIn("Agent Buddy", app)
        self.assertNotIn("Dan Wahlin", html)
        catalog = json.loads((ROOT / "dist/catalog.json").read_text(encoding="utf-8"))
        scout = next(record for record in catalog["characters"] if record["id"] == "scout")
        self.assertEqual(scout["preview"], "assets/source/scout-master-original.png")

    def test_gallery_uses_three_column_desktop_layout(self):
        css = (ROOT / "_site/styles.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr))", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", css)
        self.assertIn("aspect-ratio: 412 / 352", css)
        app = (ROOT / "_site/app.js").read_text(encoding="utf-8")
        self.assertIn("IntersectionObserver", app)
        self.assertIn("prefers-reduced-motion", app)
        self.assertIn("preview-toggle", app)

    def test_workflows_pin_actions_and_upstream(self):
        upstream = json.loads((ROOT / "UPSTREAM_AGENT_BUDDY.json").read_text(encoding="utf-8"))
        for name in ("ci.yml", "release.yml"):
            workflow = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
            for reference in re.findall(r"uses:\s+[^@\s]+@([^\s#]+)", workflow):
                self.assertRegex(reference, r"^[0-9a-f]{40}$", f"{name} has an unpinned action")
            self.assertIn(upstream["commit"], workflow)
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("retention-days: 7", ci)
        release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("python scripts/release_plan.py", release)
        self.assertNotIn("workflow_dispatch", release)
        self.assertIn("if: always() && needs.pages.result == 'success'", release)


if __name__ == "__main__":
    unittest.main()
