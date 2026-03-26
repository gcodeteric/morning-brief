"""
SimulaNewsMachine — Email digest delivery.

Gera um email mobile-friendly com a selecção final, anexando o brief em
Markdown e opcionalmente os social cards.
"""

import html
import json
import logging
import smtplib
from datetime import datetime
from pathlib import Path
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _safe_read_text(path: Path) -> str:
    """Lê texto com tolerância a falhas."""
    try:
        path = Path(path)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _attach_file(msg, file_path: Path, mime_subtype="octet-stream"):
    """Anexa um ficheiro sem propagar falhas para o caller."""
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return

        part = MIMEBase("application", mime_subtype)
        with open(file_path, "rb") as f:
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{file_path.name}"',
        )
        msg.attach(part)
    except Exception as e:
        logger.warning(f"Email digest: falha ao anexar {file_path}: {e}")


def _build_subject(date_str: str) -> str:
    return f"Simula Daily Content Pack — {date_str}"


def _article_line(article: dict) -> str:
    article = article or {}
    title = article.get("title") or "Sem título"
    source = article.get("source") or "Fonte desconhecida"
    score = article.get("score", 0)
    link = article.get("link") or ""
    return f"{title} | {source} | Score: {score} | {link}"


def _digest_story_line(index: int, article: dict, slide: dict | None = None) -> str:
    article = article or {}
    slide = slide or {}
    news_title = slide.get("news_title") or article.get("title") or "Sem título"
    mini_summary = slide.get("mini_summary") or (article.get("summary") or "")[:120]
    why_it_matters = slide.get("why_it_matters") or ""
    parts = [f"{index}. {news_title}"]
    if mini_summary:
        parts.append(f"Resumo: {mini_summary}")
    if why_it_matters:
        parts.append(f"Porque importa: {why_it_matters}")
    return " | ".join(parts)


def build_email_digest(curated, plan, output_path, card_paths=None) -> dict:
    curated = curated or {}
    plan = plan or {}
    card_paths = card_paths or {}

    output_path = Path(output_path)
    date_str = datetime.now().strftime("%d/%m/%Y")
    subject = _build_subject(date_str)
    agent_outputs = curated.get("agent_outputs", []) or []
    markdown_text = _safe_read_text(output_path)

    def _find_agent_output(article):
        if not article:
            return {}
        article_link = article.get("link") or ""
        article_title = article.get("title") or ""

        for output in agent_outputs:
            output_article = output.get("article") or {}
            if article_link and output_article.get("link") == article_link:
                return output
        for output in agent_outputs:
            output_article = output.get("article") or {}
            if article_title and output_article.get("title") == article_title:
                return output
        return {}

    def _parse_qa(output):
        qa_raw = (output or {}).get("qa") or ""
        if not qa_raw:
            return {"hashtags": [], "issues": [], "average": "N/A", "approved": False}
        try:
            qa_data = json.loads(qa_raw)
            return {
                "hashtags": [str(tag) for tag in qa_data.get("hashtags", []) if tag],
                "issues": [str(issue) for issue in qa_data.get("issues", []) if issue],
                "average": qa_data.get("average", "N/A"),
                "approved": qa_data.get("approved", False),
            }
        except Exception:
            return {"hashtags": [], "issues": [], "average": "N/A", "approved": False}

    def _text_instagram_digest_block(label, digest_articles, digest_output):
        digest_articles = digest_articles or []
        digest_output = digest_output or {}
        pack = digest_output.get("instagram_pack", {}) if isinstance(digest_output, dict) else {}
        qa = _parse_qa(digest_output)
        slides = pack.get("slides", []) if isinstance(pack, dict) else []

        lines = [label]
        if not digest_articles:
            lines.append("Sem digest selecionado.")
            return "\n".join(lines)

        lines.append(f"Tema: {pack.get('digest_theme', 'N/A')}")
        lines.append(f"Cover Hook: {pack.get('cover_hook', 'N/A')}")
        lines.append("Stories do digest:")
        for i, article in enumerate(digest_articles[:7], 1):
            slide = slides[i - 1] if i - 1 < len(slides) and isinstance(slides[i - 1], dict) else {}
            lines.append(_digest_story_line(i, article, slide))
        if pack.get("community_question"):
            lines.append("")
            lines.append(f"Pergunta final: {pack.get('community_question')}")
        if digest_output.get("post"):
            lines.append("")
            lines.append("Post final:")
            lines.append(digest_output.get("post", ""))
        if qa.get("hashtags"):
            lines.append("")
            lines.append("Hashtags:")
            lines.append(" ".join(qa["hashtags"]))
        if digest_output.get("image_prompt"):
            lines.append("")
            lines.append("Prompt de imagem (agente image_director):")
            lines.append(digest_output.get("image_prompt", ""))
        if digest_output.get("voice_script"):
            lines.append("")
            lines.append("Script de voz (agente voice_director):")
            lines.append(digest_output.get("voice_script", ""))
        return "\n".join(lines)

    def _html_instagram_digest_block(label, digest_articles, digest_output):
        digest_articles = digest_articles or []
        digest_output = digest_output or {}
        pack = digest_output.get("instagram_pack", {}) if isinstance(digest_output, dict) else {}
        qa = _parse_qa(digest_output)
        slides = pack.get("slides", []) if isinstance(pack, dict) else []

        if not digest_articles:
            return (
                f'<div style="padding:12px 0;border-bottom:1px solid #ddd;">'
                f'<h2 style="font-size:18px;margin:0 0 8px 0;">{html.escape(label)}</h2>'
                f'<p style="margin:0;color:#444;">Sem digest selecionado.</p>'
                f"</div>"
            )

        parts = [
            '<div style="padding:12px 0;border-bottom:1px solid #ddd;">',
            f'<h2 style="font-size:18px;margin:0 0 8px 0;">{html.escape(label)}</h2>',
            f'<p style="margin:0 0 6px 0;"><strong>Tema:</strong> '
            f'{html.escape(pack.get("digest_theme", "N/A"))}</p>',
            f'<p style="margin:0 0 10px 0;"><strong>Cover Hook:</strong> '
            f'{html.escape(pack.get("cover_hook", "N/A"))}</p>',
            '<p style="margin:0 0 6px 0;"><strong>Stories do digest</strong></p>',
        ]

        for i, article in enumerate(digest_articles[:7], 1):
            slide = slides[i - 1] if i - 1 < len(slides) and isinstance(slides[i - 1], dict) else {}
            parts.append(
                f'<p style="margin:0 0 8px 0;color:#444;">'
                f'{html.escape(_digest_story_line(i, article, slide))}</p>'
            )

        if pack.get("community_question"):
            parts.append(
                f'<p style="margin:8px 0 6px 0;"><strong>Pergunta final:</strong> '
                f'{html.escape(pack.get("community_question", ""))}</p>'
            )
        if digest_output.get("post"):
            parts.append('<p style="margin:8px 0 4px 0;"><strong>Post final</strong></p>')
            parts.append(
                f'<p style="margin:0 0 8px 0;white-space:pre-wrap;">'
                f'{html.escape(digest_output.get("post", ""))}</p>'
            )
        if qa.get("hashtags"):
            parts.append('<p style="margin:8px 0 4px 0;"><strong>Hashtags</strong></p>')
            parts.append(
                f'<p style="margin:0 0 8px 0;color:#444;">'
                f'{html.escape(" ".join(qa["hashtags"]))}</p>'
            )
        if digest_output.get("image_prompt"):
            parts.append('<p style="margin:8px 0 4px 0;"><strong>Prompt de imagem (agente)</strong></p>')
            parts.append(
                f'<p style="margin:0 0 8px 0;white-space:pre-wrap;color:#444;">'
                f'{html.escape(digest_output.get("image_prompt", ""))}</p>'
            )
        if digest_output.get("voice_script"):
            parts.append('<p style="margin:8px 0 4px 0;"><strong>Script de voz (agente)</strong></p>')
            parts.append(
                f'<p style="margin:0;white-space:pre-wrap;color:#444;">'
                f'{html.escape(digest_output.get("voice_script", ""))}</p>'
            )
        parts.append("</div>")
        return "".join(parts)

    def _text_channel_block(label, article):
        lines = [label]
        if not article:
            lines.append("Sem artigo selecionado.")
            return "\n".join(lines)

        lines.append(_article_line(article))
        output = _find_agent_output(article)
        qa = _parse_qa(output)

        if output.get("post"):
            lines.append("")
            lines.append("Post final:")
            lines.append(output.get("post", ""))
        if qa.get("hashtags"):
            lines.append("")
            lines.append("Hashtags:")
            lines.append(" ".join(qa["hashtags"]))
        if output.get("image_prompt"):
            lines.append("")
            lines.append("Prompt de imagem:")
            lines.append(output.get("image_prompt", ""))
        if output.get("voice_script"):
            lines.append("")
            lines.append("Script de voz:")
            lines.append(output.get("voice_script", ""))

        return "\n".join(lines)

    def _html_channel_block(label, article):
        if not article:
            return (
                f'<div style="padding:12px 0;border-bottom:1px solid #ddd;">'
                f'<h2 style="font-size:18px;margin:0 0 8px 0;">{html.escape(label)}</h2>'
                f'<p style="margin:0;color:#444;">Sem artigo selecionado.</p>'
                f"</div>"
            )

        output = _find_agent_output(article)
        qa = _parse_qa(output)
        title = html.escape(article.get("title") or "Sem título")
        source = html.escape(article.get("source") or "Fonte desconhecida")
        category = html.escape(article.get("category") or "unknown")
        score = html.escape(str(article.get("score", 0)))
        link = article.get("link") or ""
        link_html = html.escape(link)

        parts = [
            '<div style="padding:12px 0;border-bottom:1px solid #ddd;">',
            f'<h2 style="font-size:18px;margin:0 0 8px 0;">{html.escape(label)}</h2>',
            f'<p style="margin:0 0 6px 0;"><strong>{title}</strong></p>',
            f'<p style="margin:0 0 6px 0;color:#444;">{source} | {category} | Score: {score}</p>',
        ]
        if link:
            parts.append(
                f'<p style="margin:0 0 10px 0;"><a href="{link_html}" '
                'style="color:#b00020;text-decoration:none;">Abrir link</a></p>'
            )
        if output.get("post"):
            parts.append('<p style="margin:8px 0 4px 0;"><strong>Post final</strong></p>')
            parts.append(
                f'<p style="margin:0 0 8px 0;white-space:pre-wrap;">'
                f'{html.escape(output.get("post", ""))}</p>'
            )
        if qa.get("hashtags"):
            parts.append('<p style="margin:8px 0 4px 0;"><strong>Hashtags</strong></p>')
            parts.append(
                f'<p style="margin:0 0 8px 0;color:#444;">'
                f'{html.escape(" ".join(qa["hashtags"]))}</p>'
            )
        if output.get("image_prompt"):
            parts.append('<p style="margin:8px 0 4px 0;"><strong>Prompt de imagem</strong></p>')
            parts.append(
                f'<p style="margin:0 0 8px 0;white-space:pre-wrap;color:#444;">'
                f'{html.escape(output.get("image_prompt", ""))}</p>'
            )
        if output.get("voice_script"):
            parts.append('<p style="margin:8px 0 4px 0;"><strong>Script de voz</strong></p>')
            parts.append(
                f'<p style="margin:0;white-space:pre-wrap;color:#444;">'
                f'{html.escape(output.get("voice_script", ""))}</p>'
            )
        parts.append("</div>")
        return "".join(parts)

    morning_digest = plan.get("instagram_morning_digest", []) or []
    afternoon_digest = plan.get("instagram_afternoon_digest", []) or []
    morning_output = plan.get("instagram_morning_output", {}) or {}
    afternoon_output = plan.get("instagram_afternoon_output", {}) or {}
    has_instagram_digests = bool(morning_digest or afternoon_digest)

    channels = [
        ("X/Twitter — Thread 1", plan.get("x_thread_1")),
        ("X/Twitter — Thread 2", plan.get("x_thread_2")),
        ("YouTube — Daily", plan.get("youtube_daily")),
        ("Discord", plan.get("discord_post")),
    ]
    if not has_instagram_digests:
        channels = [
            ("Instagram — Sim Racing", plan.get("instagram_sim_racing")),
            ("Instagram — Motorsport", plan.get("instagram_motorsport")),
            *channels,
        ]
    reddit_candidates = plan.get("reddit_candidates", []) or []
    overrides = plan.get("override_summary") or {}

    markdown_attachment = output_path if output_path.exists() else None
    card_attachments = []
    for path in card_paths.values():
        if path:
            card_path = Path(path)
            if card_path.exists() and card_path not in card_attachments:
                card_attachments.append(card_path)

    attachments = []
    if markdown_attachment:
        attachments.append(markdown_attachment)
    attachments.extend(card_attachments)

    text_parts = [
        subject,
        "",
        f"Data: {date_str}",
    ]
    if overrides:
        text_parts.append("Overrides aplicados:")
        for channel, choice in overrides.items():
            text_parts.append(f"- {channel}: alternativa {choice}")
    else:
        text_parts.append("Overrides aplicados: nenhum")

    if has_instagram_digests:
        text_parts.append("")
        text_parts.append(_text_instagram_digest_block(
            "Instagram — Morning Digest Carousel",
            morning_digest,
            morning_output,
        ))
        text_parts.append("")
        text_parts.append(_text_instagram_digest_block(
            "Instagram — Afternoon Digest Carousel",
            afternoon_digest,
            afternoon_output,
        ))

    for label, article in channels:
        text_parts.append("")
        text_parts.append(_text_channel_block(label, article))

    text_parts.append("")
    text_parts.append("Reddit")
    if reddit_candidates:
        for article in reddit_candidates:
            text_parts.append(_article_line(article))
    else:
        text_parts.append("Sem artigos elegíveis.")

    text_parts.append("")
    text_parts.append("Cards gerados")
    if card_attachments:
        for card_path in card_attachments:
            text_parts.append(str(card_path))
    else:
        text_parts.append("Sem cards gerados.")

    text_parts.append("")
    text_parts.append("Ficheiro markdown anexado")
    if markdown_attachment:
        text_parts.append(str(markdown_attachment))
        if markdown_text:
            text_parts.append("Markdown final disponível e anexado.")
    else:
        text_parts.append("Markdown não disponível.")

    html_parts = [
        '<html><body style="margin:0;padding:16px;background:#ffffff;color:#111;'
        'font-family:Arial,Helvetica,sans-serif;line-height:1.45;">',
        f'<h1 style="font-size:22px;margin:0 0 8px 0;">{html.escape(subject)}</h1>',
        f'<p style="margin:0 0 16px 0;color:#444;">Data: {html.escape(date_str)}</p>',
    ]
    if overrides:
        html_parts.append(
            '<div style="padding:12px;background:#f6f6f6;border:1px solid #ddd;'
            'margin-bottom:16px;">'
            '<strong>Overrides aplicados</strong>'
        )
        for channel, choice in overrides.items():
            html_parts.append(
                f'<p style="margin:6px 0 0 0;">{html.escape(channel)}: '
                f'alternativa {html.escape(str(choice))}</p>'
            )
        html_parts.append("</div>")
    else:
        html_parts.append(
            '<p style="margin:0 0 16px 0;color:#444;">Overrides aplicados: nenhum</p>'
        )

    if has_instagram_digests:
        html_parts.append(_html_instagram_digest_block(
            "Instagram — Morning Digest Carousel",
            morning_digest,
            morning_output,
        ))
        html_parts.append(_html_instagram_digest_block(
            "Instagram — Afternoon Digest Carousel",
            afternoon_digest,
            afternoon_output,
        ))

    for label, article in channels:
        html_parts.append(_html_channel_block(label, article))

    html_parts.append('<div style="padding:12px 0;border-bottom:1px solid #ddd;">')
    html_parts.append('<h2 style="font-size:18px;margin:0 0 8px 0;">Reddit</h2>')
    if reddit_candidates:
        for article in reddit_candidates:
            line = _article_line(article)
            html_parts.append(
                f'<p style="margin:0 0 8px 0;color:#444;">{html.escape(line)}</p>'
            )
    else:
        html_parts.append('<p style="margin:0;color:#444;">Sem artigos elegíveis.</p>')
    html_parts.append("</div>")

    html_parts.append('<div style="padding:12px 0;border-bottom:1px solid #ddd;">')
    html_parts.append('<h2 style="font-size:18px;margin:0 0 8px 0;">Cards gerados</h2>')
    if card_attachments:
        for card_path in card_attachments:
            html_parts.append(
                f'<p style="margin:0 0 6px 0;color:#444;">{html.escape(str(card_path))}</p>'
            )
    else:
        html_parts.append('<p style="margin:0;color:#444;">Sem cards gerados.</p>')
    html_parts.append("</div>")

    html_parts.append('<div style="padding:12px 0;">')
    html_parts.append('<h2 style="font-size:18px;margin:0 0 8px 0;">Markdown final</h2>')
    if markdown_attachment:
        html_parts.append(
            f'<p style="margin:0 0 6px 0;color:#444;">Anexo: '
            f'{html.escape(str(markdown_attachment))}</p>'
        )
    else:
        html_parts.append('<p style="margin:0;color:#444;">Markdown não disponível.</p>')
    html_parts.append("</div>")
    html_parts.append("</body></html>")

    return {
        "subject": subject,
        "text_body": "\n".join(text_parts).strip(),
        "html_body": "".join(html_parts),
        "attachments": attachments,
        "markdown_attachment": markdown_attachment,
        "card_attachments": card_attachments,
    }


def send_email_digest(digest: dict, smtp_config: dict) -> bool:
    digest = digest or {}
    smtp_config = smtp_config or {}

    required = {
        "host": smtp_config.get("host"),
        "port": smtp_config.get("port"),
        "user": smtp_config.get("user"),
        "password": smtp_config.get("password"),
        "from": smtp_config.get("from"),
        "to": smtp_config.get("to"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        logger.info(f"Email digest: configuração SMTP incompleta ({', '.join(missing)})")
        return False

    recipients = [
        item.strip()
        for item in str(smtp_config.get("to", "")).replace(";", ",").split(",")
        if item.strip()
    ]
    if not recipients:
        logger.info("Email digest: destinatário vazio")
        return False

    msg = MIMEMultipart("mixed")
    msg["Subject"] = digest.get("subject", _build_subject(datetime.now().strftime("%d/%m/%Y")))
    msg["From"] = smtp_config.get("from", "")
    msg["To"] = ", ".join(recipients)

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(digest.get("text_body", ""), "plain", "utf-8"))
    alternative.attach(MIMEText(digest.get("html_body", ""), "html", "utf-8"))
    msg.attach(alternative)

    if smtp_config.get("attach_markdown", True):
        markdown_attachment = digest.get("markdown_attachment")
        if markdown_attachment:
            _attach_file(msg, Path(markdown_attachment), "markdown")

    if smtp_config.get("attach_cards", True):
        for card_path in digest.get("card_attachments", []):
            suffix = Path(card_path).suffix.lower().lstrip(".") or "octet-stream"
            _attach_file(msg, Path(card_path), suffix)

    try:
        with smtplib.SMTP(
            smtp_config.get("host"),
            int(smtp_config.get("port", 587)),
            timeout=20,
        ) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(
                smtp_config.get("user", ""),
                smtp_config.get("password", ""),
            )
            server.sendmail(
                smtp_config.get("from", ""),
                recipients,
                msg.as_string(),
            )
        return True
    except Exception as e:
        logger.warning(f"Email digest envio falhou: {e}")
        return False
