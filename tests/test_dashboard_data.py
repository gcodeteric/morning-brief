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

    def test_story_workspace_builds_per_story_platform_outputs(self):
        story = make_story("Main Story", "https://example.com/main-story", score=91)
        snapshot = {
            "curated_stories": [story],
            "plan": {
                "instagram_morning_digest": [story],
                "x_thread_1": story,
                "youtube_daily": story,
                "reddit_candidates": [story],
                "discord_post": story,
            },
            "agent_outputs": [
                {
                    "article": story,
                    "analysis": json.dumps({
                        "why_it_matters": "This matters for the community.",
                        "headline_hook": "Fast hook",
                    }),
                    "instagram_pack": {
                        "cover_hook": "Big hook",
                        "slides": ["Line one", "Line two"],
                        "caption": "Caption line one.\nCaption line two.",
                    },
                    "voice_script": "Voice script ready",
                    "qa": json.dumps({
                        "approved": True,
                        "hashtags": ["#simracing", "#motorsport"],
                    }),
                }
            ],
        }

        items = dashboard_data.build_story_workspace_items(snapshot=snapshot, overrides={})

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["key"], "https://example.com/main-story")
        self.assertTrue(item["in_active_plan"])
        self.assertIn("Morning Digest", " | ".join(item["planner_tags"]))
        self.assertIn("X Thread 1", item["planner_tags"])
        self.assertIn("YouTube Daily", item["planner_tags"])
        self.assertIn("Reddit Candidate", item["planner_tags"])
        self.assertIn("Discord Post", item["planner_tags"])
        self.assertEqual(
            item["recommended_platforms"],
            ["instagram", "x", "youtube", "reddit", "discord", "email"],
        )

        instagram = item["platform_outputs"]["instagram"]
        self.assertEqual(instagram["image_text"]["hook"], "Big hook")
        self.assertEqual(instagram["image_text"]["line_1"], "Line one")
        self.assertEqual(instagram["image_text"]["line_2"], "Line two")
        self.assertIn("https://example.com/main-story", instagram["caption"]["text"])
        self.assertIn("#simracing", instagram["hashtags"])

        youtube = item["platform_outputs"]["youtube"]
        self.assertEqual(youtube["voice_script"], "Voice script ready")
        self.assertIn("https://example.com/main-story", youtube["description"])

        x_output = item["platform_outputs"]["x"]
        self.assertIn("https://example.com/main-story", x_output["text"])

        email_output = item["platform_outputs"]["email"]
        self.assertIn("https://example.com/main-story", email_output["body"])

    def test_story_workspace_respects_active_digest_variant_and_fallback_outputs(self):
        primary_story = make_story("Primary Story", "https://example.com/primary")
        alt_story = make_story("Alternative Story", "https://example.com/alternative")
        snapshot = {
            "curated_stories": [primary_story, alt_story],
            "plan": {
                "instagram_morning_digest": [primary_story],
                "instagram_morning_digest_alternatives": [[alt_story]],
                "instagram_afternoon_digest": [],
            },
            "agent_outputs": [],
        }

        items = dashboard_data.build_story_workspace_items(
            snapshot=snapshot,
            overrides={"instagram_morning_digest": 1},
        )

        by_key = {item["key"]: item for item in items}
        self.assertFalse(by_key["https://example.com/primary"]["in_active_plan"])
        self.assertEqual(
            by_key["https://example.com/alternative"]["planner_tags"],
            ["Morning Digest (variant 1)"],
        )
        self.assertTrue(by_key["https://example.com/alternative"]["in_active_plan"])

        instagram = by_key["https://example.com/alternative"]["platform_outputs"]["instagram"]
        self.assertEqual(instagram["mode"], "fallback_story_draft")
        self.assertEqual(instagram["image_text"]["hook"], "Alternative Story")
        self.assertIn("https://example.com/alternative", instagram["caption"]["text"])
        self.assertEqual(
            by_key["https://example.com/alternative"]["available_platforms"],
            list(dashboard_data.WORKSPACE_PLATFORMS),
        )

    def test_snapshot_save_persists_full_rated_story_pool(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            snapshot_path = base / "dashboard_latest_snapshot.json"
            brief_path = base / "brief.md"
            brief_path.write_text("# Brief", encoding="utf-8")

            selected_story = make_story("Selected Story", "https://example.com/selected", score=92)
            extra_story = make_story("Extra Story", "https://example.com/extra", category="motorsport", score=41)
            curated = {
                "selected": [selected_story],
                "story_pool": [selected_story, extra_story],
                "categories": {"sim_racing": 1},
                "total_before_dedup": 4,
                "total_after_dedup": 2,
                "agent_outputs": [],
            }

            with mock.patch.object(dashboard_data, "DASHBOARD_SNAPSHOT_FILE", snapshot_path):
                dashboard_data.save_dashboard_snapshot(curated, {"instagram_morning_digest": [selected_story]}, {}, brief_path, {"status": "OK"})
                snapshot = dashboard_data.load_latest_snapshot()

            self.assertEqual(len(snapshot["curated_stories"]), 1)
            self.assertEqual(len(snapshot["rated_story_pool"]), 2)
            self.assertEqual(snapshot["rated_story_pool"][1]["link"], "https://example.com/extra")

    def test_story_workspace_uses_broader_rated_story_pool_instead_of_selected_only(self):
        selected_story = make_story("Selected Story", "https://example.com/selected", score=92)
        extra_story = make_story("Extra Story", "https://example.com/extra", category="motorsport", score=41)
        manual_story = make_story("Manual Story", "https://example.com/manual", category="nostalgia", score=27)
        snapshot = {
            "curated_stories": [selected_story],
            "rated_story_pool": [selected_story, extra_story, manual_story],
            "plan": {
                "instagram_morning_digest": [selected_story],
                "instagram_afternoon_digest": [],
            },
            "agent_outputs": [],
        }

        items = dashboard_data.build_story_workspace_items(snapshot=snapshot, overrides={})
        by_key = {item["key"]: item for item in items}

        self.assertEqual(len(items), 3)
        self.assertTrue(by_key["https://example.com/selected"]["selected_by_system"])
        self.assertFalse(by_key["https://example.com/extra"]["selected_by_system"])
        self.assertFalse(by_key["https://example.com/manual"]["selected_by_system"])
        self.assertFalse(by_key["https://example.com/extra"]["in_active_plan"])
        self.assertEqual(by_key["https://example.com/extra"]["story"]["score"], 41)
        self.assertIn("Morning Digest", " | ".join(by_key["https://example.com/selected"]["planner_tags"]))

    def test_dashboard_context_exposes_full_workspace_story_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            snapshot_path = base / "dashboard_latest_snapshot.json"
            run_summary_path = base / "run_summary.json"
            output_file = base / "brief.md"
            overrides_file = base / "manual_overrides.json"
            cards_dir = base / "cards"
            cards_dir.mkdir()
            output_file.write_text("# Brief", encoding="utf-8")
            run_summary_path.write_text(json.dumps({
                "status": "OK",
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "articles_selected": 1,
                "brief_file": str(output_file),
            }), encoding="utf-8")

            selected_story = make_story("Selected Story", "https://example.com/selected", score=92)
            extra_story = make_story("Extra Story", "https://example.com/extra", category="motorsport", score=41)
            snapshot_path.write_text(json.dumps({
                "schema_version": dashboard_data.SNAPSHOT_SCHEMA_VERSION,
                "snapshot_kind": "latest_dashboard_snapshot",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run_status": "OK",
                "curated_stories": [selected_story],
                "rated_story_pool": [selected_story, extra_story],
                "plan": {
                    "instagram_morning_digest": [selected_story],
                    "instagram_afternoon_digest": [],
                },
                "agent_outputs": [],
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

            self.assertEqual(len(context["selected_stories"]), 1)
            self.assertEqual(context["status"]["workspace_stories"], 2)
            self.assertEqual(len(context["story_workspace"]), 2)
            self.assertEqual(len(context["story_sets"]["rated_story_pool"]), 2)


if __name__ == "__main__":
    unittest.main()
