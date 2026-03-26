"""SimulaNewsMachine — data access helpers for the internal dashboard."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from config import (
    DATA_DIR,
    RUN_SUMMARY_FILE,
    OUTPUT_FILE,
    DESKTOP,
    PROJECT_DIR,
    GENERATE_IMAGES,
    SEND_EMAIL_DIGEST,
    EMAIL_SMTP_HOST,
    EMAIL_SMTP_USER,
    EMAIL_SMTP_PASSWORD,
    EMAIL_FROM,
    EMAIL_TO,
)

logger = logging.getLogger(__name__)

DASHBOARD_SNAPSHOT_FILE = DATA_DIR / "dashboard_latest_snapshot.json"
MANUAL_OVERRIDES_FILE = DATA_DIR / "manual_overrides.json"
CARDS_DIR = DESKTOP / "SIMULA_CARDS_HOJE"
ASSETS_DIR = PROJECT_DIR / "assets"


def _safe_json_load(path: Path, default):
    try:
        path = Path(path)
        if not path.exists():
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _safe_read_text(path: Path) -> str:
    try:
        path = Path(path)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _json_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _existing_path(path_like) -> str:
    try:
        path = Path(path_like)
        return str(path) if path.exists() else ""
    except Exception:
        return ""


def _bool_configured(*values) -> bool:
    return all(bool(v) for v in values)


def _has_useful_output(output: dict) -> bool:
    output = output or {}
    return any([
        output.get("post"),
        output.get("instagram_pack"),
        output.get("image_prompt"),
        output.get("voice_script"),
    ])


def parse_qa_data(qa_raw) -> dict:
    if not qa_raw:
        return {
            "scores": {},
            "average": "N/A",
            "approved": False,
            "hashtags": [],
            "issues": [],
        }
    try:
        qa_data = json.loads(qa_raw) if isinstance(qa_raw, str) else dict(qa_raw)
        return {
            "scores": qa_data.get("scores", {}) or {},
            "average": qa_data.get("average", "N/A"),
            "approved": qa_data.get("approved", False),
            "hashtags": qa_data.get("hashtags", []) or [],
            "issues": qa_data.get("issues", []) or [],
            "improved_hook": qa_data.get("improved_hook"),
            "improved_post": qa_data.get("improved_post"),
        }
    except Exception:
        return {
            "scores": {},
            "average": "N/A",
            "approved": False,
            "hashtags": [],
            "issues": [],
        }


def save_dashboard_snapshot(curated, plan, card_paths, brief_path, run_summary=None) -> str:
    """Persist a lightweight structured snapshot for the dashboard."""
    try:
        curated = curated or {}
        plan = plan or {}
        card_paths = card_paths or {}
        run_summary = run_summary or {}

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "run_status": run_summary.get("status", "OK"),
            "curated_stories": curated.get("selected", []),
            "curated_categories": curated.get("categories", {}),
            "total_before_dedup": curated.get("total_before_dedup", 0),
            "total_after_dedup": curated.get("total_after_dedup", 0),
            "plan": plan,
            "agent_outputs": curated.get("agent_outputs", []),
            "instagram_morning_pack": plan.get("instagram_morning_pack", {}),
            "instagram_afternoon_pack": plan.get("instagram_afternoon_pack", {}),
            "card_paths": {
                key: _existing_path(value) or str(value)
                for key, value in (card_paths or {}).items()
            },
            "brief_path": str(brief_path) if brief_path else "",
            "override_summary": plan.get("override_summary", {}),
            "manual_overrides_applied": plan.get("manual_overrides_applied", False),
            "run_summary": run_summary,
        }

        with open(DASHBOARD_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(_json_safe(snapshot), f, indent=2, ensure_ascii=False)
        return str(DASHBOARD_SNAPSHOT_FILE)
    except Exception as e:
        logger.warning(f"Dashboard snapshot falhou (não crítico): {e}")
        return ""


def load_dashboard_snapshot() -> dict:
    data = _safe_json_load(DASHBOARD_SNAPSHOT_FILE, {})
    if not isinstance(data, dict):
        data = {}
    return {
        "exists": DASHBOARD_SNAPSHOT_FILE.exists() and bool(data),
        "path": str(DASHBOARD_SNAPSHOT_FILE),
        "timestamp": data.get("timestamp", ""),
        "run_status": data.get("run_status", "UNKNOWN"),
        "curated_stories": data.get("curated_stories", []) or [],
        "curated_categories": data.get("curated_categories", {}) or {},
        "plan": data.get("plan", {}) or {},
        "agent_outputs": data.get("agent_outputs", []) or [],
        "instagram_morning_pack": data.get("instagram_morning_pack", {}) or {},
        "instagram_afternoon_pack": data.get("instagram_afternoon_pack", {}) or {},
        "card_paths": data.get("card_paths", {}) or {},
        "brief_path": data.get("brief_path", ""),
        "override_summary": data.get("override_summary", {}) or {},
        "manual_overrides_applied": data.get("manual_overrides_applied", False),
        "run_summary": data.get("run_summary", {}) or {},
    }


def load_latest_run_summary() -> dict:
    data = _safe_json_load(RUN_SUMMARY_FILE, {})
    if not isinstance(data, dict):
        data = {}
    return {
        "exists": RUN_SUMMARY_FILE.exists() and bool(data),
        "path": str(RUN_SUMMARY_FILE),
        **data,
    }


def load_latest_brief() -> dict:
    run_summary = load_latest_run_summary()
    brief_path = run_summary.get("brief_file") or str(OUTPUT_FILE)
    if not brief_path:
        brief_path = str(OUTPUT_FILE)
    path = Path(brief_path)
    content = _safe_read_text(path)
    return {
        "path": str(path),
        "exists": path.exists(),
        "content": content,
        "folder": str(path.parent),
    }


def load_manual_overrides() -> dict:
    data = _safe_json_load(MANUAL_OVERRIDES_FILE, {})
    return data if isinstance(data, dict) else {}


def load_cards() -> dict:
    snapshot = load_dashboard_snapshot()
    snapshot_cards = []
    for key, value in (snapshot.get("card_paths", {}) or {}).items():
        path = Path(value)
        if path.exists():
            snapshot_cards.append({
                "key": key,
                "name": path.name,
                "path": str(path),
                "exists": True,
            })

    if snapshot_cards:
        return {
            "folder": str(CARDS_DIR),
            "exists": True,
            "cards": snapshot_cards,
            "source": "snapshot",
        }

    cards = []
    try:
        if CARDS_DIR.exists():
            for path in sorted(CARDS_DIR.glob("*.png")):
                cards.append({
                    "key": path.stem,
                    "name": path.name,
                    "path": str(path),
                    "exists": True,
                })
    except Exception:
        cards = []

    return {
        "folder": str(CARDS_DIR),
        "exists": bool(cards),
        "cards": cards,
        "source": "folder",
    }


def load_runtime_status() -> dict:
    asset_files = {
        "logo_watermark": ASSETS_DIR / "logo-watermark.png",
        "font_bold": ASSETS_DIR / "BarlowCondensed-Bold.ttf",
        "font_regular": ASSETS_DIR / "Barlow-Regular.ttf",
    }
    assets_status = {key: path.exists() for key, path in asset_files.items()}
    snapshot = load_dashboard_snapshot()
    brief = load_latest_brief()
    cards = load_cards()
    return {
        "minimax_configured": bool(os.environ.get("MINIMAX_API_KEY", "").strip()),
        "email_enabled": SEND_EMAIL_DIGEST,
        "email_ready": SEND_EMAIL_DIGEST and _bool_configured(
            EMAIL_SMTP_HOST,
            EMAIL_SMTP_USER,
            EMAIL_SMTP_PASSWORD,
            EMAIL_FROM,
            EMAIL_TO,
        ),
        "card_generation_enabled": GENERATE_IMAGES,
        "cards_exist": cards.get("exists", False),
        "snapshot_exists": snapshot.get("exists", False),
        "brief_exists": brief.get("exists", False),
        "overrides_exists": MANUAL_OVERRIDES_FILE.exists(),
        "assets_status": assets_status,
        "assets_ready": all(assets_status.values()),
        "paths": {
            "brief": brief.get("path", ""),
            "brief_folder": brief.get("folder", ""),
            "cards_folder": str(CARDS_DIR),
            "overrides": str(MANUAL_OVERRIDES_FILE),
            "run_summary": str(RUN_SUMMARY_FILE),
            "snapshot": str(DASHBOARD_SNAPSHOT_FILE),
        },
    }


def load_available_story_sets() -> dict:
    snapshot = load_dashboard_snapshot()
    plan = snapshot.get("plan", {}) or {}
    curated_stories = snapshot.get("curated_stories", []) or []
    return {
        "curated_stories": curated_stories,
        "plan": plan,
        "agent_outputs": snapshot.get("agent_outputs", []) or [],
        "morning_digest": plan.get("instagram_morning_digest", []) or [],
        "morning_alternatives": plan.get("instagram_morning_digest_alternatives", []) or [],
        "afternoon_digest": plan.get("instagram_afternoon_digest", []) or [],
        "afternoon_alternatives": plan.get("instagram_afternoon_digest_alternatives", []) or [],
    }


def find_agent_output_for_article(article: dict, agent_outputs=None) -> dict:
    article = article or {}
    agent_outputs = agent_outputs or load_dashboard_snapshot().get("agent_outputs", [])
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


def extract_brief_snippet(article_title: str, window: int = 260) -> str:
    brief = load_latest_brief()
    content = brief.get("content", "")
    if not article_title or not content:
        return ""
    idx = content.lower().find(article_title.lower())
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(content), idx + len(article_title) + window)
    snippet = content[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet += "..."
    return snippet


def load_dashboard_context() -> dict:
    snapshot = load_dashboard_snapshot()
    run_summary = load_latest_run_summary()
    brief = load_latest_brief()
    cards = load_cards()
    runtime = load_runtime_status()
    story_sets = load_available_story_sets()
    overrides = load_manual_overrides()

    useful_agent_outputs = [
        output for output in (snapshot.get("agent_outputs", []) or [])
        if _has_useful_output(output)
    ]
    useful_digest_outputs = [
        plan_output for plan_output in [
            (snapshot.get("plan", {}) or {}).get("instagram_morning_output", {}),
            (snapshot.get("plan", {}) or {}).get("instagram_afternoon_output", {}),
        ]
        if _has_useful_output(plan_output)
    ]

    return {
        "snapshot": snapshot,
        "run_summary": run_summary,
        "brief": brief,
        "cards": cards,
        "runtime": runtime,
        "story_sets": story_sets,
        "overrides": overrides,
        "agents_useful": bool(useful_agent_outputs or useful_digest_outputs),
    }


def build_selection_summary(context: dict, draft_overrides: dict | None = None) -> str:
    context = context or {}
    snapshot = context.get("snapshot", {}) or {}
    run_summary = context.get("run_summary", {}) or {}
    plan = (snapshot.get("plan", {}) or {})
    draft_overrides = draft_overrides or {}

    lines = [
        "SimulaNewsMachine — Selection Summary",
        "",
        f"Status: {run_summary.get('status', snapshot.get('run_status', 'UNKNOWN'))}",
        f"Ended at: {run_summary.get('ended_at', snapshot.get('timestamp', ''))}",
        f"Selected: {run_summary.get('articles_selected', len(snapshot.get('curated_stories', [])))}",
        "",
        "Instagram Morning Digest:",
    ]
    for i, article in enumerate(plan.get("instagram_morning_digest", [])[:7], 1):
        lines.append(f"{i}. {article.get('title', 'Sem título')} | {article.get('link', '')}")

    lines.append("")
    lines.append("Instagram Afternoon Digest:")
    for i, article in enumerate(plan.get("instagram_afternoon_digest", [])[:7], 1):
        lines.append(f"{i}. {article.get('title', 'Sem título')} | {article.get('link', '')}")

    if draft_overrides:
        lines.append("")
        lines.append("Draft overrides:")
        for key, value in sorted(draft_overrides.items()):
            lines.append(f"- {key}: {value}")

    brief_path = snapshot.get("brief_path") or run_summary.get("brief_file", "")
    if brief_path:
        lines.append("")
        lines.append(f"Brief: {brief_path}")

    for card in (context.get("cards", {}) or {}).get("cards", []):
        lines.append(f"Card: {card.get('path', '')}")

    return "\n".join(lines).strip()
