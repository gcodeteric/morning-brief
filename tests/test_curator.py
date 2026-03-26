import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import curator


def make_article(
    title="iRacing 2026 update adds new content",
    link="https://example.com/story",
    source="Source A",
    summary="Strong sim racing update with useful detail.",
    category="sim_racing",
    priority=8,
    no_date=False,
):
    return {
        "title": title,
        "link": link,
        "source": source,
        "summary": summary,
        "category": category,
        "priority": priority,
        "no_date": no_date,
        "published": datetime.now(timezone.utc).isoformat(),
    }


class CuratorTests(unittest.TestCase):
    def test_empty_input_returns_safe_structure(self):
        result = curator.curate_articles([])
        self.assertEqual(result["selected"], [])
        self.assertEqual(result["total_before_dedup"], 0)
        self.assertEqual(result["total_after_dedup"], 0)
        self.assertEqual(result["categories"], {})

    def test_malformed_and_incomplete_articles_do_not_crash(self):
        articles = [
            None,
            "bad-shape",
            {},
            {"summary": "Summary only", "source": "Feed A", "link": "https://example.com/summary-only"},
            {"title": "No Source", "link": "https://example.com/no-source", "summary": "text"},
            make_article(title="", summary="Fallback summary", source="Feed B", link="https://example.com/fallback"),
            make_article(title="Valid", link="", source="Feed C"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_seen = Path(tmpdir) / "seen_links.json"
            with mock.patch.object(curator, "SEEN_LINKS_FILE", temp_seen), \
                 mock.patch.object(curator, "_DRY_RUN", True):
                result = curator.curate_articles(articles)

        self.assertIn("selected", result)
        self.assertIn("categories", result)
        self.assertIsInstance(result["selected"], list)

    def test_valid_inputs_produce_usable_curated_result(self):
        articles = [
            make_article(title="iRacing 2026 update adds new content", link="https://example.com/1", source="Feed A"),
            make_article(title="Assetto Corsa EVO patch review", link="https://example.com/2", source="Feed B"),
            make_article(title="Le Mans update for sim racing fans", link="https://example.com/3", source="Feed C", category="motorsport"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_seen = Path(tmpdir) / "seen_links.json"
            with mock.patch.object(curator, "SEEN_LINKS_FILE", temp_seen), \
                 mock.patch.object(curator, "_DRY_RUN", True):
                result = curator.curate_articles(articles)

        self.assertGreaterEqual(len(result["selected"]), 1)
        self.assertTrue(all("score" in article for article in result["selected"]))

    def test_canonical_url_dedup_collapses_tracking_variants(self):
        base = "https://example.com/article"
        articles = [
            make_article(link=f"{base}?utm_source=x", source="Feed A", priority=5),
            make_article(link=f"{base}?ref=twitter", source="Feed B", priority=8),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_seen = Path(tmpdir) / "seen_links.json"
            with mock.patch.object(curator, "SEEN_LINKS_FILE", temp_seen), \
                 mock.patch.object(curator, "_DRY_RUN", True):
                result = curator.curate_articles(articles)

        selected_links = [article["link"] for article in result["selected"]]
        self.assertEqual(len(selected_links), 1)
        self.assertEqual(selected_links[0], f"{base}?ref=twitter")

    def test_title_similarity_dedup_collapses_near_duplicates(self):
        articles = [
            make_article(
                title="iRacing 2026 season update adds new cars and tracks",
                link="https://example.com/a",
                source="Feed A",
                priority=7,
            ),
            make_article(
                title="iRacing 2026 season update adds new car and track",
                link="https://example.com/b",
                source="Feed B",
                priority=9,
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_seen = Path(tmpdir) / "seen_links.json"
            with mock.patch.object(curator, "SEEN_LINKS_FILE", temp_seen), \
                 mock.patch.object(curator, "_DRY_RUN", True):
                result = curator.curate_articles(articles)

        self.assertEqual(len(result["selected"]), 1)
        self.assertEqual(result["selected"][0]["link"], "https://example.com/b")

    def test_distinct_titles_survive_similarity_filter(self):
        articles = [
            make_article(
                title="iRacing update adds rain tyre changes",
                link="https://example.com/a",
                source="Feed A",
            ),
            make_article(
                title="Assetto Corsa EVO cockpit UI redesign explained",
                link="https://example.com/b",
                source="Feed B",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_seen = Path(tmpdir) / "seen_links.json"
            with mock.patch.object(curator, "SEEN_LINKS_FILE", temp_seen), \
                 mock.patch.object(curator, "_DRY_RUN", True):
                result = curator.curate_articles(articles)

        self.assertEqual(len(result["selected"]), 2)

    def test_recent_seen_links_suppress_repeated_content(self):
        article = make_article(link="https://example.com/repeat")
        now_iso = datetime.now(timezone.utc).isoformat()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_seen = Path(tmpdir) / "seen_links.json"
            temp_seen.write_text(
                json.dumps({
                    "example.com/repeat": {
                        "ts": now_iso,
                        "source": "Older Feed",
                        "title": "Older title",
                    }
                }),
                encoding="utf-8",
            )
            with mock.patch.object(curator, "SEEN_LINKS_FILE", temp_seen), \
                 mock.patch.object(curator, "_DRY_RUN", True):
                result = curator.curate_articles([article])

        self.assertEqual(result["selected"], [])

    def test_stale_seen_links_do_not_block_current_story(self):
        article = make_article(link="https://example.com/repeat")
        old_iso = (datetime.now(timezone.utc) - timedelta(hours=curator.SEEN_LINKS_MAX_AGE_HOURS + 24)).isoformat()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_seen = Path(tmpdir) / "seen_links.json"
            temp_seen.write_text(
                json.dumps({
                    "example.com/repeat": {
                        "ts": old_iso,
                        "source": "Older Feed",
                        "title": "Older title",
                    }
                }),
                encoding="utf-8",
            )
            with mock.patch.object(curator, "SEEN_LINKS_FILE", temp_seen), \
                 mock.patch.object(curator, "_DRY_RUN", True):
                result = curator.curate_articles([article])

        self.assertEqual(len(result["selected"]), 1)

    def test_corrupt_seen_links_non_dict_json_is_tolerated(self):
        article = make_article(link="https://example.com/repeat")

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_seen = Path(tmpdir) / "seen_links.json"
            temp_seen.write_text("[]", encoding="utf-8")
            with mock.patch.object(curator, "SEEN_LINKS_FILE", temp_seen), \
                 mock.patch.object(curator, "_DRY_RUN", True):
                result = curator.curate_articles([article])

        self.assertEqual(len(result["selected"]), 1)

    def test_youtube_source_cap_is_respected(self):
        articles = [
            make_article(
                title="Sim racing update one",
                link="https://youtube.com/watch?v=1",
                source="YT Jimmy Broadbent",
                summary="Long enough YouTube summary with useful sim racing context.",
            ),
            make_article(
                title="Sim racing update two",
                link="https://youtube.com/watch?v=2",
                source="YT Jimmy Broadbent",
                summary="Another long enough YouTube summary with useful sim racing context.",
            ),
            make_article(
                title="Assetto Corsa EVO patch review",
                link="https://example.com/non-youtube",
                source="Feed B",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_seen = Path(tmpdir) / "seen_links.json"
            with mock.patch.object(curator, "SEEN_LINKS_FILE", temp_seen), \
                 mock.patch.object(curator, "_DRY_RUN", True):
                result = curator.curate_articles(articles)

        youtube_selected = [a for a in result["selected"] if a["source"] == "YT Jimmy Broadbent"]
        self.assertLessEqual(len(youtube_selected), 1)

    def test_mixed_noisy_pool_still_returns_valid_structure(self):
        articles = [
            make_article(
                title="Moza review and sim racing update",
                link="https://example.com/good",
                source="Feed A",
            ),
            make_article(
                title="Livery Pack Release",
                link="https://example.com/low-value",
                source="Feed B",
                summary="Low value cosmetic pack only.",
            ),
            make_article(
                title="Moza review and sim racing update",
                link="https://example.com/good?utm_source=newsletter",
                source="Feed C",
                priority=9,
            ),
            {"title": None, "link": "https://example.com/bad-shape", "source": "Feed D", "summary": "text"},
            "bad-shape",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_seen = Path(tmpdir) / "seen_links.json"
            with mock.patch.object(curator, "SEEN_LINKS_FILE", temp_seen), \
                 mock.patch.object(curator, "_DRY_RUN", True):
                result = curator.curate_articles(articles)

        self.assertIn("selected", result)
        self.assertIn("categories", result)
        self.assertGreaterEqual(len(result["selected"]), 1)


if __name__ == "__main__":
    unittest.main()
