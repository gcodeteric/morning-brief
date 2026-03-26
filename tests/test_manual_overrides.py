import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import manual_overrides


class ManualOverridesTests(unittest.TestCase):
    def test_missing_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            overrides_path = Path(tmpdir) / "manual_overrides.json"
            with mock.patch.object(manual_overrides, "OVERRIDES_FILE", overrides_path):
                self.assertEqual(manual_overrides.load_manual_overrides(), {})

    def test_invalid_json_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            overrides_path = Path(tmpdir) / "manual_overrides.json"
            overrides_path.write_text("{invalid", encoding="utf-8")
            with mock.patch.object(manual_overrides, "OVERRIDES_FILE", overrides_path):
                self.assertEqual(manual_overrides.load_manual_overrides(), {})

    def test_valid_override_selection_uses_digest_alternative(self):
        plan = {
            "instagram_morning_digest": [{"title": "Primary"}],
            "instagram_morning_digest_alternatives": [
                [{"title": "Alt 1"}],
                [{"title": "Alt 2"}],
            ],
        }
        updated = manual_overrides.apply_manual_overrides(
            plan,
            {"instagram_morning_digest": 1},
        )

        self.assertEqual(updated["instagram_morning_digest"][0]["title"], "Alt 1")
        self.assertTrue(updated["manual_overrides_applied"])
        self.assertEqual(updated["override_summary"], {"instagram_morning_digest": 1})

    def test_invalid_index_falls_back_to_primary(self):
        plan = {
            "instagram_afternoon_digest": [{"title": "Primary"}],
            "instagram_afternoon_digest_alternatives": [[{"title": "Alt 1"}]],
        }
        updated = manual_overrides.apply_manual_overrides(
            plan,
            {"instagram_afternoon_digest": 99},
        )

        self.assertEqual(updated["instagram_afternoon_digest"][0]["title"], "Primary")
        self.assertFalse(updated["manual_overrides_applied"])


if __name__ == "__main__":
    unittest.main()
