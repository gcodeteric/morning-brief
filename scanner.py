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

from config import HOURS_LOOKBACK, FEED_TIMEOUT_SECONDS, SEEN_LINKS_FILE, SEEN_LINKS_MAX_AGE_HOURS
from feeds import get_all_feeds

logger = logging.getLogger(__name__)


def _load_seen_links():
    """Carrega links já vistos em briefs anteriores."""
    if SEEN_LINKS_FILE.exists():
        try:
            with open(SEEN_LINKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Limpar links com mais de SEEN_LINKS_MAX_AGE_HOURS
            cutoff = datetime.now(timezone.utc) - timedelta(hours=SEEN_LINKS_MAX_AGE_HOURS)
            cleaned = {}
            for link, timestamp_str in data.items():
                try:
                    ts = datetime.fromisoformat(timestamp_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts > cutoff:
                        cleaned[link] = timestamp_str
                except (ValueError, TypeError):
                    pass
            return cleaned
        except Exception:
            return {}
    return {}


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
    """Scan um feed individual. Retorna lista de artigos."""
    url = feed_info["url"]
    name = feed_info["name"]
    category = feed_info["cat"]
    priority = feed_info["p"]
    articles = []

    try:
        # Usar requests com timeout real, depois feedparser para parsing
        try:
            resp = requests.get(url, timeout=FEED_TIMEOUT_SECONDS, headers={
                "User-Agent": "SimulaNewsMachine/2.1"
            })
            parsed = feedparser.parse(resp.content)
        except requests.exceptions.RequestException:
            # Fallback para feedparser directo (alguns feeds precisam)
            parsed = feedparser.parse(url)

        if not parsed.entries:
            logger.debug(f"Feed '{name}' sem entradas")
            return articles

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

    except Exception as e:
        logger.warning(f"Erro ao ler feed '{name}' ({url}): {e}")

    return articles


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
        "fail": 0,
        "failed_names": [],
    }

    for feed in feeds:
        try:
            articles = _scan_single_feed(feed)
            if articles:
                all_articles.extend(articles)
                stats["ok"] += 1
            else:
                # Feed OK mas sem artigos na janela temporal
                stats["ok"] += 1
        except Exception as e:
            logger.warning(f"Feed falhou completamente: {feed['name']} — {e}")
            stats["fail"] += 1
            stats["failed_names"].append(feed["name"])

    # Excluir links já vistos
    seen = _load_seen_links()
    if seen:
        before = len(all_articles)
        all_articles = [a for a in all_articles if a["link"] not in seen]
        excluded = before - len(all_articles)
        if excluded > 0:
            logger.info(f"Excluídos {excluded} artigos já vistos em briefs anteriores")

    logger.info(f"Scan completo: {stats['ok']}/{stats['total']} feeds OK, {len(all_articles)} artigos")
    return all_articles, stats
