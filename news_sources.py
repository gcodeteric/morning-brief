"""
SimulaNewsMachine — Fontes de notícias via API gratuita
NewsAPI + GNews + Reddit PRAW
Complementam os RSS feeds existentes com priority=3 (RSS usam 5-10).
"""

import logging
import os
import requests
from datetime import datetime, timezone
from collections import Counter

logger = logging.getLogger(__name__)

NEWSAPI_KEY          = os.environ.get("NEWSAPI_KEY", "")
GNEWS_KEY            = os.environ.get("GNEWS_KEY", "")
REDDIT_CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT    = "SimulaMorningBrief/2.0"

# Mapeamento subreddit → categoria compatível com o curador existente
SUBREDDIT_CATEGORY = {
    "simracing":    "sim_racing",
    "iRacing":      "sim_racing",
    "assettocorsa": "sim_racing",
    "BeamNG":       "sim_racing",
    "granturismo":  "racing_games",
    "trucksim":     "nostalgia",
}

SIM_RACING_QUERY = (
    "sim racing OR simracing OR iRacing OR \"Assetto Corsa\" "
    "OR Moza Racing OR direct drive OR racing pedals OR sim wheel"
)
MOTORSPORT_QUERY = (
    "Formula 1 OR MotoGP OR WEC OR Le Mans OR NASCAR OR motorsport"
)


def _is_key_valid(key: str) -> bool:
    return bool(key) and len(key) > 8


def _normalize(raw: dict, source_name: str, category: str = "sim_racing") -> dict:
    return {
        "title":       raw.get("title", ""),
        "summary":     raw.get("description") or raw.get("content") or "",
        "link":        raw.get("url") or raw.get("link") or "",
        "source":      source_name,
        "priority":    3,
        "category":    category,
        "published":   raw.get("publishedAt") or "",
        "no_date":     False,
        "source_type": "api",
    }


def fetch_newsapi(query: str, page_size: int, category: str) -> list:
    if not _is_key_valid(NEWSAPI_KEY):
        return []
    try:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "language": "en", "sortBy": "publishedAt",
                    "pageSize": page_size, "apiKey": NEWSAPI_KEY},
            timeout=10
        )
        r.raise_for_status()
        result = [_normalize(a, a.get("source", {}).get("name", "NewsAPI"), category)
                  for a in r.json().get("articles", [])]
        logger.info(f"NewsAPI [{category}]: {len(result)} artigos")
        return result
    except Exception as e:
        logger.warning(f"NewsAPI falhou: {e}")
        return []


def fetch_gnews(query: str, max_results: int, category: str) -> list:
    if not _is_key_valid(GNEWS_KEY):
        return []
    try:
        r = requests.get(
            "https://gnews.io/api/v4/search",
            params={"q": query, "lang": "en", "max": max_results,
                    "apikey": GNEWS_KEY},
            timeout=10
        )
        r.raise_for_status()
        result = [_normalize(a, a.get("source", {}).get("name", "GNews"), category)
                  for a in r.json().get("articles", [])]
        logger.info(f"GNews [{category}]: {len(result)} artigos")
        return result
    except Exception as e:
        logger.warning(f"GNews falhou: {e}")
        return []


def fetch_reddit_simracing(limit: int = 20, min_score: int = 50) -> list:
    if not _is_key_valid(REDDIT_CLIENT_ID):
        return []
    try:
        try:
            import praw
        except ImportError:
            logger.warning("Reddit desactivado: praw não instalado")
            return []
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
        posts = []
        for sub, cat in SUBREDDIT_CATEGORY.items():
            for post in reddit.subreddit(sub).hot(limit=limit):
                if post.score >= min_score and not post.stickied:
                    posts.append({
                        "title":        post.title,
                        "summary":      post.selftext[:600] if post.selftext else post.title,
                        "link":         f"https://reddit.com{post.permalink}",
                        "source":       f"r/{sub}",
                        "priority":     3,
                        "category":     cat,
                        "published":    datetime.fromtimestamp(
                                            post.created_utc, tz=timezone.utc).isoformat(),
                        "no_date":      False,
                        "source_type":  "api",
                        "reddit_score": post.score,
                    })
        posts.sort(key=lambda x: x.get("reddit_score", 0), reverse=True)
        logger.info(f"Reddit: {len(posts[:15])} posts (min_score={min_score})")
        return posts[:15]
    except Exception as e:
        logger.warning(f"Reddit falhou: {e}")
        return []


def fetch_all_api_sources() -> list:
    """Agrega todas as fontes API. Chamado pelo scanner.py."""
    articles = []
    articles += fetch_newsapi(SIM_RACING_QUERY,  15, "sim_racing")
    articles += fetch_newsapi(MOTORSPORT_QUERY,  10, "motorsport")
    articles += fetch_gnews("sim racing simulator", 10, "sim_racing")
    articles += fetch_reddit_simracing()

    # Log por categoria para detetar enviesamento rápido
    if articles:
        cat_counts = Counter(a.get("category", "unknown") for a in articles)
        for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   API mix: {cat} = {count} artigos")
    logger.info(f"API sources total: {len(articles)} artigos (priority=3)")
    return articles
