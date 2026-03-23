"""SimulaNewsMachine v2.1 — Corre diariamente às 05:00"""

import logging
import shutil
import json
import sys
from datetime import datetime

from config import (
    LOG_DIR, ARCHIVE_DIR, OUTPUT_FILE, RUN_SUMMARY_FILE,
)


def setup_logging():
    """Configura logging para ficheiro + consola."""
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler())


def main():
    started_at = datetime.now().isoformat()
    setup_logging()
    logging.info("=== SimulaNewsMachine v2.1 iniciada ===")

    try:
        from scanner import scan_all_feeds
        from curator import curate_articles
        from formatter import format_brief

        # Scan
        logging.info("Passo 1: Scanning feeds...")
        raw, scan_stats = scan_all_feeds()
        logging.info(f"   → {len(raw)} artigos encontrados")

        # Curate
        logging.info("Passo 2: Curating...")
        curated = curate_articles(raw)
        logging.info(f"   → {len(curated['selected'])} selecionados")

        # Format
        logging.info("Passo 3: Formatting...")
        format_brief(curated, OUTPUT_FILE)
        logging.info(f"   → Brief guardado em {OUTPUT_FILE}")

        # Archive
        archive_file = ARCHIVE_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_brief.md"
        shutil.copy2(OUTPUT_FILE, archive_file)
        logging.info(f"   → Arquivo guardado em {archive_file}")

        # Generate run_summary.json
        summary = {
            "started_at": started_at,
            "ended_at": datetime.now().isoformat(),
            "feeds_total": scan_stats.get("total", 0),
            "feeds_ok": scan_stats.get("ok", 0),
            "feeds_fail": scan_stats.get("fail", 0),
            "feeds_failed_names": scan_stats.get("failed_names", []),
            "articles_scanned": len(raw),
            "articles_selected": len(curated["selected"]),
            "top_sources": [a["source"] for a in curated["selected"][:5]],
            "brief_file": str(OUTPUT_FILE),
            "status": "OK",
        }
        with open(RUN_SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logging.info("   → run_summary.json actualizado")
        logging.info("=== Concluído com sucesso ===")

    except Exception as e:
        logging.error(f"ERRO FATAL: {e}", exc_info=True)

        # Guardar summary mesmo em caso de erro
        try:
            error_summary = {
                "started_at": started_at,
                "ended_at": datetime.now().isoformat(),
                "status": "ERRO",
                "error": str(e),
            }
            with open(RUN_SUMMARY_FILE, "w", encoding="utf-8") as f:
                json.dump(error_summary, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
