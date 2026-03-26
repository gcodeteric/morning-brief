import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import dashboard_overrides


class DashboardOverridesTests(unittest.TestCase):
    def test_ensure_overrides_file_creates_neutral_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            live_file = base / "manual_overrides.json"
            example_file = base / "manual_overrides.example.json"
            example_file.write_text(
                json.dumps({
                    "instagram_morning_digest": 0,
                    "instagram_afternoon_digest": 1,
                    "youtube_daily": 2,
                    "discord_post": 0,
                }),
                encoding="utf-8",
            )

            with mock.patch.object(dashboard_overrides, "OVERRIDES_FILE", live_file), mock.patch.object(
                dashboard_overrides, "OVERRIDES_EXAMPLE_FILE", example_file
            ):
                created = dashboard_overrides.ensure_overrides_file()
                data = json.loads(live_file.read_text(encoding="utf-8"))

        self.assertEqual(created, live_file)
        self.assertEqual(
            data,
            {
                "instagram_morning_digest": 0,
                "instagram_afternoon_digest": 0,
                "youtube_daily": 0,
                "discord_post": 0,
            },
        )
        self.assertTrue(all(value == 0 for value in data.values()))


if __name__ == "__main__":
    unittest.main()
