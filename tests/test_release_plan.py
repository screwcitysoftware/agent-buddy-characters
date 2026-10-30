from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_plan", ROOT / "scripts/release_plan.py")
RELEASE_PLAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE_PLAN)


class ReleasePlanTests(unittest.TestCase):
    def test_detects_character_and_shared_pack_changes(self):
        known = {"scout", "other"}
        self.assertEqual(
            RELEASE_PLAN.changed_ids_from_paths(["characters/scout/catalog.json"], known),
            ["scout"],
        )
        self.assertEqual(
            RELEASE_PLAN.changed_ids_from_paths(["tools/character_pack.py"], known),
            ["other", "scout"],
        )
        self.assertEqual(
            RELEASE_PLAN.changed_ids_from_paths(["scripts/release_plan.py"], known),
            ["other", "scout"],
        )
        self.assertEqual(RELEASE_PLAN.changed_ids_from_paths(["site/index.html"], known), [])

    def test_unchanged_pack_does_not_release(self):
        current = {"version": "1.0.1", "releaseTag": "v1.0.1"}
        self.assertIsNone(RELEASE_PLAN.evaluate("scout", current, {}, "same", "same", None))

    def test_changed_pack_requires_version_bump(self):
        metadata = {"version": "1.0.1", "releaseTag": "scout-v1.0.1"}
        with self.assertRaisesRegex(ValueError, "new version"):
            RELEASE_PLAN.evaluate("scout", metadata, metadata, "new", "old", None)

    def test_changed_pack_becomes_independent_release(self):
        previous = {"version": "1.0.1", "releaseTag": "v1.0.1"}
        current = {"version": "1.0.2", "releaseTag": "scout-v1.0.2"}
        self.assertEqual(
            RELEASE_PLAN.evaluate("scout", current, previous, "new", "old", None),
            {"id": "scout", "version": "1.0.2", "tag": "scout-v1.0.2"},
        )

    def test_failed_release_metadata_can_be_corrected_without_another_bump(self):
        metadata = {"version": "1.0.2", "releaseTag": "scout-v1.0.2"}
        self.assertEqual(
            RELEASE_PLAN.evaluate("scout", metadata, metadata, "new", None, None),
            {"id": "scout", "version": "1.0.2", "tag": "scout-v1.0.2"},
        )

    def test_matching_existing_release_makes_rerun_idempotent(self):
        previous = {"version": "1.0.1", "releaseTag": "v1.0.1"}
        current = {"version": "1.0.2", "releaseTag": "scout-v1.0.2"}
        self.assertIsNone(RELEASE_PLAN.evaluate("scout", current, previous, "new", "old", "new"))

    def test_unchanged_pack_rejects_unnecessary_bump(self):
        previous = {"version": "1.0.1", "releaseTag": "v1.0.1"}
        current = {"version": "1.0.2", "releaseTag": "scout-v1.0.2"}
        with self.assertRaisesRegex(ValueError, "unchanged"):
            RELEASE_PLAN.evaluate("scout", current, previous, "same", "same", None)


if __name__ == "__main__":
    unittest.main()
