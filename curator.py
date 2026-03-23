"""
SimulaNewsMachine — Curadoria e scoring de artigos.

Deduplica, pontua, garante diversidade, seleciona top 15.
"""

import json
import logging
import re
import string
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, urlencode

from config import (
    MAX_ARTICLES_OUTPUT, MIN_RELEVANCE_SCORE, SEEN_LINKS_FILE,
    GUARANTEE_CATEGORIES, GUARANTEE_PORTUGAL,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Keywords para scoring
# ============================================================================

HIGH_RELEVANCE_KEYWORDS = [
    "update", "patch", "release", "launch", "announce", "reveal",
    "new car", "new track", "new content", "dlc", "expansion",
    "season", "championship", "esport", "world series",
    "sim racing", "simracing", "simulator",
    "iracing", "assetto corsa", "acc", "evo",
    "le mans", "lemans", "rfactor", "automobilista",
    "rennsport", "raceroom", "beamng",
    "review", "comparison", "versus", "first look", "hands-on",
    "ets2", "euro truck", "farming simulator", "fs25", "fs22",
    "msfs", "flight simulator", "x-plane",
    "forza", "gran turismo", "gt7", "need for speed", "nfs",
    "f1 24", "f1 25", "f1 game", "ea sports f1",
]

BRAND_KEYWORDS = [
    "moza", "simucube", "sim-lab", "simlab", "heusinkveld",
    "fanatec", "thrustmaster", "simagic", "asetek",
    "trak racer", "next level racing", "playseat",
    "cubcontrols", "cube controls",
]

NOSTALGIA_KEYWORDS = [
    "ets2", "euro truck simulator", "american truck simulator", "ats",
    "farming simulator", "fs25", "fs22", "fs19",
    "flight simulator", "msfs", "msfs2024", "msfs 2024", "x-plane",
    "train sim", "flightsim",
]

RACING_GAMES_KEYWORDS = [
    "forza motorsport", "forza horizon", "gran turismo", "gt7",
    "need for speed", "nfs", "f1 24", "f1 25", "f1 game",
    "test drive unlimited", "tdu", "grid", "dirt rally",
    "wrc", "ea sports",
]

CROSSOVER_KEYWORDS = [
    "real driver", "pro driver", "f1 driver", "nascar driver",
    "indycar driver", "wec driver", "real vs sim", "sim to real",
    "real to sim", "professional racer", "max verstappen sim",
    "lando norris sim", "charles leclerc sim",
]

PORTUGAL_KEYWORDS = [
    "portugal", "português", "portuguese", "lisboa", "porto",
    "ibéria", "iberia", "espanha", "spain", "spanish",
    "portimão", "algarve", "estoril",
]

LOW_VALUE_KEYWORDS = [
    "livery pack", "skin pack", "reshade preset", "texture mod",
    "paint scheme", "livery collection",
]

# Stopwords para dedup de títulos
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more", "most",
    "other", "some", "such", "no", "only", "own", "same", "than",
    "too", "very", "just", "because", "how", "what", "which", "who",
    "whom", "this", "that", "these", "those", "it", "its",
    "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
    "um", "uma", "o", "os", "as", "e", "ou", "com", "por", "para",
    "que", "se", "não", "mais", "muito", "também", "já", "ainda",
    "new", "now", "get", "out", "up",
}


def _canonicalize_url(url):
    """Normaliza URL para dedup: remove query params de tracking, www, trailing slash."""
    try:
        parsed = urlparse(url)
        # Remover www
        host = parsed.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        # Filtrar query params de tracking
        params = parse_qs(parsed.query)
        clean_params = {
            k: v for k, v in params.items()
            if not k.startswith("utm_") and k not in ("ref", "source", "fbclid", "gclid")
        }
        clean_query = urlencode(clean_params, doseq=True) if clean_params else ""
        # Remover trailing slash
        path = parsed.path.rstrip("/")
        return f"{host}{path}{'?' + clean_query if clean_query else ''}"
    except Exception:
        return url.lower().strip()


def _normalize_title(title):
    """Normaliza título para comparação: lowercase, sem pontuação, sem stopwords."""
    title = title.lower()
    title = title.translate(str.maketrans("", "", string.punctuation))
    tokens = title.split()
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    return tokens


def _title_similarity(tokens1, tokens2):
    """Retorna percentagem de tokens em comum."""
    if not tokens1 or not tokens2:
        return 0.0
    set1, set2 = set(tokens1), set(tokens2)
    common = set1 & set2
    max_len = max(len(set1), len(set2))
    return len(common) / max_len if max_len else 0.0


def _score_article(article):
    """Calcula score de relevância (0-100) para um artigo."""
    score = 0

    # Base: priority * 3 (max 30)
    score += min(article["priority"] * 3, 30)

    text = f"{article['title']} {article.get('summary', '')}".lower()

    # Keywords alta relevância: +5 cada (max 20)
    kw_bonus = 0
    for kw in HIGH_RELEVANCE_KEYWORDS:
        if kw in text:
            kw_bonus += 5
    score += min(kw_bonus, 20)

    # Nossas marcas: +10
    for brand in BRAND_KEYWORDS:
        if brand in text:
            score += 10
            break

    # Nostalgia: +10
    for kw in NOSTALGIA_KEYWORDS:
        if kw in text:
            score += 10
            break

    # Racing Games: +8
    for kw in RACING_GAMES_KEYWORDS:
        if kw in text:
            score += 8
            break

    # Crossover real-sim: +15
    for kw in CROSSOVER_KEYWORDS:
        if kw in text:
            score += 15
            break

    # Portugal/Ibéria: +12
    for kw in PORTUGAL_KEYWORDS:
        if kw in text:
            score += 12
            break

    # Artigo sem data: -15
    if article.get("no_date"):
        score -= 15

    # Conteúdo de baixo valor: -10
    for kw in LOW_VALUE_KEYWORDS:
        if kw in text:
            score -= 10
            break

    return max(score, 0)


def _load_seen_links():
    """Carrega seen_links.json."""
    if SEEN_LINKS_FILE.exists():
        try:
            with open(SEEN_LINKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_seen_links(seen):
    """Guarda seen_links.json."""
    try:
        with open(SEEN_LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(seen, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Erro ao guardar seen_links: {e}")


def curate_articles(articles):
    """
    Recebe lista crua do scanner, deduplica, pontua, seleciona top 15.
    Retorna dict com metadata e lista selecionada.
    """
    if not articles:
        return {
            "selected": [],
            "total_before_dedup": 0,
            "total_after_dedup": 0,
            "categories": {},
        }

    total_before = len(articles)

    # ========================================================================
    # Dedup camada 1: Link canónico
    # ========================================================================
    seen_urls = {}
    deduped_by_url = []
    for article in articles:
        canon = _canonicalize_url(article["link"])
        if canon in seen_urls:
            # Manter o de maior priority
            existing = seen_urls[canon]
            if article["priority"] > existing["priority"]:
                deduped_by_url.remove(existing)
                deduped_by_url.append(article)
                seen_urls[canon] = article
        else:
            seen_urls[canon] = article
            deduped_by_url.append(article)

    # ========================================================================
    # Dedup camada 2: Título normalizado (>65% tokens em comum)
    # ========================================================================
    deduped_by_title = []
    title_tokens_list = []
    for article in deduped_by_url:
        tokens = _normalize_title(article["title"])
        is_dup = False
        for i, existing_tokens in enumerate(title_tokens_list):
            if _title_similarity(tokens, existing_tokens) > 0.65:
                # Manter o de maior priority
                if article["priority"] > deduped_by_title[i]["priority"]:
                    deduped_by_title[i] = article
                    title_tokens_list[i] = tokens
                is_dup = True
                break
        if not is_dup:
            deduped_by_title.append(article)
            title_tokens_list.append(tokens)

    # ========================================================================
    # Dedup camada 3: Cross-dia (seen_links.json)
    # ========================================================================
    seen_links = _load_seen_links()
    deduped = [a for a in deduped_by_title if a["link"] not in seen_links]

    total_after = len(deduped)
    logger.info(f"Dedup: {total_before} → {total_after} artigos")

    # ========================================================================
    # Scoring
    # ========================================================================
    for article in deduped:
        article["score"] = _score_article(article)

    # Bónus novidade de fonte pouco recorrente
    source_counts = {}
    for link, ts in seen_links.items():
        # Não temos source nos seen_links, skip
        pass

    # Ordenar por score desc
    deduped.sort(key=lambda a: a["score"], reverse=True)

    # ========================================================================
    # Garantir diversidade de categorias
    # ========================================================================
    selected = []
    used_indices = set()

    # Primeiro: garantir categorias mínimas
    for cat, min_count in GUARANTEE_CATEGORIES.items():
        cat_articles = [
            (i, a) for i, a in enumerate(deduped)
            if a["category"] == cat and i not in used_indices and a["score"] >= MIN_RELEVANCE_SCORE
        ]
        for j in range(min(min_count, len(cat_articles))):
            idx, article = cat_articles[j]
            selected.append(article)
            used_indices.add(idx)

    # Garantir Portugal se disponível
    if GUARANTEE_PORTUGAL:
        pt_articles = [
            (i, a) for i, a in enumerate(deduped)
            if a["category"] == "portugal" and i not in used_indices
        ]
        if pt_articles:
            idx, article = pt_articles[0]
            selected.append(article)
            used_indices.add(idx)

    # Preencher restantes por score
    for i, article in enumerate(deduped):
        if len(selected) >= MAX_ARTICLES_OUTPUT:
            break
        if i not in used_indices and article["score"] >= MIN_RELEVANCE_SCORE:
            selected.append(article)
            used_indices.add(i)

    # Se não temos 15, baixar o threshold
    if len(selected) < MAX_ARTICLES_OUTPUT:
        for i, article in enumerate(deduped):
            if len(selected) >= MAX_ARTICLES_OUTPUT:
                break
            if i not in used_indices:
                selected.append(article)
                used_indices.add(i)

    # Re-ordenar selecção por score
    selected.sort(key=lambda a: a["score"], reverse=True)

    # ========================================================================
    # Actualizar seen_links com links seleccionados
    # ========================================================================
    now_iso = datetime.now(timezone.utc).isoformat()
    for article in selected:
        seen_links[article["link"]] = now_iso
    _save_seen_links(seen_links)

    # ========================================================================
    # Contagem por categoria
    # ========================================================================
    categories = {}
    for article in selected:
        cat = article["category"]
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "selected": selected,
        "total_before_dedup": total_before,
        "total_after_dedup": total_after,
        "categories": categories,
    }
