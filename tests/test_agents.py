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


def make_reader_payload():
    return json.dumps({
        "status": "ok",
        "url": "https://example.com/story",
        "title": "Headline",
        "article_summary": [
            "Linha factual 1",
            "Linha factual 2",
            "Linha factual 3",
        ],
        "key_points": [
            "Facto 1",
            "Facto 2",
            "Facto 3",
        ],
        "angle": "Isto importa para a comunidade.",
        "tone_hint": "community",
    })


def make_copywriter_payload():
    return json.dumps({
        "title": "Headline",
        "url": "https://example.com/story",
        "source": "Source",
        "category": "sim_racing",
        "score": 80,
        "article_summary": [
            "Linha factual 1",
            "Linha factual 2",
            "Linha factual 3",
        ],
        "instagram": {
            "image_text": {
                "hook": "Gancho curto",
                "line_1": "Linha de apoio 1",
                "line_2": "Linha de apoio 2",
            },
            "caption": {
                "title": "Título Insta",
                "body": [
                    "Legenda 1",
                    "Legenda 2",
                    "Legenda 3",
                ],
                "link": "https://example.com/story",
            },
        },
        "x": {
            "post": [
                "Linha X 1",
                "Linha X 2",
                "https://example.com/story",
            ],
        },
        "youtube": {
            "title": "Título YouTube",
            "hook": "Hook curto",
            "description": [
                "Descrição 1",
                "Descrição 2",
                "Descrição 3",
            ],
            "voice_script": [
                "Voz 1",
                "Voz 2",
                "Voz 3",
            ],
        },
        "reddit": {
            "title": "Título Reddit",
            "body": [
                "Reddit 1",
                "Reddit 2",
                "Reddit 3",
            ],
        },
        "discord": {
            "post": [
                "Discord 1",
                "Discord 2",
                "https://example.com/story",
            ],
        },
        "email": {
            "subject": "Assunto Email",
            "body": [
                "Email 1",
                "Email 2",
                "Email 3",
            ],
            "link": "https://example.com/story",
        },
    })


class AgentPipelineTests(unittest.TestCase):
    def test_run_story_platform_pipeline_returns_two_agent_story_shape(self):
        with mock.patch.object(
            agents,
            "_fetch_article_payload",
            return_value={
                "status": "ok",
                "url": "https://example.com/story",
                "title": "Headline",
                "text": "texto suficiente do artigo",
            },
        ), mock.patch.object(
            agents,
            "run_agent",
            side_effect=[make_reader_payload(), make_copywriter_payload()],
        ):
            result = agents.run_story_platform_pipeline(make_article())

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["reader_status"], "ok")
        self.assertEqual(result["copy_status"], "ok")
        self.assertEqual(result["summary_source"], "article_reader")
        self.assertEqual(result["article_summary"][0], "Linha factual 1")
        self.assertEqual(result["instagram"]["image_text"]["hook"], "Gancho curto")
        self.assertEqual(result["instagram"]["caption"]["title"], "Título Insta")
        self.assertEqual(result["x"]["post"][-1], "https://example.com/story")
        self.assertEqual(result["youtube"]["title"], "Título YouTube")
        self.assertEqual(result["reddit"]["title"], "Título Reddit")
        self.assertEqual(result["discord"]["post"][-1], "https://example.com/story")
        self.assertEqual(result["email"]["subject"], "Assunto Email")
        self.assertEqual(result["copywriter_output"]["instagram"]["caption"]["title"], "Título Insta")
        self.assertIsNot(result["copywriter_output"], result)
        self.assertEqual(result["voice_script"], "Voz 1\nVoz 2\nVoz 3")
        self.assertIn("Resumo do artigo:", result["post"])
        self.assertEqual(json.loads(result["analysis"])["reader_status"], "ok")

    def test_run_story_platform_pipeline_handles_inaccessible_article_safely(self):
        with mock.patch.object(
            agents,
            "_fetch_article_payload",
            return_value={
                "status": "cannot_access_article",
                "url": "https://example.com/story",
                "title": "Headline",
                "text": "",
            },
        ), mock.patch.object(agents, "run_agent") as run_agent_mock:
            result = agents.run_story_platform_pipeline(make_article())

        run_agent_mock.assert_not_called()
        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["reader_status"], "cannot_access_article")
        self.assertEqual(result["copy_status"], "metadata_fallback")
        self.assertEqual(result["summary_source"], "metadata_fallback")
        self.assertEqual(result["copywriter_output"], {})
        self.assertEqual(result["instagram"]["caption"]["link"], "https://example.com/story")
        self.assertTrue(result["article_summary"])

    def test_run_story_platform_pipeline_invalid_copywriter_json_falls_back_to_reader_context(self):
        with mock.patch.object(
            agents,
            "_fetch_article_payload",
            return_value={
                "status": "ok",
                "url": "https://example.com/story",
                "title": "Headline",
                "text": "texto suficiente do artigo",
            },
        ), mock.patch.object(
            agents,
            "run_agent",
            side_effect=[make_reader_payload(), "not-json"],
        ):
            result = agents.run_story_platform_pipeline(make_article())

        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["reader_status"], "ok")
        self.assertEqual(result["copy_status"], "copywriter_fallback")
        self.assertEqual(result["summary_source"], "article_reader")
        self.assertEqual(result["raw_post"], "not-json")
        self.assertEqual(result["copywriter_output"], {})
        self.assertEqual(result["article_summary"][0], "Linha factual 1")
        self.assertEqual(result["instagram"]["caption"]["link"], "https://example.com/story")

    def test_run_full_pipeline_is_backward_compatible_wrapper(self):
        expected = {"status": "ok", "title": "Wrapped"}
        with mock.patch.object(agents, "run_story_platform_pipeline", return_value=expected) as pipeline_mock:
            result = agents.run_full_pipeline(make_article())

        pipeline_mock.assert_called_once()
        self.assertIs(result, expected)

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
