import tempfile
import unittest
from pathlib import Path

import email_digest


def make_story(title, category="sim_racing", score=80, link=None):
    slug = title.lower().replace(" ", "-")
    return {
        "title": title,
        "source": "Source",
        "category": category,
        "score": score,
        "summary": f"Resumo {title}",
        "link": link or f"https://example.com/{slug}",
    }


class EmailDigestTests(unittest.TestCase):
    def test_build_email_digest_with_and_without_optional_pieces(self):
        morning = [make_story("Morning One"), make_story("Morning Two", category="nostalgia", link="https://example.com/m2")]
        afternoon = [make_story("Afternoon One", category="motorsport", link="https://example.com/a1")]
        plan = {
            "instagram_morning_digest": morning,
            "instagram_afternoon_digest": afternoon,
            "instagram_morning_output": {
                "instagram_pack": {
                    "digest_theme": "Tema manhã",
                    "cover_hook": "Hook manhã",
                    "slides": [{"news_title": "Morning One", "mini_summary": "Resumo", "why_it_matters": "Importa"}],
                    "community_question": "Quem lidera a manhã?",
                },
                "image_prompt": "Prompt manhã",
                "voice_script": "Voz manhã",
            },
            "instagram_afternoon_output": {
                "instagram_pack": {
                    "digest_theme": "Tema tarde",
                    "cover_hook": "Hook tarde",
                    "slides": [{"news_title": "Afternoon One", "mini_summary": "Resumo", "why_it_matters": "Importa"}],
                    "community_question": "Quem pesa mais na tarde?",
                },
            },
            "x_thread_1": make_story("X One"),
            "x_thread_2": make_story("X Two", link="https://example.com/x2"),
            "youtube_daily": make_story("YT One", link="https://example.com/yt"),
            "reddit_candidates": [make_story("Reddit One", link="https://example.com/reddit")],
            "discord_post": make_story("Discord One", link="https://example.com/discord"),
        }
        curated = {"agent_outputs": []}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "brief.md"
            output_path.write_text("# Brief", encoding="utf-8")
            card_path = Path(tmpdir) / "card.png"
            card_path.write_bytes(b"png")

            digest = email_digest.build_email_digest(
                curated,
                plan,
                output_path,
                {"morning_digest": str(card_path)},
            )

        self.assertIn("Morning Digest", digest["text_body"])
        self.assertIn("Afternoon Digest", digest["html_body"])
        self.assertIn("Hook manhã", digest["text_body"])
        self.assertIn(output_path, digest["attachments"])
        self.assertIn(card_path, digest["attachments"])

    def test_send_email_digest_fails_safely_with_incomplete_smtp_config(self):
        digest = {
            "subject": "Subject",
            "text_body": "Hello",
            "html_body": "<p>Hello</p>",
            "attachments": [],
        }
        smtp_config = {
            "host": "",
            "port": 587,
            "user": "",
            "password": "",
            "from": "",
            "to": "",
            "attach_markdown": True,
            "attach_cards": True,
        }
        self.assertFalse(email_digest.send_email_digest(digest, smtp_config))


if __name__ == "__main__":
    unittest.main()
