"""
SimulaNewsMachine — Curadoria e scoring de artigos.

Deduplica, pontua, garante diversidade, seleciona top 15.
"""

import json
import logging
import os
import re
import string
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs, urlencode

from config import (
    MAX_ARTICLES_OUTPUT, MIN_RELEVANCE_SCORE, SEEN_LINKS_FILE,
    GUARANTEE_CATEGORIES, GUARANTEE_PORTUGAL, MAX_PER_SOURCE,
    MAX_PER_SOURCE_YOUTUBE,
    SEEN_LINKS_MAX_AGE_HOURS,
)

logger = logging.getLogger(__name__)

# Flag controlada por main.py para modo dry-run (não escrever ficheiros de estado)
_DRY_RUN = False

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

# FIX 2.3 — Separar marcas parceiras de concorrentes
OUR_BRANDS = [
    "moza", "simucube", "sim-lab", "simlab", "heusinkveld", "akracing",
]

OTHER_HARDWARE_BRANDS = [
    "fanatec", "thrustmaster", "simagic", "asetek",
    "trak racer", "next level racing", "playseat",
    "cube controls",
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

# FIX 2.4 — Keywords Portugal expandidas
PORTUGAL_KEYWORDS = [
    "portugal", "português", "portuguese", "lisboa", "porto",
    "ibéria", "iberia", "espanha", "spain",
    "portimão", "algarve", "estoril",
    "fpak",
    "torres vedras",
    "simracing portugal",
    "srp",
    "rally de portugal",
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

YOUTUBE_CHANNEL_NOISE_PATTERNS = [
    "discounts", "coupons", "coupon", "affiliate", "patreon.com",
    "g2a.com", "nohesi.gg", "discord.gg/", "twitch.tv/",
    "*available*", "*here*", "join my discord", "join the discord",
    "check out my", "use code", "sponsor",
]

YOUTUBE_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
YOUTUBE_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


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


def _youtube_summary_useful_length(summary):
    """Conta caracteres úteis do summary YouTube após remover URLs e emojis."""
    cleaned = YOUTUBE_URL_RE.sub(" ", summary or "")
    cleaned = YOUTUBE_EMOJI_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    useful = re.sub(r"[^0-9A-Za-zÀ-ÿ]", "", cleaned)
    return len(useful)


def _is_youtube_source(article):
    """Detecta artigos provenientes de feeds YouTube no formato actual do repositório."""
    source = article.get("source", "")
    link = (article.get("link") or "").lower()
    return (
        source.startswith("YT ")
        or "YouTube" in source
        or source.endswith(" YT")
        or "youtube.com/watch" in link
        or "youtube.com/shorts" in link
    )


def _is_youtube_channel_noise(article):
    """Detecta descrições de canal/promocionais vindas de feeds YouTube."""
    if not _is_youtube_source(article):
        return False

    link = (article.get("link") or "").lower()
    if "youtube.com/watch" not in link and "youtube.com/shorts" not in link:
        return False

    summary = (article.get("summary") or "").lower()
    matched_patterns = sum(1 for pattern in YOUTUBE_CHANNEL_NOISE_PATTERNS if pattern in summary)
    return matched_patterns >= 3


def _max_articles_for_source(article):
    """Aplica limite diferenciado para fontes YouTube."""
    is_youtube = _is_youtube_source(article)
    return MAX_PER_SOURCE_YOUTUBE if is_youtube else MAX_PER_SOURCE


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

    # FIX 2.3 — Marcas parceiras: +10
    for brand in OUR_BRANDS:
        if brand in text:
            score += 10
            break

    # FIX 2.3 — Outras marcas hardware: +5 (não +10)
    for brand in OTHER_HARDWARE_BRANDS:
        if brand in text:
            score += 5
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

    # Engagement bonus preditivo (cap +10)
    eng = _engagement_bonus(article)
    if eng > 0:
        score += eng
        logger.debug("Engagement bonus +%d para: %s", eng, article.get("title", "")[:60])

    return max(min(score, 100), 0)


def _engagement_bonus(article: dict) -> int:
    """
    Bonus de engagement preditivo. Cap: 10 pontos.
    Baseado em sinais de título que correlacionam
    com melhor performance editorial.
    """
    try:
        title = article.get("title", "")
        if not title:
            return 0
        bonus = 0
        # Comprimento óptimo (50-70 chars performam melhor)
        if 50 <= len(title) <= 70:
            bonus += 3
        # Números no título ("Top 5", "2026", "GT3")
        if re.search(r'\d+', title):
            bonus += 2
        # Comparações
        if any(kw in title.lower() for kw in
               ["vs", "versus", "compared", "comparison",
                "vs.", "against", "better than"]):
            bonus += 3
        # Nomes de pilotos conhecidos (sim racing + motorsport)
        known_names = [
            "verstappen", "norris", "leclerc", "hamilton",
            "alonso", "sainz", "russell", "piastri",
            "vandoorne", "de vries"
        ]
        if any(name in title.lower() for name in known_names):
            bonus += 5
        return min(bonus, 10)
    except Exception:
        return 0


# FIX 2.6 — seen_links agora guarda metadata (ts, source, title)
def _load_seen_links():
    """Carrega seen_links.json. Limpa entradas com mais de SEEN_LINKS_MAX_AGE_HOURS."""
    if not SEEN_LINKS_FILE.exists():
        return {}
    try:
        with open(SEEN_LINKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    cutoff = datetime.now(timezone.utc) - timedelta(hours=SEEN_LINKS_MAX_AGE_HOURS)
    cleaned = {}
    for link, value in data.items():
        try:
            # Suportar formato novo (dict com ts) e antigo (string ISO)
            if isinstance(value, dict):
                ts_str = value.get("ts", "")
            else:
                ts_str = value
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts > cutoff:
                cleaned[link] = value
        except (ValueError, TypeError):
            pass
    return cleaned


# FIX 2.7 — Escrita atómica de seen_links.json
def _save_seen_links(seen):
    """Guarda seen_links.json atomicamente."""
    if _DRY_RUN:
        logger.info("DRY RUN — seen_links.json não actualizado")
        return
    try:
        tmp = SEEN_LINKS_FILE.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(seen, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp), str(SEEN_LINKS_FILE))
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

    filtered_articles = []
    for article in articles:
        is_youtube_article = _is_youtube_source(article)

        if is_youtube_article and _youtube_summary_useful_length(article.get("summary", "")) < 20:
            logger.info(f"FILTRADO: resumo YouTube vazio/curto — {article['title']}")
            continue

        if _is_youtube_channel_noise(article):
            logger.info(f"FILTRADO: descrição de canal YouTube — {article['title']}")
            continue

        filtered_articles.append(article)
    articles = filtered_articles

    # ========================================================================
    # Dedup camada 1: Link canónico
    # ========================================================================
    seen_urls = {}
    deduped_by_url = []
    for article in articles:
        canon = _canonicalize_url(article["link"])
        if canon in seen_urls:
            existing = seen_urls[canon]
            if article["priority"] > existing["priority"]:
                deduped_by_url.remove(existing)
                deduped_by_url.append(article)
                seen_urls[canon] = article
        else:
            seen_urls[canon] = article
            deduped_by_url.append(article)

    # ========================================================================
    # Dedup camada 2: Título normalizado (>55% tokens em comum)
    # ========================================================================
    deduped_by_title = []
    title_tokens_list = []
    for article in deduped_by_url:
        tokens = _normalize_title(article["title"])
        is_dup = False
        for i, existing_tokens in enumerate(title_tokens_list):
            if _title_similarity(tokens, existing_tokens) > 0.55:
                if article["priority"] > deduped_by_title[i]["priority"]:
                    deduped_by_title[i] = article
                    title_tokens_list[i] = tokens
                is_dup = True
                break
        if not is_dup:
            deduped_by_title.append(article)
            title_tokens_list.append(tokens)

    # ========================================================================
    # Dedup camada 3: Cross-dia (seen_links.json) — FIX 2.6: por URL canónica
    # ========================================================================
    seen_links = _load_seen_links()
    deduped = [
        a for a in deduped_by_title
        if _canonicalize_url(a["link"]) not in seen_links
    ]

    total_after = len(deduped)
    logger.info(f"Dedup: {total_before} -> {total_after} artigos")

    # ========================================================================
    # Scoring
    # ========================================================================
    for article in deduped:
        article["score"] = _score_article(article)

    # FIX 2.5 — Source rarity bonus: fontes que não apareceram em briefs recentes +5
    recent_sources = set()
    for entry in seen_links.values():
        if isinstance(entry, dict) and "source" in entry:
            recent_sources.add(entry["source"])
    for article in deduped:
        if article["source"] not in recent_sources:
            article["score"] = min(article["score"] + 5, 100)

    # Ordenar por score desc
    deduped.sort(key=lambda a: a["score"], reverse=True)

    # ========================================================================
    # Instrumentação nostalgia — observabilidade sem alterar seleção
    # ========================================================================
    _nostalgia_raw = [a for a in deduped if a.get("category") == "nostalgia"]
    _nostalgia_above_threshold = [a for a in _nostalgia_raw if a.get("score", 0) >= MIN_RELEVANCE_SCORE]
    logger.info(f"Curator: nostalgia raw candidates={len(_nostalgia_raw)}")
    logger.info(f"Curator: nostalgia above threshold (>={MIN_RELEVANCE_SCORE})={len(_nostalgia_above_threshold)}")
    if _nostalgia_raw and not _nostalgia_above_threshold:
        top_score = max((a.get("score", 0) for a in _nostalgia_raw), default=0)
        logger.info(f"Curator: nostalgia top score={top_score} (abaixo do threshold {MIN_RELEVANCE_SCORE})")

    # ========================================================================
    # Garantir diversidade de categorias
    # ========================================================================
    selected = []
    used_indices = set()
    source_counts = {}  # FIX 2.1 — Contar fontes para limite por fonte

    # Primeiro: garantir categorias mínimas
    for cat, min_count in GUARANTEE_CATEGORIES.items():
        cat_articles = [
            (i, a) for i, a in enumerate(deduped)
            if a["category"] == cat and i not in used_indices
            and a["score"] >= MIN_RELEVANCE_SCORE
            and source_counts.get(a["source"], 0) < _max_articles_for_source(a)
        ]
        for j in range(min(min_count, len(cat_articles))):
            idx, article = cat_articles[j]
            selected.append(article)
            used_indices.add(idx)
            source_counts[article["source"]] = source_counts.get(article["source"], 0) + 1

    # Garantir Portugal se disponível
    if GUARANTEE_PORTUGAL:
        pt_articles = [
            (i, a) for i, a in enumerate(deduped)
            if a["category"] == "portugal" and i not in used_indices
            and source_counts.get(a["source"], 0) < _max_articles_for_source(a)
        ]
        if pt_articles:
            idx, article = pt_articles[0]
            selected.append(article)
            used_indices.add(idx)
            source_counts[article["source"]] = source_counts.get(article["source"], 0) + 1

    # FIX 2.1 — Preencher restantes por score COM limite por fonte
    for i, article in enumerate(deduped):
        if len(selected) >= MAX_ARTICLES_OUTPUT:
            break
        if i not in used_indices and article["score"] >= MIN_RELEVANCE_SCORE:
            src = article["source"]
            max_allowed = _max_articles_for_source(article)
            if source_counts.get(src, 0) < max_allowed:
                selected.append(article)
                used_indices.add(i)
                source_counts[src] = source_counts.get(src, 0) + 1

    # Se não temos 15, baixar o threshold (mas manter limite por fonte)
    if len(selected) < MAX_ARTICLES_OUTPUT:
        for i, article in enumerate(deduped):
            if len(selected) >= MAX_ARTICLES_OUTPUT:
                break
            if i not in used_indices:
                src = article["source"]
                max_allowed = _max_articles_for_source(article)
                if source_counts.get(src, 0) < max_allowed:
                    selected.append(article)
                    used_indices.add(i)
                    source_counts[src] = source_counts.get(src, 0) + 1

    # Re-ordenar selecção por score
    selected.sort(key=lambda a: a["score"], reverse=True)

    # Instrumentação nostalgia — resultado final
    _nostalgia_selected = sum(1 for a in selected if a.get("category") == "nostalgia")
    logger.info(f"Curator: nostalgia selected={_nostalgia_selected}")
    if _nostalgia_selected == 0 and _nostalgia_above_threshold:
        logger.info("Curator: nostalgia guarantee not filled — candidates existed but lost to source limits or fill order")
    elif _nostalgia_selected == 0 and _nostalgia_raw:
        logger.info("Curator: nostalgia guarantee not filled — no candidates above threshold")
    elif _nostalgia_selected == 0:
        logger.info("Curator: nostalgia guarantee not filled — no raw candidates after dedup")

    # ========================================================================
    # FIX 2.6 — Guardar seen_links por URL canónica com metadata
    # ========================================================================
    now_iso = datetime.now(timezone.utc).isoformat()
    for article in selected:
        canon = _canonicalize_url(article["link"])
        seen_links[canon] = {
            "ts": now_iso,
            "source": article["source"],
            "title": article["title"][:80],
        }
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
