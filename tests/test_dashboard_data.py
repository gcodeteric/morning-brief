import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import dashboard_data


def make_story(title="Story", link="https://example.com/story", category="sim_racing", score=80):
    return {
        "title": title,
        "source": "Source",
        "category": category,
        "score": score,
        "summary": f"Resumo {title}",
        "link": link,
    }


class DashboardDataTests(unittest.TestCase):
    def test_snapshot_save_and_load_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            snapshot_path = base / "dashboard_latest_snapshot.json"
            run_summary_path = base / "run_summary.json"
            output_file = base / "brief.md"
            overrides_file = base / "manual_overrides.json"
            cards_dir = base / "cards"
            cards_dir.mkdir()
            output_file.write_text("# Brief", encoding="utf-8")
            run_summary_path.write_text(json.dumps({"status": "OK", "ended_at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
            overrides_file.write_text(json.dumps({"instagram_morning_digest": 1}), encoding="utf-8")

            curated = {
                "selected": [make_story()],
                "categories": {"sim_racing": 1},
                "total_before_dedup": 2,
                "total_after_dedup": 1,
                "agent_outputs": [],
            }
            plan = {
                "instagram_morning_digest": [make_story()],
                "instagram_morning_output": {"post": "Digest pronto"},
                "instagram_afternoon_digest": [],
            }

            with mock.patch.multiple(
                dashboard_data,
                DASHBOARD_SNAPSHOT_FILE=snapshot_path,
                RUN_SUMMARY_FILE=run_summary_path,
                OUTPUT_FILE=output_file,
                MANUAL_OVERRIDES_FILE=overrides_file,
                CARDS_DIR=cards_dir,
            ):
                saved = dashboard_data.save_dashboard_snapshot(curated, plan, {}, output_file, {"status": "OK"})
                snapshot = dashboard_data.load_latest_snapshot()
                context = dashboard_data.build_dashboard_context()

            self.assertEqual(saved, str(snapshot_path))
            self.assertTrue(snapshot["exists"])
            self.assertEqual(snapshot["schema_version"], dashboard_data.SNAPSHOT_SCHEMA_VERSION)
            self.assertEqual(context["freshness"]["label"], "Fresh")
            self.assertEqual(context["selected_stories"][0]["link"], "https://example.com/story")

    def test_missing_snapshot_uses_partial_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            snapshot_path = base / "dashboard_latest_snapshot.json"
            run_summary_path = base / "run_summary.json"
            output_file = base / "brief.md"
            overrides_file = base / "manual_overrides.json"
            cards_dir = base / "cards"
            output_file.write_text("# Brief", encoding="utf-8")
            run_summary_path.write_text(json.dumps({
                "status": "OK",
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "brief_file": str(output_file),
            }), encoding="utf-8")

            with mock.patch.multiple(
                dashboard_data,
                DASHBOARD_SNAPSHOT_FILE=snapshot_path,
                RUN_SUMMARY_FILE=run_summary_path,
                OUTPUT_FILE=output_file,
                MANUAL_OVERRIDES_FILE=overrides_file,
                CARDS_DIR=cards_dir,
            ):
                context = dashboard_data.build_dashboard_context()

            self.assertEqual(context["freshness"]["label"], "Partial")
            self.assertEqual(context["freshness"]["source"], "fallback_files")
            self.assertTrue(context["brief"]["exists"])

    def test_stale_snapshot_is_labeled_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            snapshot_path = base / "dashboard_latest_snapshot.json"
            stale_time = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
            snapshot_path.write_text(json.dumps({
                "schema_version": 2,
                "snapshot_kind": "latest_dashboard_snapshot",
                "timestamp": stale_time,
                "plan": {"instagram_morning_digest": [make_story()]},
                "curated_stories": [make_story()],
            }), encoding="utf-8")

            with mock.patch.object(dashboard_data, "DASHBOARD_SNAPSHOT_FILE", snapshot_path):
                snapshot = dashboard_data.load_latest_snapshot()
                freshness = dashboard_data._build_freshness_status(snapshot, {"exists": False}, {"exists": False})

            self.assertEqual(freshness["label"], "Stale")


if __name__ == "__main__":
    unittest.main()
