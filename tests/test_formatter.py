import tempfile
import unittest
from pathlib import Path

import formatter


def make_article(title, category, score, link):
    return {
        "title": title,
        "source": "Source",
        "category": category,
        "score": score,
        "summary": f"Resumo de {title}",
        "link": link,
    }


class FormatterTests(unittest.TestCase):
    def test_brief_generation_with_grouped_instagram_sections(self):
        selected = [
            make_article("Sim Story", "sim_racing", 90, "https://example.com/sim"),
            make_article("Moto Story", "motorsport", 85, "https://example.com/moto"),
            make_article("Game Story", "racing_games", 76, "https://example.com/game"),
            make_article("Nostalgia Story", "nostalgia", 72, "https://example.com/retro"),
        ]
        curated = {
            "selected": selected,
            "categories": {"sim_racing": 1, "motorsport": 1, "racing_games": 1, "nostalgia": 1},
            "total_before_dedup": 6,
            "total_after_dedup": 4,
            "agent_outputs": [
                {
                    "article": selected[0],
                    "post": "Post gerado",
                    "qa": '{"average": 8.0, "approved": true, "hashtags": ["#simula"]}',
                    "image_prompt": "Prompt visual",
                    "voice_script": "Script voz",
                    "instagram_pack": {
                        "format": "carousel_explainer",
                        "cover_hook": "Hook",
                        "slides": ["Slide 1", "Slide 2"],
                        "caption": "Caption",
                        "community_question": "Pergunta?",
                        "notes_for_design": "clean",
                    },
                }
            ],
        }
        plan = {
            "instagram_morning_digest": selected[:3],
            "instagram_morning_digest_alternatives": [selected[1:4]],
            "instagram_afternoon_digest": [selected[1]],
            "instagram_afternoon_digest_alternatives": [],
            "instagram_morning_output": {
                "instagram_pack": {
                    "digest_theme": "Morning",
                    "cover_hook": "Morning Hook",
                    "slides": [{"news_title": "Sim Story", "mini_summary": "Resumo", "why_it_matters": "Importa"}],
                    "caption_intro": "Bom dia",
                    "caption_news_list": ["1. Sim Story"],
                    "community_question": "O que achas?",
                    "notes_for_design": "clean",
                },
                "image_prompt": "Prompt manhã",
                "voice_script": "Voz manhã",
                "qa": '{"average": 8.3, "approved": true}',
            },
            "instagram_afternoon_output": {
                "instagram_pack": {
                    "digest_theme": "Afternoon",
                    "cover_hook": "Afternoon Hook",
                    "slides": [{"news_title": "Moto Story", "mini_summary": "Resumo", "why_it_matters": "Importa"}],
                    "caption_intro": "Boa tarde",
                    "caption_news_list": ["1. Moto Story"],
                    "community_question": "Quem ganha?",
                    "notes_for_design": "bold",
                },
                "image_prompt": "Prompt tarde",
                "voice_script": "Voz tarde",
                "qa": '{"average": 7.9, "approved": true}',
            },
            "instagram_morning_pack": {},
            "instagram_afternoon_pack": {},
            "x_thread_1": selected[0],
            "x_thread_2": selected[1],
            "youtube_daily": selected[0],
            "youtube_daily_alternatives": [],
            "youtube_weekly": [],
            "reddit_candidates": [selected[0]],
            "discord_post": selected[0],
            "discord_post_alternatives": [],
            "is_sunday": False,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "brief.md"
            formatter.format_brief(curated, output_path, plan=plan, card_paths={})
            content = output_path.read_text(encoding="utf-8")

        self.assertIn("Instagram — Morning Digest", content)
        self.assertIn("Instagram — Afternoon Digest", content)
        self.assertIn("Morning Digest — Agent Output", content)
        self.assertIn("Afternoon Digest — Agent Output", content)
        self.assertIn("Prompt de Imagem", content)
        self.assertIn("Script de Voz", content)

    def test_brief_generation_with_missing_optional_data_does_not_crash(self):
        curated = {
            "selected": [make_article("Only Story", "sim_racing", 80, "https://example.com/only")],
            "categories": {"sim_racing": 1},
            "total_before_dedup": 1,
            "total_after_dedup": 1,
            "agent_outputs": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "brief.md"
            formatter.format_brief(curated, output_path, plan=None, card_paths=None)
            content = output_path.read_text(encoding="utf-8")

        self.assertIn("PROMPT 1 — INSTAGRAM", content)
        self.assertIn("Instagram editorial recommendation", content)

    def test_empty_useless_minimax_section_is_suppressed(self):
        curated = {
            "selected": [make_article("Only Story", "sim_racing", 80, "https://example.com/only")],
            "categories": {"sim_racing": 1},
            "total_before_dedup": 1,
            "total_after_dedup": 1,
            "agent_outputs": [
                {"article": {}, "post": "", "image_prompt": "", "voice_script": "", "instagram_pack": {}},
                {"article": {}, "post": "", "image_prompt": "", "voice_script": "", "instagram_pack": {}},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "brief.md"
            formatter.format_brief(curated, output_path, plan=None, card_paths=None)
            content = output_path.read_text(encoding="utf-8")

        self.assertNotIn("# 🤖 POSTS GERADOS — PIPELINE MINIMAX M2.7", content)

    def test_useful_minimax_section_is_retained(self):
        article = make_article("Only Story", "sim_racing", 80, "https://example.com/only")
        curated = {
            "selected": [article],
            "categories": {"sim_racing": 1},
            "total_before_dedup": 1,
            "total_after_dedup": 1,
            "agent_outputs": [
                {
                    "article": article,
                    "post": "Texto útil",
                    "image_prompt": "",
                    "voice_script": "",
                    "instagram_pack": {},
                    "qa": '{"average": 8.0, "approved": true}',
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "brief.md"
            formatter.format_brief(curated, output_path, plan=None, card_paths=None)
            content = output_path.read_text(encoding="utf-8")

        self.assertIn("# 🤖 POSTS GERADOS — PIPELINE MINIMAX M2.7", content)
        self.assertIn("Texto útil", content)


if __name__ == "__main__":
    unittest.main()
