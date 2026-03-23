"""
SimulaNewsMachine — Validador de Feeds.

Corre uma vez: python feed_validator.py
Testa TODOS os feeds e dá um relatório OK/FAIL.
"""

import sys
import feedparser

from feeds import get_all_feeds
from config import FEED_TIMEOUT_SECONDS


def validate_feed(feed_info):
    """Testa um feed individual. Retorna (status, num_entries, erro)."""
    url = feed_info["url"]
    name = feed_info["name"]

    try:
        parsed = feedparser.parse(url)

        # Verificar se houve erro de parsing
        if parsed.bozo and not parsed.entries:
            error_msg = str(getattr(parsed, "bozo_exception", "Erro desconhecido"))
            return "FAIL", 0, error_msg

        num_entries = len(parsed.entries)

        if num_entries == 0:
            return "WARN", 0, "0 artigos encontrados"

        return "OK", num_entries, None

    except Exception as e:
        return "FAIL", 0, str(e)


def main():
    print("=" * 70)
    print("SimulaNewsMachine — Feed Validator")
    print("=" * 70)
    print()

    feeds = get_all_feeds()
    print(f"A testar {len(feeds)} feeds...\n")

    results = {"OK": [], "WARN": [], "FAIL": []}

    for i, feed in enumerate(feeds, 1):
        name = feed["name"]
        url = feed["url"]
        cat = feed["cat"]

        status, count, error = validate_feed(feed)

        if status == "OK":
            print(f"  [{i:3d}] OK   {name:30s} ({cat:15s}) — {count} artigos")
            results["OK"].append(feed)
        elif status == "WARN":
            print(f"  [{i:3d}] WARN {name:30s} ({cat:15s}) — {error}")
            results["WARN"].append(feed)
        else:
            print(f"  [{i:3d}] FAIL {name:30s} ({cat:15s}) — {error}")
            results["FAIL"].append(feed)

    # Resumo final
    print()
    print("=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"  OK:   {len(results['OK']):3d} feeds a funcionar")
    print(f"  WARN: {len(results['WARN']):3d} feeds sem artigos (podem estar vazios temporariamente)")
    print(f"  FAIL: {len(results['FAIL']):3d} feeds com erro")
    print()

    if results["FAIL"]:
        print("Feeds que FALHARAM:")
        for feed in results["FAIL"]:
            print(f"  - {feed['name']}: {feed['url']}")
        print()

    if results["WARN"]:
        print("Feeds com WARNING (0 artigos):")
        for feed in results["WARN"]:
            print(f"  - {feed['name']}: {feed['url']}")
        print()

    total = len(feeds)
    ok = len(results["OK"])
    print(f"Taxa de sucesso: {ok}/{total} ({100*ok//total if total else 0}%)")

    return 0 if not results["FAIL"] else 1


if __name__ == "__main__":
    sys.exit(main())
