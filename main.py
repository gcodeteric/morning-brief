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


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="SimulaNewsMachine — daily sim racing brief generator"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Corre o pipeline sem escrever ficheiros de output ou estado"
    )
    return parser.parse_args()


def _print_run_summary(curated, plan, card_paths, dry_run):
    try:
        def _safe_print(text=""):
            try:
                print(text)
            except UnicodeEncodeError:
                encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
                fallback_text = text.replace("✓", "OK").replace("–", "-")
                safe_text = fallback_text.encode(encoding, errors="replace").decode(encoding, errors="replace")
                print(safe_text)

        curated = curated or {}
        plan = plan or {}
        card_paths = card_paths or []
        selected = curated.get("selected", [])
        top3 = selected[:3]

        _safe_print("\n" + "=" * 52)
        if dry_run:
            _safe_print("  DRY RUN — nenhum ficheiro escrito")
            _safe_print("=" * 52)

        if top3:
            _safe_print("  TOP 3 ARTIGOS:")
            for i, a in enumerate(top3, 1):
                title = a.get("title", "sem título")[:45]
                score = a.get("score", 0)
                _safe_print(f"  {i}. [{score:>3}] {title}")
        else:
            _safe_print("  Sem artigos seleccionados")

        _safe_print("=" * 52)

        ig_sim = "✓" if plan.get("instagram_sim_racing") else "–"
        ig_moto = "✓" if plan.get("instagram_motorsport") else "–"
        yt_daily = "✓" if plan.get("youtube_daily") else "–"
        reddit = len(plan.get("reddit_candidates", []))
        discord = "✓" if plan.get("discord_post") else "SILÊNCIO"
        cards = len(card_paths) if card_paths else 0

        _safe_print(f"  IG sim={ig_sim}  IG moto={ig_moto}  "
                    f"YT={yt_daily}  Reddit={reddit}  "
                    f"Discord={discord}  Cards={cards}")
        _safe_print("=" * 52 + "\n")
    except Exception:
        pass  # preview nunca pode quebrar o run


def main(dry_run: bool = False):
    if not acquire_lock():
        print("Outra instancia ja esta a correr. A sair.")
        sys.exit(0)

    try:
        started_at = datetime.now().isoformat()
        setup_logging()
        logging.info("=== SimulaNewsMachine v2.2 iniciada ===")
        if dry_run:
            logging.info("DRY RUN — pipeline completo, nenhum ficheiro será escrito")

        from scanner import scan_all_feeds
        from curator import curate_articles
        from formatter import format_brief
        import curator
        import planner

        # Propagar dry_run para módulos que escrevem ficheiros de estado
        if dry_run:
            curator._DRY_RUN = True
            planner._DRY_RUN = True

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
        if GENERATE_IMAGES and not dry_run:
            try:
                from card_generator import generate_instagram_cards
                card_paths = generate_instagram_cards(editorial_plan or {})
                logging.info(f"   -> {len(card_paths)} cards gerados")
            except Exception as e:
                logging.warning(f"Card generator falhou (não crítico): {e}")

        if not dry_run:
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
        else:
            logging.info(
                "DRY RUN concluído — %d artigos seleccionados, brief NÃO guardado",
                len(curated.get("selected", []))
            )

        _print_run_summary(curated, editorial_plan, card_paths, dry_run)
        logging.info("=== Concluido com sucesso ===")

    except Exception as e:
        logging.error(f"ERRO FATAL: {e}", exc_info=True)

        # Guardar summary mesmo em caso de erro (excepto em dry-run)
        if not dry_run:
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
    args = parse_args()
    main(dry_run=args.dry_run)
