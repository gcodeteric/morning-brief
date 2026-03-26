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

    def test_selection_summary_resolves_active_variants_correctly(self):
        context = {
            "snapshot": {
                "run_status": "OK",
                "timestamp": "2026-03-26T10:00:00+00:00",
                "plan": {
                    "instagram_morning_digest": [
                        make_story("Morning Primary", "https://example.com/morning-primary"),
                    ],
                    "instagram_morning_digest_alternatives": [
                        [make_story("Morning Alt 1", "https://example.com/morning-alt-1")],
                        [make_story("Morning Alt 2", "https://example.com/morning-alt-2")],
                    ],
                    "instagram_afternoon_digest": [
                        make_story("Afternoon Primary", "https://example.com/afternoon-primary", category="motorsport"),
                    ],
                    "instagram_afternoon_digest_alternatives": [
                        [make_story("Afternoon Alt 1", "https://example.com/afternoon-alt-1", category="motorsport")],
                    ],
                },
                "curated_stories": [make_story()],
                "brief_path": "C:/brief.md",
            },
            "run_summary": {
                "status": "OK",
                "ended_at": "2026-03-26T10:00:00+00:00",
                "articles_selected": 1,
            },
            "overrides": {
                "instagram_morning_digest": 1,
                "instagram_afternoon_digest": 0,
            },
            "cards": {"cards": []},
        }

        summary_primary = dashboard_data.build_selection_summary(context)
        summary_alt = dashboard_data.build_selection_summary(
            context,
            {"instagram_morning_digest": 2, "instagram_afternoon_digest": 1},
        )

        self.assertIn("Instagram Morning Digest (variant 1):", summary_primary)
        self.assertIn("Morning Alt 1", summary_primary)
        self.assertNotIn("Morning Primary | https://example.com/morning-primary", summary_primary)

        self.assertIn("Instagram Morning Digest (variant 2):", summary_alt)
        self.assertIn("Morning Alt 2", summary_alt)
        self.assertIn("Instagram Afternoon Digest (variant 1):", summary_alt)
        self.assertIn("Afternoon Alt 1", summary_alt)

    def test_selection_summary_invalid_variant_falls_back_to_primary_story_list(self):
        context = {
            "snapshot": {
                "run_status": "OK",
                "timestamp": "2026-03-26T10:00:00+00:00",
                "plan": {
                    "instagram_morning_digest": [make_story("Morning Primary", "https://example.com/primary")],
                    "instagram_morning_digest_alternatives": [],
                    "instagram_afternoon_digest": [],
                },
                "curated_stories": [make_story()],
            },
            "run_summary": {"status": "OK", "ended_at": "2026-03-26T10:00:00+00:00"},
            "overrides": {},
            "cards": {"cards": []},
        }
        summary = dashboard_data.build_selection_summary(
            context,
            {"instagram_morning_digest": 2},
        )

        self.assertIn("Instagram Morning Digest (variant 0):", summary)
        self.assertIn("Morning Primary", summary)


if __name__ == "__main__":
    unittest.main()
