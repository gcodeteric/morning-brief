import unittest
from unittest import mock

import planner


def make_article(title, category, score, link=None, source="Source", summary="Resumo curto"):
    slug = title.lower().replace(" ", "-")
    return {
        "title": title,
        "source": source,
        "category": category,
        "score": score,
        "summary": summary,
        "link": link or f"https://example.com/{slug}",
    }


class PlannerTests(unittest.TestCase):
    def test_empty_input_returns_safe_plan(self):
        with mock.patch.object(planner, "_get_youtube_weekly", return_value=[]):
            result = planner.plan({"selected": []})

        self.assertEqual(result["instagram_morning_digest"], [])
        self.assertEqual(result["instagram_afternoon_digest"], [])
        self.assertIsNone(result["x_thread_1"])
        self.assertIsNone(result["x_thread_2"])
        self.assertEqual(result["reddit_candidates"], [])

    def test_one_article_case_does_not_duplicate_secondary_slots(self):
        selected = [make_article("Only Sim Story", "sim_racing", 88)]
        with mock.patch.object(planner, "_get_youtube_weekly", return_value=[]):
            result = planner.plan({"selected": selected})

        self.assertEqual(result["x_thread_1"]["title"], "Only Sim Story")
        self.assertIsNone(result["x_thread_2"])
        self.assertEqual(len(result["instagram_morning_digest"]), 1)
        self.assertEqual(result["instagram_afternoon_digest"], [])

    def test_morning_and_afternoon_digest_creation_and_no_duplicates(self):
        selected = [
            make_article("Sim Rig Update", "sim_racing", 92),
            make_article("Classic Mod Revival", "nostalgia", 80),
            make_article("Racing Games Patch", "racing_games", 78),
            make_article("Portuguese Cup News", "sim_racing", 77, source="Simula Portugal"),
            make_article("F1 Weekend Shake-up", "motorsport", 89),
            make_article("WEC Team Change", "motorsport", 84),
            make_article("MotoGP Strategy", "motorsport", 81),
        ]
        with mock.patch.object(planner, "_get_youtube_weekly", return_value=[]):
            result = planner.plan({"selected": selected})

        morning = result["instagram_morning_digest"]
        afternoon = result["instagram_afternoon_digest"]

        self.assertGreaterEqual(len(morning), 4)
        self.assertLessEqual(len(morning), 7)
        self.assertTrue(all(article["category"] == "motorsport" for article in afternoon))
        self.assertEqual(
            len({article["link"] for article in morning}),
            len(morning),
        )
        self.assertEqual(
            len({article["link"] for article in afternoon}),
            len(afternoon),
        )

    def test_digest_alternatives_are_present_and_distinct_when_possible(self):
        selected = [
            make_article("Sim A", "sim_racing", 95),
            make_article("Sim B", "sim_racing", 90),
            make_article("Nostalgia A", "nostalgia", 88),
            make_article("Games A", "racing_games", 86),
            make_article("Portugal A", "sim_racing", 85, source="Liga Portugal"),
            make_article("Moto A", "motorsport", 91),
            make_article("Moto B", "motorsport", 87),
            make_article("Moto C", "motorsport", 83),
        ]
        with mock.patch.object(planner, "_get_youtube_weekly", return_value=[]):
            result = planner.plan({"selected": selected})

        morning_primary = tuple(article["link"] for article in result["instagram_morning_digest"])
        afternoon_primary = tuple(article["link"] for article in result["instagram_afternoon_digest"])
        morning_alts = [tuple(article["link"] for article in digest) for digest in result["instagram_morning_digest_alternatives"]]
        afternoon_alts = [tuple(article["link"] for article in digest) for digest in result["instagram_afternoon_digest_alternatives"]]

        self.assertLessEqual(len(morning_alts), 2)
        self.assertLessEqual(len(afternoon_alts), 2)
        self.assertNotIn(morning_primary, morning_alts)
        self.assertNotIn(afternoon_primary, afternoon_alts)


if __name__ == "__main__":
    unittest.main()
