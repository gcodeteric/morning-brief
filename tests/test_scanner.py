import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import requests

import scanner


def make_feed(name="Feed A", url="https://example.com/feed", category="sim_racing", priority=8):
    return {"url": url, "name": name, "cat": category, "p": priority}


def make_entry(
    title="Valid Story",
    link="https://example.com/story",
    summary="<p>Resumo <b>útil</b></p>",
    published=None,
):
    return {
        "title": title,
        "link": link,
        "summary": summary,
        "published": published or datetime.now(timezone.utc).isoformat(),
    }


def make_parsed(entries=None, bozo=False, bozo_exception=None):
    return types.SimpleNamespace(
        entries=entries or [],
        bozo=bozo,
        bozo_exception=bozo_exception,
    )


class _FakeResponse:
    def __init__(self, content=b"<rss></rss>"):
        self.content = content

    def raise_for_status(self):
        return None


class ScannerTests(unittest.TestCase):
    def test_scan_all_feeds_aggregates_ok_empty_fail_and_api_articles(self):
        feeds = [
            make_feed(name="OK Feed"),
            make_feed(name="Empty Feed", url="https://example.com/empty"),
            make_feed(name="Fail Feed", url="https://example.com/fail"),
        ]
        ok_article = {
            "title": "From Feed",
            "link": "https://example.com/feed-story",
            "summary": "Resumo",
            "published": datetime.now(timezone.utc).isoformat(),
            "source": "OK Feed",
            "category": "sim_racing",
            "priority": 8,
            "no_date": False,
        }
        api_article = {
            "title": "From API",
            "link": "https://example.com/api-story",
            "summary": "Resumo API",
            "published": datetime.now(timezone.utc).isoformat(),
            "source": "API",
            "category": "motorsport",
            "priority": 3,
            "no_date": False,
        }

        with mock.patch.object(scanner, "get_all_feeds", return_value=feeds), \
             mock.patch.object(
                 scanner,
                 "_scan_single_feed",
                 side_effect=[
                     {"status": "OK", "articles": [ok_article], "error": None},
                     {"status": "EMPTY", "articles": [], "error": None},
                     {"status": "FAIL", "articles": [], "error": "boom"},
                 ],
             ), \
             mock.patch("news_sources.fetch_all_api_sources", return_value=[api_article]):
            articles, stats = scanner.scan_all_feeds()

        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["ok"], 1)
        self.assertEqual(stats["empty"], 1)
        self.assertEqual(stats["fail"], 1)
        self.assertEqual(stats["failed_names"], ["Fail Feed"])
        self.assertEqual(len(articles), 2)
        self.assertEqual({a["title"] for a in articles}, {"From Feed", "From API"})

    def test_scan_all_feeds_api_failure_is_non_critical(self):
        feeds = [make_feed(name="OK Feed")]
        ok_article = {
            "title": "From Feed",
            "link": "https://example.com/feed-story",
            "summary": "Resumo",
            "published": datetime.now(timezone.utc).isoformat(),
            "source": "OK Feed",
            "category": "sim_racing",
            "priority": 8,
            "no_date": False,
        }

        with mock.patch.object(scanner, "get_all_feeds", return_value=feeds), \
             mock.patch.object(
                 scanner,
                 "_scan_single_feed",
                 return_value={"status": "OK", "articles": [ok_article], "error": None},
             ), \
             mock.patch("news_sources.fetch_all_api_sources", side_effect=RuntimeError("api down")):
            articles, stats = scanner.scan_all_feeds()

        self.assertEqual(stats["ok"], 1)
        self.assertEqual(stats["fail"], 0)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["title"], "From Feed")

    def test_scan_single_feed_successful_result_returns_usable_article(self):
        parsed = make_parsed(entries=[make_entry()])
        with mock.patch.object(scanner.requests, "get", return_value=_FakeResponse()), \
             mock.patch.object(scanner.feedparser, "parse", return_value=parsed):
            result = scanner._scan_single_feed(make_feed())

        self.assertEqual(result["status"], "OK")
        self.assertEqual(len(result["articles"]), 1)
        article = result["articles"][0]
        self.assertEqual(article["source"], "Feed A")
        self.assertEqual(article["category"], "sim_racing")
        self.assertEqual(article["priority"], 8)
        self.assertFalse(article["no_date"])
        self.assertIn("Resumo útil", article["summary"])

    def test_scan_single_feed_uses_feedparser_fallback_after_request_failure(self):
        parsed = make_parsed(entries=[make_entry(title="Fallback Story")])
        with mock.patch.object(
            scanner.requests,
            "get",
            side_effect=requests.exceptions.Timeout("timeout"),
        ), \
             mock.patch.object(scanner.feedparser, "parse", return_value=parsed):
            result = scanner._scan_single_feed(make_feed())

        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["articles"][0]["title"], "Fallback Story")

    def test_scan_single_feed_malformed_entry_does_not_fail_entire_feed(self):
        valid = make_entry(title="Valid Story", link="https://example.com/valid")
        malformed = {
            "title": None,
            "link": "https://example.com/bad",
            "summary": "bad entry",
            "published": datetime.now(timezone.utc).isoformat(),
        }
        parsed = make_parsed(entries=[valid, malformed])

        with mock.patch.object(scanner.requests, "get", return_value=_FakeResponse()), \
             mock.patch.object(scanner.feedparser, "parse", return_value=parsed):
            result = scanner._scan_single_feed(make_feed())

        self.assertEqual(result["status"], "OK")
        self.assertEqual(len(result["articles"]), 1)
        self.assertEqual(result["articles"][0]["title"], "Valid Story")

    def test_scan_single_feed_malformed_feed_returns_fail(self):
        malformed = make_parsed(entries=[], bozo=True, bozo_exception=ValueError("broken xml"))
        with mock.patch.object(scanner.requests, "get", return_value=_FakeResponse()), \
             mock.patch.object(scanner.feedparser, "parse", return_value=malformed):
            result = scanner._scan_single_feed(make_feed())

        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["articles"], [])

    def test_scan_single_feed_skips_future_and_too_old_entries(self):
        now = datetime.now(timezone.utc)
        future = make_entry(
            title="Future Story",
            link="https://example.com/future",
            published=(now + timedelta(hours=5)).isoformat(),
        )
        old = make_entry(
            title="Old Story",
            link="https://example.com/old",
            published=(now - timedelta(hours=scanner.HOURS_LOOKBACK + 5)).isoformat(),
        )
        fresh = make_entry(
            title="Fresh Story",
            link="https://example.com/fresh",
            published=now.isoformat(),
        )
        parsed = make_parsed(entries=[future, old, fresh])

        with mock.patch.object(scanner.requests, "get", return_value=_FakeResponse()), \
             mock.patch.object(scanner.feedparser, "parse", return_value=parsed):
            result = scanner._scan_single_feed(make_feed())

        self.assertEqual(result["status"], "OK")
        self.assertEqual([a["title"] for a in result["articles"]], ["Fresh Story"])


if __name__ == "__main__":
    unittest.main()
