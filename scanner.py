"""
SimulaNewsMachine — Scanner de feeds RSS.

Lê todos os feeds, filtra por janela temporal, e retorna artigos crus.
"""

import html
import json
import logging
import re
from datetime import datetime, timezone, timedelta

import feedparser
import requests
from dateutil import parser as dateutil_parser

from config import HOURS_LOOKBACK, FEED_TIMEOUT_SECONDS
from feeds import get_all_feeds

import socket
# Safety net for feedparser fallback, which may open sockets internally without explicit timeout.
# Acceptable here because this is a standalone scheduled script, not a library.
socket.setdefaulttimeout(FEED_TIMEOUT_SECONDS)

logger = logging.getLogger(__name__)


def _parse_date(entry):
    """Tenta extrair data de publicação de um entry. Retorna datetime ou None."""
    for field in ("published", "updated", "created"):
        raw = entry.get(field) or entry.get(f"{field}_parsed")
        if raw:
            try:
                if isinstance(raw, str):
                    dt = dateutil_parser.parse(raw)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                elif hasattr(raw, "tm_year"):
                    # time.struct_time
                    from calendar import timegm
                    return datetime.fromtimestamp(timegm(raw), tz=timezone.utc)
            except Exception:
                continue
    return None


def _scan_single_feed(feed_info):
    """Scan um feed individual. Retorna dict com status e artigos."""
    url = feed_info["url"]
    name = feed_info["name"]
    category = feed_info["cat"]
    priority = feed_info["p"]
    articles = []

    try:
        # FIX 1.2 — Usar requests com timeout real + raise_for_status
        parsed = None
        try:
            resp = requests.get(url, timeout=FEED_TIMEOUT_SECONDS, headers={
                "User-Agent": "SimulaNewsMachine/2.2"
            })
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except requests.exceptions.RequestException:
            parsed = None  # Forçar fallback

        # Se requests falhou OU deu bozo sem entries, tentar feedparser directo
        if parsed is None or (parsed.bozo and not parsed.entries):
            try:
                parsed = feedparser.parse(url)
            except Exception as fallback_err:
                return {"status": "FAIL", "articles": [], "error": str(fallback_err)}

        # FIX 1.3 — Verificar bozo flag (após ambas as tentativas)
        if parsed.bozo and not parsed.entries:
            return {
                "status": "FAIL",
                "articles": [],
                "error": f"Feed malformado: {getattr(parsed, 'bozo_exception', 'desconhecido')}",
            }

        if not parsed.entries:
            return {"status": "EMPTY", "articles": [], "error": None}

        now = datetime.now(timezone.utc)
        lookback_cutoff = now - timedelta(hours=HOURS_LOOKBACK)

        for entry in parsed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                continue

            # Extrair summary
            summary = ""
            if entry.get("summary"):
                summary = entry["summary"]
            elif entry.get("description"):
                summary = entry["description"]
            # Limpar HTML tags, unescape entities, e truncar
            summary = re.sub(r"<[^>]+>", " ", summary)
            summary = html.unescape(summary)
            summary = re.sub(r"\s+", " ", summary).strip()
            summary = summary[:300]

            # Parse da data
            pub_date = _parse_date(entry)
            no_date = pub_date is None

            if pub_date:
                # Ignorar datas futuras
                if pub_date > now + timedelta(hours=2):
                    continue
                # Verificar se está na janela de lookback
                if pub_date < lookback_cutoff:
                    continue

            articles.append({
                "title": title,
                "link": link,
                "summary": summary,
                "published": pub_date.isoformat() if pub_date else None,
                "source": name,
                "category": category,
                "priority": priority,
                "no_date": no_date,
            })

        # FIX 1.1 — Distinguir OK de EMPTY
        if articles:
            return {"status": "OK", "articles": articles, "error": None}
        else:
            return {"status": "EMPTY", "articles": [], "error": None}

    except Exception as e:
        logger.warning(f"Erro ao ler feed '{name}' ({url}): {e}")
        return {"status": "FAIL", "articles": [], "error": str(e)}


def scan_all_feeds():
    """
    Scan todos os feeds e retorna (artigos, stats).
    Nunca levanta excepção — feeds que falham são ignorados.
    """
    feeds = get_all_feeds()
    all_articles = []
    stats = {
        "total": len(feeds),
        "ok": 0,
        "empty": 0,
        "fail": 0,
        "failed_names": [],
    }

    # FIX 1.1 — Contar status real de cada feed
    for feed in feeds:
        result = _scan_single_feed(feed)

        if result["status"] == "OK":
            all_articles.extend(result["articles"])
            stats["ok"] += 1
        elif result["status"] == "EMPTY":
            stats["empty"] += 1
        else:  # FAIL
            stats["fail"] += 1
            stats["failed_names"].append(feed["name"])
            logger.warning(f"Feed falhou: {feed['name']} — {result['error']}")

    # FIX 1.5 — Removida filtragem de seen_links aqui.
    # TODA a deduplicação cross-dia é feita no curator.

    logger.info(
        f"Scan completo: {stats['ok']} OK, {stats['empty']} vazios, "
        f"{stats['fail']} falhas"
    )
    logger.info(f"Scanner: {len(all_articles)} artigos dos feeds")
    # Fontes API gratuitas — complemento com priority=3 (não crítico)
    try:
        from news_sources import fetch_all_api_sources
        api_articles = fetch_all_api_sources()
        all_articles.extend(api_articles)
        logger.info(f"Scanner: +{len(api_articles)} artigos via API (priority=3)")
    except Exception as e:
        logger.warning(f"API sources falhou (não crítico): {e}")
    logger.info(f"Scanner: total final {len(all_articles)} artigos")
    return all_articles, stats
