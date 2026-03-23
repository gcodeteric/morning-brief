"""
SimulaNewsMachine — Alertas operacionais.
Gera alerts.json com problemas relevantes do run actual.
Sem dependências externas. Não crítico.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

ALERT_FILE = Path(__file__).parent / "data" / "alerts.json"


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def check_and_alert(run_summary):
    """
    Gera alerts.json quando detecta problemas operacionais ou editoriais.
    Nunca levanta excepções para o caller.
    """
    alerts = []
    try:
        status = run_summary.get("status")
        feeds_total = max(_safe_int(run_summary.get("feeds_total"), 1), 1)
        feeds_fail = _safe_int(run_summary.get("feeds_fail"), 0)
        selected = _safe_int(run_summary.get("articles_selected"), 0)

        if status == "ERRO":
            alerts.append({
                "level": "CRITICAL",
                "type": "pipeline_error",
                "msg": f"Pipeline falhou: {run_summary.get('error', 'erro desconhecido')}"
            })

        fail_rate = feeds_fail / feeds_total
        if fail_rate > 0.30:
            alerts.append({
                "level": "WARNING",
                "type": "feed_fail_rate",
                "msg": f"{feeds_fail}/{feeds_total} feeds falharam ({fail_rate:.0%})"
            })

        if selected == 0:
            alerts.append({
                "level": "WARNING",
                "type": "zero_selected",
                "msg": "0 artigos selecionados"
            })

        # Alertas por categoria / guarantee coverage
        category_counts = run_summary.get("selected_by_category", {})
        if isinstance(category_counts, dict):
            for category in ("sim_racing", "motorsport", "hardware", "nostalgia", "racing_games"):
                if _safe_int(category_counts.get(category), 0) == 0:
                    alerts.append({
                        "level": "INFO" if category in ("hardware", "racing_games") else "WARNING",
                        "type": "category_empty",
                        "category": category,
                        "msg": f"Sem artigos selecionados para a categoria '{category}'"
                    })

        # Feeds falhados por categoria/origem crítica (se existirem no summary)
        failed_names = run_summary.get("feeds_failed_names", [])
        if isinstance(failed_names, list) and failed_names:
            critical_sources = ["fanatec", "moza", "flightsim.to", "flightsim", "msfs", "giants"]
            lowered = [str(x).lower() for x in failed_names]
            hits = [src for src in critical_sources if any(src in item for item in lowered)]
            if hits:
                alerts.append({
                    "level": "WARNING",
                    "type": "critical_sources_failed",
                    "msg": f"Feeds importantes falharam: {', '.join(sorted(set(hits)))}"
                })

        if alerts:
            ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ALERT_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "alerts": alerts,
                }, f, indent=2, ensure_ascii=False)
            logger.warning(f"Alerts: {len(alerts)} alerta(s) gerado(s) em {ALERT_FILE}")
        else:
            # Se não houver alertas, remover ficheiro antigo para não deixar stale state
            if ALERT_FILE.exists():
                ALERT_FILE.unlink()
            logger.info("Alerts: nenhum alerta gerado")

    except Exception as e:
        logger.warning(f"Alerts falharam (não crítico): {e}")
