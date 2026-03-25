"""SimulaNewsMachine — Manual overrides opcionais por canal."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

OVERRIDES_FILE = Path(__file__).parent / "data" / "manual_overrides.json"


def load_manual_overrides() -> dict:
    if not OVERRIDES_FILE.exists():
        logger.info("Manual overrides: ficheiro não existe, a usar escolhas principais")
        return {}
    try:
        with open(OVERRIDES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("Manual overrides inválido: JSON não é um objecto")
            return {}
        logger.info(f"Manual overrides: {len(data)} entradas carregadas")
        return data
    except Exception as e:
        logger.warning(f"Manual overrides inválido ou ilegível: {e}")
        return {}


def resolve_channel_choice(primary, alternatives, override_value):
    alternatives = alternatives or []
    if override_value in (None, 0):
        return primary
    if override_value == 1:
        return alternatives[0] if len(alternatives) > 0 else primary
    if override_value == 2:
        return alternatives[1] if len(alternatives) > 1 else primary
    return primary


def apply_manual_overrides(plan, overrides) -> dict:
    updated = dict(plan or {})
    applied = {}
    channel_keys = [
        "instagram_sim_racing",
        "instagram_motorsport",
        "x_thread_1",
        "x_thread_2",
        "youtube_daily",
        "discord_post",
    ]

    for channel in channel_keys:
        primary = updated.get(channel)
        alternatives = updated.get(f"{channel}_alternatives", [])
        override_value = overrides.get(channel)
        resolved = resolve_channel_choice(primary, alternatives, override_value)
        updated[channel] = resolved
        if override_value in (1, 2) and resolved is not primary:
            applied[channel] = override_value

    updated["manual_overrides_applied"] = bool(applied)
    if applied:
        updated["override_summary"] = applied
    return updated
