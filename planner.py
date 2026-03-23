"""
SimulaNewsMachine — Planner editorial.
Camada entre curator e formatter.
Decide quais artigos vão para cada canal com base na estratégia editorial.

NOTA: youtube_weekly = selected[:5] é um fallback temporário.
Não representa um resumo real da semana — não há memória semanal ainda.
Documentado aqui para não criar expectativas falsas.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DISCORD_MIN_SCORE = 35


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
    promo_signals = ["oferta", "desconto", "compra", "sponsored", "ad:", "patrocinado"]
    eligible = []
    for a in articles:
        link = a.get("link", "")
        title_lower = a.get("title", "").lower()
        score = a.get("score", 0)
        is_short = "youtube.com/shorts" in link
        is_promo = any(p in title_lower for p in promo_signals)
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
    return candidates[0] if candidates else (articles[0] if articles else None)


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


def plan(curated):
    selected = curated.get("selected", [])
    now = datetime.now()
    is_sunday = (now.weekday() == 6)

    ig_sim = _best_by_category(selected, "sim_racing")
    ig_moto = _best_by_category(selected, "motorsport")

    # Fallback: se não houver motorsport, usar melhor alternativa distinta
    if ig_moto is None:
        ig_moto = _pick_distinct_secondary(selected, ig_sim)

    # Protecção explícita contra duplicação; tenta alternativa antes de anular
    if ig_moto is not None and ig_moto == ig_sim:
        alt = _pick_distinct_secondary(selected, ig_sim)
        if alt is not None and alt != ig_sim:
            ig_moto = alt
        else:
            ig_moto = None
            logger.warning("Planner: não foi possível encontrar segundo artigo distinto para IG/X")

    yt_daily = _youtube_daily_candidate(selected)

    # NOTA: youtube_weekly é um proxy do top 5 de hoje, não um resumo real da semana
    # A memória semanal real ainda não está implementada — este é um fallback temporário
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
        "youtube_weekly": yt_weekly,  # fallback temporário: top 5 de hoje
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
