"""
SimulaNewsMachine — Planner editorial.
Camada entre curator e formatter.
Decide quais artigos vão para cada canal com base na estratégia editorial.
"""

import json
import logging
import os
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

WEEKLY_CACHE_FILE = Path(__file__).parent / "data" / "weekly_cache.json"

DISCORD_MIN_SCORE = 35


def _normalize_text(text):
    """Normaliza texto para comparação simples e robusta."""
    text = (text or "").lower()
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _best_by_category(articles, category):
    candidates = [a for a in articles if a.get("category") == category]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x.get("score", 0))


def _reddit_eligible(articles):
    """
    Artigos elegíveis para Reddit:
    - Score >= 40
    - Não são YouTube Shorts
    - Sem linguagem claramente promocional no título
    """
    promo_signals = [
        "oferta", "desconto", "disconto", "promo", "promocao",
        "sponsored", "patrocinado", "affiliate", "afiliado",
        "deal", "compra",
    ]
    eligible = []
    for a in articles:
        link = a.get("link", "")
        title_normalized = _normalize_text(a.get("title", ""))
        score = a.get("score", 0)
        is_short = "youtube.com/shorts" in link
        is_promo = any(p in title_normalized for p in promo_signals)
        if not is_short and not is_promo and score >= 40:
            eligible.append(a)
    eligible.sort(key=lambda x: x.get("score", 0), reverse=True)
    return eligible[:3]


def _youtube_daily_candidate(articles):
    priority_keywords = [
        "review", "first look", "hands-on", "update", "patch",
        "release", "launch", "new", "announce",
    ]
    candidates = [
        a for a in articles
        if "youtube.com/shorts" not in a.get("link", "")
    ]

    def priority_score(a):
        title_lower = a.get("title", "").lower()
        kw_bonus = sum(1 for kw in priority_keywords if kw in title_lower) * 10
        return a.get("score", 0) + kw_bonus

    candidates.sort(key=priority_score, reverse=True)
    if candidates:
        return candidates[0]

    logger.info("Planner: sem candidato válido para YouTube daily (todos eram Shorts ou lista vazia)")
    return None


def _pick_distinct_secondary(selected, primary):
    """
    Escolhe um artigo alternativo diferente do primary.
    Ordem:
    1) outro motorsport
    2) segunda melhor sim_racing
    3) melhor artigo restante não usado
    """
    if not selected:
        return None

    motorsport_candidates = sorted(
        [a for a in selected if a.get("category") == "motorsport" and a != primary],
        key=lambda x: x.get("score", 0),
        reverse=True
    )
    if motorsport_candidates:
        return motorsport_candidates[0]

    sim_candidates = sorted(
        [a for a in selected if a.get("category") == "sim_racing" and a != primary],
        key=lambda x: x.get("score", 0),
        reverse=True
    )
    if sim_candidates:
        return sim_candidates[0]

    remaining = sorted(
        [a for a in selected if a != primary],
        key=lambda x: x.get("score", 0),
        reverse=True
    )
    return remaining[0] if remaining else None


def _load_weekly_cache():
    """Carrega weekly_cache.json. Descarta entries com mais de 7 dias ou corruptas."""
    if not WEEKLY_CACHE_FILE.exists():
        return []
    try:
        with open(WEEKLY_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
    except Exception:
        return []

    cutoff = datetime.now() - timedelta(days=7)
    valid = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        try:
            added_at = datetime.fromisoformat(entry["added_at"])
            if added_at >= cutoff:
                valid.append(entry)
        except (KeyError, ValueError, TypeError):
            continue
    return valid


def _save_weekly_cache(entries):
    """Guarda weekly_cache.json atomicamente."""
    try:
        WEEKLY_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = WEEKLY_CACHE_FILE.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp), str(WEEKLY_CACHE_FILE))
    except Exception as e:
        logger.warning(f"Erro ao guardar weekly_cache: {e}")


def _get_youtube_weekly(selected, is_sunday):
    """
    Memória semanal real para YouTube roundup.
    Acumula top 3 de cada dia. Ao domingo devolve top 5 da semana por score.
    """
    cache = _load_weekly_cache()
    now_iso = datetime.now().isoformat()

    # Adicionar top 3 de hoje ao cache (dedup por link)
    existing_links = {e.get("link") for e in cache}
    added = 0
    for article in selected[:3]:
        link = article.get("link", "")
        if link and link not in existing_links:
            cache.append({
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "link": link,
                "summary": article.get("summary", ""),
                "category": article.get("category", ""),
                "score": article.get("score", 0),
                "added_at": now_iso,
            })
            existing_links.add(link)
            added += 1

    _save_weekly_cache(cache)
    logger.info(f"Planner: weekly cache={len(cache)} entries (+{added} hoje)")

    if is_sunday:
        # Top 5 da semana por score
        ranked = sorted(cache, key=lambda x: x.get("score", 0), reverse=True)
        return ranked[:5]
    return []


def plan(curated):
    selected = curated.get("selected", [])
    now = datetime.now()
    is_sunday = (now.weekday() == 6)

    ig_sim = _best_by_category(selected, "sim_racing")
    ig_moto = _best_by_category(selected, "motorsport")

    # Fallback: se não houver motorsport, usar melhor alternativa distinta
    if ig_moto is None:
        ig_moto = _pick_distinct_secondary(selected, ig_sim)
        if ig_sim is not None and ig_moto is None and len(selected) == 1:
            logger.info("Planner: apenas 1 artigo disponível — segundo slot IG/X fica vazio para evitar duplicação")

    # Protecção explícita contra duplicação; tenta alternativa antes de anular
    if ig_moto is not None and ig_moto == ig_sim:
        alt = _pick_distinct_secondary(selected, ig_sim)
        if alt is not None and alt != ig_sim:
            ig_moto = alt
        else:
            ig_moto = None
            logger.warning("Planner: não foi possível encontrar segundo artigo distinto para IG/X")

    yt_daily = _youtube_daily_candidate(selected)

    # Memória semanal real — acumula top 3/dia, devolve top 5 ao domingo
    try:
        yt_weekly = _get_youtube_weekly(selected, is_sunday)
    except Exception as e:
        logger.warning(f"youtube_weekly: fallback para selected[:5] (weekly cache indisponível): {e}")
        yt_weekly = selected[:5] if is_sunday else []

    reddit = _reddit_eligible(selected)
    best = selected[0] if selected else None
    discord_post = best if (best and best.get("score", 0) >= DISCORD_MIN_SCORE) else None
    if discord_post is None:
        logger.info("Planner: Discord silêncio hoje — score abaixo do threshold")

    result = {
        "instagram_sim_racing": ig_sim,
        "instagram_motorsport": ig_moto,
        "x_thread_1": ig_sim,
        "x_thread_2": ig_moto,
        "youtube_daily": yt_daily,
        "youtube_weekly": yt_weekly,  # memória semanal real via weekly_cache.json
        "reddit_candidates": reddit,
        "discord_post": discord_post,
        "is_sunday": is_sunday,
    }

    logger.info(f"Planner: IG sim={ig_sim['title'][:40] if ig_sim else 'None'}")
    logger.info(f"Planner: IG moto={ig_moto['title'][:40] if ig_moto else 'None'}")
    logger.info(f"Planner: YT daily={yt_daily['title'][:40] if yt_daily else 'None'}")
    logger.info(f"Planner: Reddit={len(reddit)} candidatos | Discord={'SIM' if discord_post else 'SILÊNCIO'}")
    logger.info(f"Planner: Domingo={is_sunday}")

    return result
