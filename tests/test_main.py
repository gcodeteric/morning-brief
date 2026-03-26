import io
import unittest
from contextlib import redirect_stdout

import main


class MainSummaryTests(unittest.TestCase):
    def test_cli_summary_uses_digest_wording(self):
        curated = {
            "selected": [
                {"title": "Story 1", "score": 50},
                {"title": "Story 2", "score": 42},
            ]
        }
        plan = {
            "instagram_morning_digest": [{"title": "Morning Story"}],
            "instagram_afternoon_digest": [{"title": "Afternoon Story"}],
            "youtube_daily": {"title": "YT"},
            "reddit_candidates": [{"title": "R1"}],
            "discord_post": {"title": "D1"},
        }

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            main._print_run_summary(curated, plan, {}, dry_run=True)
        output = buffer.getvalue()

        self.assertIn("IG manhã=", output)
        self.assertIn("IG tarde=", output)
        self.assertNotIn("IG sim=", output)
        self.assertNotIn("IG moto=", output)


if __name__ == "__main__":
    unittest.main()
