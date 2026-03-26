"""SimulaNewsMachine — centralized data access helpers for the internal dashboard."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
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

SNAPSHOT_SCHEMA_VERSION = 2
# Keep the existing filename for backward compatibility with the current
# dashboard, gitignore rules, and the latest successful run on disk.
LATEST_DASHBOARD_SNAPSHOT_FILE = DATA_DIR / "dashboard_latest_snapshot.json"
DASHBOARD_SNAPSHOT_FILE = LATEST_DASHBOARD_SNAPSHOT_FILE
MANUAL_OVERRIDES_FILE = DATA_DIR / "manual_overrides.json"
CARDS_DIR = DESKTOP / "SIMULA_CARDS_HOJE"
ASSETS_DIR = PROJECT_DIR / "assets"

STORY_DEFAULTS = {
    "title": "Sem título",
    "source": "Fonte desconhecida",
    "category": "unknown",
    "score": 0,
    "summary": "",
    "link": "",
    "priority": 0,
    "published": "",
    "no_date": False,
}

SINGLE_STORY_PLAN_FIELDS = (
    "instagram_sim_racing",
    "instagram_motorsport",
    "x_thread_1",
    "x_thread_2",
    "youtube_daily",
    "discord_post",
)

DIGEST_PLAN_FIELDS = (
    "instagram_morning_digest",
    "instagram_afternoon_digest",
)

DIGEST_OUTPUT_FIELDS = (
    "instagram_morning_output",
    "instagram_afternoon_output",
)

DIGEST_PACK_FIELDS = (
    "instagram_morning_pack",
    "instagram_afternoon_pack",
)


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


def _coerce_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _coerce_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _has_useful_output(output: dict) -> bool:
    output = output or {}
    return any([
        output.get("post"),
        output.get("instagram_pack"),
        output.get("image_prompt"),
        output.get("voice_script"),
    ])


def _parse_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _safe_mtime_iso(path_like) -> str:
    try:
        path = Path(path_like)
        if not path.exists():
            return ""
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def _hours_since(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    now = datetime.now(dt.tzinfo or timezone.utc)
    delta = now - dt
    return round(max(delta.total_seconds(), 0) / 3600, 2)


def _atomic_write_json(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(path.parent),
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            json.dump(payload, tmp, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def normalize_story(story: dict | None) -> dict:
    if not isinstance(story, dict):
        return dict(STORY_DEFAULTS)

    normalized = dict(story)
    normalized["title"] = str(normalized.get("title") or STORY_DEFAULTS["title"])
    normalized["source"] = str(normalized.get("source") or STORY_DEFAULTS["source"])
    normalized["category"] = str(normalized.get("category") or STORY_DEFAULTS["category"])
    normalized["summary"] = str(normalized.get("summary") or "")
    normalized["link"] = str(normalized.get("link") or "")
    normalized["priority"] = _coerce_int(normalized.get("priority"), 0)
    normalized["score"] = _coerce_int(normalized.get("score"), 0)
    normalized["published"] = str(normalized.get("published") or "")
    normalized["no_date"] = bool(normalized.get("no_date", False))
    return normalized


def normalize_digest(stories) -> list[dict]:
    if not isinstance(stories, list):
        return []
    return [normalize_story(story) for story in stories if isinstance(story, dict)]


def normalize_card_paths(card_paths) -> dict:
    if not isinstance(card_paths, dict):
        return {}
    normalized = {}
    for key, value in card_paths.items():
        if not value:
            continue
        normalized[str(key)] = str(value)
    return normalized


def _normalize_agent_metrics(metrics) -> dict:
    if not isinstance(metrics, dict):
        return {
            "scope": "",
            "timeout_seconds": 0.0,
            "calls_attempted": 0,
            "calls_succeeded": 0,
            "calls_failed": 0,
            "calls_timed_out": 0,
            "calls_skipped": 0,
            "durations": {},
            "parse_failures": [],
            "total_duration_sec": 0.0,
            "useful_output": False,
        }

    durations = metrics.get("durations", {})
    normalized_durations = {}
    if isinstance(durations, dict):
        for key, value in durations.items():
            normalized_durations[str(key)] = round(_coerce_float(value, 0.0), 3)

    parse_failures = []
    raw_failures = metrics.get("parse_failures", [])
    if isinstance(raw_failures, list):
        for item in raw_failures:
            if isinstance(item, dict):
                parse_failures.append({
                    "stage": str(item.get("stage", "")),
                    "error": str(item.get("error", "")),
                })
            elif item:
                parse_failures.append({"stage": str(item), "error": ""})

    return {
        "scope": str(metrics.get("scope", "") or ""),
        "timeout_seconds": round(_coerce_float(metrics.get("timeout_seconds"), 0.0), 3),
        "calls_attempted": _coerce_int(metrics.get("calls_attempted"), 0),
        "calls_succeeded": _coerce_int(metrics.get("calls_succeeded"), 0),
        "calls_failed": _coerce_int(metrics.get("calls_failed"), 0),
        "calls_timed_out": _coerce_int(metrics.get("calls_timed_out"), 0),
        "calls_skipped": _coerce_int(metrics.get("calls_skipped"), 0),
        "durations": normalized_durations,
        "parse_failures": parse_failures,
        "total_duration_sec": round(_coerce_float(metrics.get("total_duration_sec"), 0.0), 3),
        "useful_output": bool(metrics.get("useful_output", False)),
    }


def _aggregate_agent_metrics(outputs) -> dict:
    summary = {
        "pipelines": 0,
        "calls_attempted": 0,
        "calls_succeeded": 0,
        "calls_failed": 0,
        "calls_timed_out": 0,
        "calls_skipped": 0,
        "parse_failures": 0,
        "total_duration_sec": 0.0,
        "useful_outputs": 0,
    }
    for output in outputs or []:
        metrics = _normalize_agent_metrics((output or {}).get("agent_metrics", {}))
        if not any([
            metrics.get("calls_attempted"),
            metrics.get("calls_succeeded"),
            metrics.get("calls_failed"),
            metrics.get("calls_timed_out"),
            metrics.get("calls_skipped"),
            metrics.get("total_duration_sec"),
        ]):
            continue
        summary["pipelines"] += 1
        summary["calls_attempted"] += metrics.get("calls_attempted", 0)
        summary["calls_succeeded"] += metrics.get("calls_succeeded", 0)
        summary["calls_failed"] += metrics.get("calls_failed", 0)
        summary["calls_timed_out"] += metrics.get("calls_timed_out", 0)
        summary["calls_skipped"] += metrics.get("calls_skipped", 0)
        summary["parse_failures"] += len(metrics.get("parse_failures", []))
        summary["total_duration_sec"] += metrics.get("total_duration_sec", 0.0)
        if metrics.get("useful_output"):
            summary["useful_outputs"] += 1
    summary["total_duration_sec"] = round(summary["total_duration_sec"], 3)
    return summary


def _build_freshness_status(snapshot: dict, run_summary: dict, brief: dict) -> dict:
    snapshot_exists = bool(snapshot.get("exists", False))
    run_summary_exists = bool(run_summary.get("exists", False))
    brief_exists = bool(brief.get("exists", False))

    snapshot_dt = _parse_datetime(snapshot.get("timestamp", ""))
    run_dt = _parse_datetime(run_summary.get("ended_at", ""))
    brief_dt = _parse_datetime(brief.get("modified_at", ""))
    reference_dt = snapshot_dt or run_dt or brief_dt
    age_hours = _hours_since(reference_dt)

    if snapshot_exists:
        source = "structured_snapshot"
    elif run_summary_exists or brief_exists:
        source = "fallback_files"
    else:
        source = "missing"

    if source == "missing":
        label = "Missing"
        tone = "red"
        message = "No structured snapshot or fallback files are available for this dashboard state."
    elif source == "fallback_files":
        label = "Partial"
        tone = "warn"
        message = "Structured snapshot missing — dashboard is reconstructing what it can from fallback files."
    elif not (snapshot.get("plan") or snapshot.get("curated_stories")):
        label = "Partial"
        tone = "warn"
        message = "Structured snapshot exists but key planning/story data is missing."
    elif age_hours is None:
        label = "Partial"
        tone = "warn"
        message = "Structured snapshot exists but timestamp metadata is unavailable."
    elif age_hours <= 30:
        label = "Fresh"
        tone = "ok"
        message = "Structured snapshot matches the latest successful run closely enough for daily operations."
    else:
        label = "Stale"
        tone = "warn" if age_hours <= 72 else "red"
        message = "Latest structured data is older than a normal daily cycle. Confirm the latest run before acting."

    return {
        "label": label,
        "tone": tone,
        "source": source,
        "message": message,
        "age_hours": age_hours,
        "snapshot_timestamp": snapshot.get("timestamp", ""),
        "run_timestamp": run_summary.get("ended_at", ""),
        "brief_timestamp": brief.get("modified_at", ""),
    }


def _normalize_output(output) -> dict:
    if not isinstance(output, dict):
        return {}

    normalized = dict(output)
    article = normalized.get("article")
    normalized["article"] = normalize_story(article) if isinstance(article, dict) else {}
    normalized["analysis"] = normalized.get("analysis", "") or ""
    normalized["post"] = normalized.get("post", "") or ""
    normalized["raw_post"] = normalized.get("raw_post", "") or ""
    normalized["image_prompt"] = normalized.get("image_prompt", "") or ""
    normalized["voice_script"] = normalized.get("voice_script", "") or ""
    normalized["qa"] = normalized.get("qa", "") or ""
    normalized["agent_metrics"] = _normalize_agent_metrics(normalized.get("agent_metrics", {}))
    normalized["instagram_pack"] = (
        normalized.get("instagram_pack", {})
        if isinstance(normalized.get("instagram_pack"), dict)
        else {}
    )
    return normalized


def _normalize_digest_alternatives(value) -> list[list[dict]]:
    if not isinstance(value, list):
        return []
    return [normalize_digest(variant) for variant in value if isinstance(variant, list)]


def _normalize_plan(plan) -> dict:
    if not isinstance(plan, dict):
        return {}

    normalized = dict(plan)

    for key in SINGLE_STORY_PLAN_FIELDS:
        value = normalized.get(key)
        normalized[key] = normalize_story(value) if isinstance(value, dict) and value else {}

    normalized["reddit_candidates"] = normalize_digest(normalized.get("reddit_candidates", []))

    for key in DIGEST_PLAN_FIELDS:
        normalized[key] = normalize_digest(normalized.get(key, []))
        normalized[f"{key}_alternatives"] = _normalize_digest_alternatives(
            normalized.get(f"{key}_alternatives", [])
        )

    for key in DIGEST_OUTPUT_FIELDS:
        normalized[key] = _normalize_output(normalized.get(key, {}))

    for key in DIGEST_PACK_FIELDS:
        normalized[key] = normalized.get(key, {}) if isinstance(normalized.get(key), dict) else {}

    return normalized


def is_valid_snapshot(data) -> bool:
    if not isinstance(data, dict):
        return False
    return any([
        isinstance(data.get("plan"), dict),
        isinstance(data.get("run_summary"), dict),
        isinstance(data.get("curated_stories"), list),
        bool(data.get("brief_path")),
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
        normalized_plan = _normalize_plan(plan or {})
        normalized_cards = normalize_card_paths(card_paths or {})
        normalized_agent_outputs = [
            _normalize_output(output)
            for output in (curated.get("agent_outputs", []) or [])
            if isinstance(output, dict)
        ]
        normalized_curated = normalize_digest(curated.get("selected", []))
        run_summary = run_summary or {}

        snapshot = {
            "snapshot_kind": "latest_dashboard_snapshot",
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "timestamp": datetime.now().isoformat(),
            "run_status": run_summary.get("status", "OK"),
            "curated_stories": normalized_curated,
            "curated_categories": curated.get("categories", {}) or {},
            "total_before_dedup": _coerce_int(curated.get("total_before_dedup"), 0),
            "total_after_dedup": _coerce_int(curated.get("total_after_dedup"), 0),
            "plan": normalized_plan,
            "agent_outputs": normalized_agent_outputs,
            "instagram_morning_pack": normalized_plan.get("instagram_morning_pack", {}) or {},
            "instagram_afternoon_pack": normalized_plan.get("instagram_afternoon_pack", {}) or {},
            "card_paths": normalized_cards,
            "brief_path": _existing_path(brief_path) or str(brief_path or ""),
            "override_summary": normalized_plan.get("override_summary", {}) or {},
            "manual_overrides_applied": normalized_plan.get("manual_overrides_applied", False),
            "run_summary": run_summary,
        }

        _atomic_write_json(DASHBOARD_SNAPSHOT_FILE, _json_safe(snapshot))
        return str(DASHBOARD_SNAPSHOT_FILE)
    except Exception as e:
        logger.warning(f"Dashboard snapshot falhou (não crítico): {e}")
        return ""


def load_latest_snapshot() -> dict:
    raw = _safe_json_load(DASHBOARD_SNAPSHOT_FILE, {})
    data = raw if is_valid_snapshot(raw) else {}
    plan = _normalize_plan(data.get("plan", {}))
    agent_outputs = [
        _normalize_output(output)
        for output in (data.get("agent_outputs", []) or [])
        if isinstance(output, dict)
    ]

    return {
        "exists": DASHBOARD_SNAPSHOT_FILE.exists() and bool(data),
        "path": str(DASHBOARD_SNAPSHOT_FILE),
        "schema_version": _coerce_int(data.get("schema_version"), 1) if data else 0,
        "snapshot_kind": (
            data.get("snapshot_kind", "")
            or ("latest_dashboard_snapshot" if data else "")
        ),
        "timestamp": data.get("timestamp", "") if data else "",
        "run_status": data.get("run_status", "UNKNOWN") if data else "UNKNOWN",
        "curated_stories": normalize_digest(data.get("curated_stories", [])) if data else [],
        "curated_categories": data.get("curated_categories", {}) if isinstance(data.get("curated_categories", {}), dict) else {},
        "total_before_dedup": _coerce_int(data.get("total_before_dedup"), 0) if data else 0,
        "total_after_dedup": _coerce_int(data.get("total_after_dedup"), 0) if data else 0,
        "plan": plan,
        "agent_outputs": agent_outputs,
        "instagram_morning_pack": (
            data.get("instagram_morning_pack", {}) if isinstance(data.get("instagram_morning_pack"), dict)
            else plan.get("instagram_morning_pack", {})
        ) or {},
        "instagram_afternoon_pack": (
            data.get("instagram_afternoon_pack", {}) if isinstance(data.get("instagram_afternoon_pack"), dict)
            else plan.get("instagram_afternoon_pack", {})
        ) or {},
        "card_paths": normalize_card_paths(data.get("card_paths", {})) if data else {},
        "brief_path": str(data.get("brief_path", "")) if data else "",
        "override_summary": data.get("override_summary", {}) if isinstance(data.get("override_summary", {}), dict) else {},
        "manual_overrides_applied": bool(data.get("manual_overrides_applied", False)) if data else False,
        "run_summary": data.get("run_summary", {}) if isinstance(data.get("run_summary", {}), dict) else {},
    }


def load_dashboard_snapshot() -> dict:
    """Backward-compatible alias used by the existing dashboard UI."""
    return load_latest_snapshot()


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
    path = Path(brief_path or OUTPUT_FILE)
    content = _safe_read_text(path)
    return {
        "path": str(path),
        "exists": path.exists(),
        "content": content,
        "folder": str(path.parent),
        "modified_at": _safe_mtime_iso(path),
    }


def load_latest_brief_path() -> str:
    return load_latest_brief().get("path", "")


def load_latest_brief_text() -> str:
    return load_latest_brief().get("content", "")


def load_manual_overrides() -> dict:
    data = _safe_json_load(MANUAL_OVERRIDES_FILE, {})
    return data if isinstance(data, dict) else {}


def load_cards(snapshot: dict | None = None) -> dict:
    snapshot = snapshot or load_latest_snapshot()
    snapshot_card_paths = normalize_card_paths(snapshot.get("card_paths", {}))
    snapshot_cards = []

    for key, value in snapshot_card_paths.items():
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


def load_runtime_status(
    snapshot: dict | None = None,
    brief: dict | None = None,
    cards: dict | None = None,
) -> dict:
    asset_files = {
        "logo_watermark": ASSETS_DIR / "logo-watermark.png",
        "font_bold": ASSETS_DIR / "BarlowCondensed-Bold.ttf",
        "font_regular": ASSETS_DIR / "Barlow-Regular.ttf",
    }
    assets_status = {key: path.exists() for key, path in asset_files.items()}
    snapshot = snapshot or load_latest_snapshot()
    brief = brief or load_latest_brief()
    cards = cards or load_cards(snapshot=snapshot)
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


def find_agent_output_for_article(article: dict, agent_outputs=None) -> dict:
    raw_article = article if isinstance(article, dict) else {}
    article_link = str(raw_article.get("link") or "")
    article_title = str(raw_article.get("title") or "")
    if not article_link and not article_title:
        return {}

    article = normalize_story(raw_article)
    if agent_outputs is None:
        agent_outputs = load_latest_snapshot().get("agent_outputs", [])

    for output in agent_outputs:
        output_article = normalize_story((output or {}).get("article", {}))
        if article_link and output_article.get("link") == article_link:
            return _normalize_output(output)
    for output in agent_outputs:
        output_article = normalize_story((output or {}).get("article", {}))
        if article_title and output_article.get("title") == article_title:
            return _normalize_output(output)
    return {}


def load_instagram_digest_data(snapshot: dict | None = None, overrides: dict | None = None) -> dict:
    snapshot = snapshot or load_latest_snapshot()
    plan = snapshot.get("plan", {}) or {}
    overrides = overrides or load_manual_overrides()
    card_paths = normalize_card_paths(snapshot.get("card_paths", {}))

    active_morning = _coerce_int(overrides.get("instagram_morning_digest"), 0)
    active_afternoon = _coerce_int(overrides.get("instagram_afternoon_digest"), 0)
    if active_morning not in (0, 1, 2):
        active_morning = 0
    if active_afternoon not in (0, 1, 2):
        active_afternoon = 0

    return {
        "morning_digest": normalize_digest(plan.get("instagram_morning_digest", [])),
        "morning_alternatives": _normalize_digest_alternatives(
            plan.get("instagram_morning_digest_alternatives", [])
        ),
        "morning_pack": plan.get("instagram_morning_pack", {}) or snapshot.get("instagram_morning_pack", {}) or {},
        "morning_output": _normalize_output(plan.get("instagram_morning_output", {})),
        "afternoon_digest": normalize_digest(plan.get("instagram_afternoon_digest", [])),
        "afternoon_alternatives": _normalize_digest_alternatives(
            plan.get("instagram_afternoon_digest_alternatives", [])
        ),
        "afternoon_pack": plan.get("instagram_afternoon_pack", {}) or snapshot.get("instagram_afternoon_pack", {}) or {},
        "afternoon_output": _normalize_output(plan.get("instagram_afternoon_output", {})),
        "active_variants": {
            "instagram_morning_digest": active_morning,
            "instagram_afternoon_digest": active_afternoon,
        },
        "card_paths": {
            "morning_digest": card_paths.get("morning_digest", ""),
            "afternoon_digest": card_paths.get("afternoon_digest", ""),
        },
        "legacy_instagram": {
            "instagram_sim_racing": plan.get("instagram_sim_racing", {}) or {},
            "instagram_motorsport": plan.get("instagram_motorsport", {}) or {},
        },
    }


def load_other_channel_data(snapshot: dict | None = None) -> dict:
    snapshot = snapshot or load_latest_snapshot()
    plan = snapshot.get("plan", {}) or {}
    agent_outputs = snapshot.get("agent_outputs", []) or []
    return {
        "x_thread_1": {
            "article": plan.get("x_thread_1", {}) or {},
            "output": find_agent_output_for_article(plan.get("x_thread_1", {}), agent_outputs),
        },
        "x_thread_2": {
            "article": plan.get("x_thread_2", {}) or {},
            "output": find_agent_output_for_article(plan.get("x_thread_2", {}), agent_outputs),
        },
        "youtube_daily": {
            "article": plan.get("youtube_daily", {}) or {},
            "output": find_agent_output_for_article(plan.get("youtube_daily", {}), agent_outputs),
        },
        "reddit_candidates": normalize_digest(plan.get("reddit_candidates", [])),
        "discord_post": {
            "article": plan.get("discord_post", {}) or {},
            "output": find_agent_output_for_article(plan.get("discord_post", {}), agent_outputs),
        },
    }


def load_available_story_sets(snapshot: dict | None = None) -> dict:
    snapshot = snapshot or load_latest_snapshot()
    instagram = load_instagram_digest_data(snapshot=snapshot)
    plan = snapshot.get("plan", {}) or {}
    return {
        "curated_stories": normalize_digest(snapshot.get("curated_stories", [])),
        "plan": plan,
        "agent_outputs": snapshot.get("agent_outputs", []) or [],
        "morning_digest": instagram.get("morning_digest", []),
        "morning_alternatives": instagram.get("morning_alternatives", []),
        "afternoon_digest": instagram.get("afternoon_digest", []),
        "afternoon_alternatives": instagram.get("afternoon_alternatives", []),
    }


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


def build_dashboard_context() -> dict:
    snapshot = load_latest_snapshot()
    run_summary = load_latest_run_summary()
    brief = load_latest_brief()
    overrides = load_manual_overrides()
    cards = load_cards(snapshot=snapshot)
    runtime = load_runtime_status(snapshot=snapshot, brief=brief, cards=cards)
    instagram = load_instagram_digest_data(snapshot=snapshot, overrides=overrides)
    channels = load_other_channel_data(snapshot=snapshot)
    story_sets = load_available_story_sets(snapshot=snapshot)
    freshness = _build_freshness_status(snapshot, run_summary, brief)

    useful_agent_outputs = [
        output for output in (snapshot.get("agent_outputs", []) or [])
        if _has_useful_output(output)
    ]
    useful_digest_outputs = [
        output for output in [
            instagram.get("morning_output", {}),
            instagram.get("afternoon_output", {}),
        ]
        if _has_useful_output(output)
    ]
    agent_runtime = _aggregate_agent_metrics([
        *(snapshot.get("agent_outputs", []) or []),
        instagram.get("morning_output", {}),
        instagram.get("afternoon_output", {}),
    ])

    return {
        "status": {
            "run_status": run_summary.get("status", snapshot.get("run_status", "UNKNOWN")),
            "timestamp": run_summary.get("ended_at", snapshot.get("timestamp", "")),
            "articles_scanned": run_summary.get("articles_scanned", 0),
            "articles_selected": run_summary.get("articles_selected", len(snapshot.get("curated_stories", []))),
            "snapshot_exists": snapshot.get("exists", False),
            "freshness": freshness.get("label", "Missing"),
            "data_source": freshness.get("source", "missing"),
        },
        "brief": brief,
        "overrides": overrides,
        "instagram": instagram,
        "channels": channels,
        "cards": cards,
        "paths": runtime.get("paths", {}),
        "freshness": freshness,
        "agent_runtime": agent_runtime,
        "selected_stories": normalize_digest(snapshot.get("curated_stories", [])),
        # Backward-compatible keys used by the current Streamlit app.
        "snapshot": snapshot,
        "run_summary": run_summary,
        "runtime": runtime,
        "story_sets": story_sets,
        "agents_useful": bool(useful_agent_outputs or useful_digest_outputs),
    }


def load_dashboard_context() -> dict:
    """Backward-compatible alias used by the existing dashboard UI."""
    return build_dashboard_context()


def build_selection_summary(context: dict, draft_overrides: dict | None = None) -> str:
    context = context or {}
    snapshot = context.get("snapshot", {}) or {}
    run_summary = context.get("run_summary", {}) or {}
    plan = (snapshot.get("plan", {}) or {})
    active_overrides = dict((context.get("overrides", {}) or {}))
    if draft_overrides:
        active_overrides.update(draft_overrides)

    def _resolve_digest(channel: str):
        override_value = _coerce_int(active_overrides.get(channel), 0)
        alternatives = plan.get(f"{channel}_alternatives", []) or []
        if override_value == 1:
            if len(alternatives) > 0:
                return normalize_digest(alternatives[0]), 1
            return normalize_digest(plan.get(channel, [])), 0
        if override_value == 2:
            if len(alternatives) > 1:
                return normalize_digest(alternatives[1]), 2
            return normalize_digest(plan.get(channel, [])), 0
        return normalize_digest(plan.get(channel, [])), 0

    morning_digest, morning_variant = _resolve_digest("instagram_morning_digest")
    afternoon_digest, afternoon_variant = _resolve_digest("instagram_afternoon_digest")

    lines = [
        "SimulaNewsMachine — Selection Summary",
        "",
        f"Status: {run_summary.get('status', snapshot.get('run_status', 'UNKNOWN'))}",
        f"Ended at: {run_summary.get('ended_at', snapshot.get('timestamp', ''))}",
        f"Selected: {run_summary.get('articles_selected', len(snapshot.get('curated_stories', [])))}",
        "",
        f"Instagram Morning Digest (variant {morning_variant}):",
    ]
    for i, article in enumerate(morning_digest[:7], 1):
        story = normalize_story(article)
        lines.append(f"{i}. {story.get('title')} | {story.get('link')}")

    lines.append("")
    lines.append(f"Instagram Afternoon Digest (variant {afternoon_variant}):")
    for i, article in enumerate(afternoon_digest[:7], 1):
        story = normalize_story(article)
        lines.append(f"{i}. {story.get('title')} | {story.get('link')}")

    if active_overrides:
        lines.append("")
        lines.append("Resolved overrides:")
        for key, value in sorted(active_overrides.items()):
            lines.append(f"- {key}: {value}")

    brief_path = snapshot.get("brief_path") or run_summary.get("brief_file", "")
    if brief_path:
        lines.append("")
        lines.append(f"Brief: {brief_path}")

    for card in (context.get("cards", {}) or {}).get("cards", []):
        lines.append(f"Card: {card.get('path', '')}")

    return "\n".join(lines).strip()
