import json
import unittest
from unittest import mock

import agents


def make_article():
    return {
        "title": "Headline",
        "source": "Source",
        "summary": "Resumo da notícia",
        "score": 80,
        "link": "https://example.com/story",
        "category": "sim_racing",
    }


class _FakeCompletions:
    def __init__(self, exc):
        self.exc = exc

    def create(self, **kwargs):
        raise self.exc


class _FakeChat:
    def __init__(self, exc):
        self.completions = _FakeCompletions(exc)


class _FakeClient:
    def __init__(self, exc):
        self.chat = _FakeChat(exc)


class AgentPipelineTests(unittest.TestCase):
    def test_run_full_pipeline_handles_valid_structured_json(self):
        qa_payload = json.dumps({
            "approved": False,
            "average": 6.5,
            "hashtags": ["#simula"],
            "improved_post": json.dumps({
                "format": "carousel_explainer",
                "cover_hook": "Hook Melhorado",
                "slides": ["Slide A", "Slide B"],
                "caption": "Caption melhorada",
                "community_question": "Concordas?",
                "cta_style": "implicit",
                "notes_for_design": "clean",
            }),
        })
        with mock.patch.object(
            agents,
            "run_agent",
            side_effect=[
                '{"content_type":"NOTÍCIA GERAL"}',
                json.dumps({
                    "format": "carousel_explainer",
                    "cover_hook": "Hook Inicial",
                    "slides": ["Slide 1"],
                    "caption": "Caption",
                    "community_question": "Pergunta?",
                    "cta_style": "implicit",
                    "notes_for_design": "clean",
                }),
                "Prompt de imagem",
                "Script de voz",
                qa_payload,
            ],
        ):
            result = agents.run_full_pipeline(make_article())

        self.assertEqual(result["instagram_pack"]["cover_hook"], "Hook Melhorado")
        self.assertIn("Cover Hook: Hook Melhorado", result["post"])
        self.assertEqual(result["image_prompt"], "Prompt de imagem")
        self.assertEqual(result["voice_script"], "Script de voz")

    def test_run_full_pipeline_invalid_json_falls_back_to_raw_post(self):
        with mock.patch.object(
            agents,
            "run_agent",
            side_effect=[
                '{"content_type":"NOTÍCIA GERAL"}',
                "not-json",
                "",
                "",
                '{"approved": true, "average": 8.0}',
            ],
        ):
            result = agents.run_full_pipeline(make_article())

        self.assertEqual(result["post"], "not-json")
        self.assertEqual(result["instagram_pack"], {})

    def test_run_instagram_digest_pipeline_reparses_structured_improved_post(self):
        digest = [
            {**make_article(), "title": "Story 1"},
            {**make_article(), "title": "Story 2", "link": "https://example.com/story-2"},
            {**make_article(), "title": "Story 3", "link": "https://example.com/story-3"},
            {**make_article(), "title": "Story 4", "link": "https://example.com/story-4"},
        ]
        improved_payload = json.dumps({
            "approved": False,
            "average": 6.1,
            "improved_post": json.dumps({
                "format": "editorial_digest_carousel",
                "cover_hook": "Digest Melhorado",
                "digest_theme": "Tema",
                "slides": [
                    {"news_title": "A", "mini_summary": "B", "why_it_matters": "C"},
                    {"news_title": "D", "mini_summary": "E", "why_it_matters": "F"},
                ],
                "caption_intro": "Intro",
                "caption_news_list": ["1. A", "2. D"],
                "community_question": "Qual pesa mais?",
                "cta_style": "implicit",
                "notes_for_design": "forte",
            }),
        })
        with mock.patch.object(
            agents,
            "run_agent",
            side_effect=[
                '{"digest_theme":"Tema","digest_type":"morning_digest"}',
                json.dumps({
                    "format": "editorial_digest_carousel",
                    "cover_hook": "Hook",
                    "digest_theme": "Tema",
                    "slides": [{"news_title": "A", "mini_summary": "B", "why_it_matters": "C"}],
                    "caption_intro": "Intro",
                    "caption_news_list": ["1. A"],
                    "community_question": "Pergunta?",
                    "cta_style": "implicit",
                    "notes_for_design": "clean",
                }),
                "Image prompt",
                "Voice script",
                improved_payload,
            ],
        ):
            result = agents.run_instagram_digest_pipeline(digest, "morning_digest")

        self.assertEqual(result["instagram_pack"]["cover_hook"], "Digest Melhorado")
        self.assertIn("Digest Melhorado", result["post"])

    def test_run_instagram_digest_pipeline_empty_digest_is_safe(self):
        result = agents.run_instagram_digest_pipeline([], "afternoon_digest")
        self.assertEqual(result["articles"], [])
        self.assertEqual(result["instagram_pack"], {})
        self.assertEqual(result["agent_metrics"]["scope"], "instagram_digest")

    def test_run_agent_timeout_path_is_safe(self):
        metrics = agents._new_agent_metrics("single_article")
        fake_client = _FakeClient(TimeoutError("request timed out"))
        with mock.patch.object(agents, "MINIMAX_API_KEY", "configured"), mock.patch.object(agents, "client", fake_client):
            result = agents.run_agent("analyst", "hello", metrics=metrics)

        self.assertEqual(result, "")
        self.assertEqual(metrics["calls_attempted"], 1)
        self.assertEqual(metrics["calls_timed_out"], 1)
        self.assertIn("analyst", metrics["durations"])


if __name__ == "__main__":
    unittest.main()
