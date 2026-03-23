"""SimulaNewsMachine v2.2 — Corre diariamente às 05:00"""

import logging
import os
import shutil
import json
import sys
from datetime import datetime

from config import (
    LOG_DIR, ARCHIVE_DIR, OUTPUT_FILE, RUN_SUMMARY_FILE, DATA_DIR,
    GENERATE_IMAGES,
)
from planner import plan as run_planner

# FIX B.1 — Instance locking
LOCK_FILE = DATA_DIR / "instance.lock"


def acquire_lock():
    """Tenta adquirir lock. Retorna True se conseguiu."""
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        # Verificar se o PID ainda está vivo
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)  # Testar se o processo existe
            return False
        except (ProcessLookupError, ValueError, OSError):
            LOCK_FILE.unlink(missing_ok=True)
            return acquire_lock()


def release_lock():
    """Liberta o lock."""
    LOCK_FILE.unlink(missing_ok=True)


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
    if not acquire_lock():
        print("Outra instancia ja esta a correr. A sair.")
        sys.exit(0)

    try:
        started_at = datetime.now().isoformat()
        setup_logging()
        logging.info("=== SimulaNewsMachine v2.2 iniciada ===")

        from scanner import scan_all_feeds
        from curator import curate_articles
        from formatter import format_brief

        # Scan
        logging.info("Passo 1: Scanning feeds...")
        raw, scan_stats = scan_all_feeds()
        logging.info(f"   -> {len(raw)} artigos encontrados")

        # Curate
        logging.info("Passo 2: Curating...")
        curated = curate_articles(raw)
        logging.info(f"   -> {len(curated['selected'])} selecionados")

        # Plan (não crítico — formatter tem fallback interno)
        logging.info("Passo 3: Planning...")
        editorial_plan = None
        try:
            editorial_plan = run_planner(curated)
        except Exception as e:
            logging.warning(f"Planner falhou (não crítico): {e}")

        # Cards (import lazy — depende de Pillow/assets opcionais)
        card_paths = {}
        if GENERATE_IMAGES:
            try:
                from card_generator import generate_instagram_cards
                card_paths = generate_instagram_cards(editorial_plan or {})
                logging.info(f"   -> {len(card_paths)} cards gerados")
            except Exception as e:
                logging.warning(f"Card generator falhou (não crítico): {e}")

        # Format
        logging.info("Passo 4: Formatting...")
        format_brief(curated, OUTPUT_FILE, plan=editorial_plan, card_paths=card_paths)
        logging.info(f"   -> Brief guardado em {OUTPUT_FILE}")

        # Archive
        archive_file = ARCHIVE_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_brief.md"
        shutil.copy2(OUTPUT_FILE, archive_file)
        logging.info(f"   -> Arquivo guardado em {archive_file}")

        # FIX 1.4 — run_summary.json com métricas completas
        summary = {
            "started_at": started_at,
            "ended_at": datetime.now().isoformat(),
            "feeds_total": scan_stats.get("total", 0),
            "feeds_ok": scan_stats.get("ok", 0),
            "feeds_empty": scan_stats.get("empty", 0),
            "feeds_fail": scan_stats.get("fail", 0),
            "feeds_failed_names": scan_stats.get("failed_names", []),
            "articles_scanned": len(raw),
            "articles_after_dedup": curated.get("total_after_dedup", 0),
            "articles_selected": len(curated["selected"]),
            "top_sources": list(dict.fromkeys(
                a["source"] for a in curated["selected"][:8]
            ))[:5],
            "categories": curated.get("categories", {}),
            "selected_by_category": curated.get("categories", {}),
            "brief_file": str(OUTPUT_FILE),
            "status": "OK",
        }
        with open(RUN_SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logging.info("   -> run_summary.json actualizado")

        # Alertas operacionais (não crítico)
        try:
            from alerts import check_and_alert
            check_and_alert(summary)
        except Exception as e:
            logging.warning(f"Alerts falharam (não crítico): {e}")

        logging.info("=== Concluido com sucesso ===")

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

    finally:
        release_lock()


if __name__ == "__main__":
    main()
