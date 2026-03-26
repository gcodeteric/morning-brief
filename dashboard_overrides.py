"""SimulaNewsMachine — safe override helpers for the internal dashboard."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from manual_overrides import OVERRIDES_FILE, resolve_channel_choice

logger = logging.getLogger(__name__)

OVERRIDES_EXAMPLE_FILE = Path(__file__).parent / "data" / "manual_overrides.example.json"
SUPPORTED_OVERRIDE_FIELDS = [
    "instagram_morning_digest",
    "instagram_afternoon_digest",
    "instagram_sim_racing",
    "instagram_motorsport",
    "x_thread_1",
    "x_thread_2",
    "youtube_daily",
    "discord_post",
]


def ensure_overrides_file() -> Path:
    if OVERRIDES_FILE.exists():
        return OVERRIDES_FILE
    try:
        OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
        if OVERRIDES_EXAMPLE_FILE.exists():
            example_data = json.loads(OVERRIDES_EXAMPLE_FILE.read_text(encoding="utf-8"))
            OVERRIDES_FILE.write_text(
                json.dumps(example_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        else:
            OVERRIDES_FILE.write_text("{}", encoding="utf-8")
    except Exception as e:
        logger.warning(f"Dashboard overrides: não foi possível criar o ficheiro: {e}")
    return OVERRIDES_FILE


def load_current_overrides() -> dict:
    try:
        if not OVERRIDES_FILE.exists():
            return {}
        with open(OVERRIDES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def sanitize_overrides(data: dict, allowed_fields=None) -> dict:
    data = data or {}
    allowed_fields = allowed_fields or SUPPORTED_OVERRIDE_FIELDS
    cleaned = {}
    for key, value in data.items():
        if key not in allowed_fields:
            continue
        try:
            value = int(value)
        except Exception:
            continue
        if value in (0, 1, 2):
            cleaned[key] = value
    return cleaned


def save_current_overrides(data: dict) -> tuple[bool, str]:
    try:
        cleaned = sanitize_overrides(data)
        ensure_overrides_file()
        with open(OVERRIDES_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)
        return True, str(OVERRIDES_FILE)
    except Exception as e:
        logger.warning(f"Dashboard overrides: falha ao guardar: {e}")
        return False, str(e)


def reset_current_overrides() -> tuple[bool, str]:
    try:
        ensure_overrides_file()
        with open(OVERRIDES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
        return True, str(OVERRIDES_FILE)
    except Exception as e:
        logger.warning(f"Dashboard overrides: falha ao limpar: {e}")
        return False, str(e)


def resolve_preview_selection(plan: dict, channel: str, override_value: int):
    plan = plan or {}
    primary = plan.get(channel)
    alternatives = plan.get(f"{channel}_alternatives", []) or []
    return resolve_channel_choice(primary, alternatives, override_value)


def get_override_options(plan: dict, channel: str) -> list[tuple[int, str]]:
    plan = plan or {}
    alternatives = plan.get(f"{channel}_alternatives", []) or []

    options = [(0, "Primary")]
    if len(alternatives) > 0:
        options.append((1, "Alternative 1"))
    else:
        options.append((1, "Alternative 1 (unavailable)"))
    if len(alternatives) > 1:
        options.append((2, "Alternative 2"))
    else:
        options.append((2, "Alternative 2 (unavailable)"))
    return options
