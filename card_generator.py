"""
SimulaNewsMachine — Gerador de social cards Instagram.
Pillow local + assets/. Sem APIs externas.
Fallback gracioso se Pillow ou assets não estiverem disponíveis.
3 templates: news, review, editorial.
"""

import logging
import textwrap
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow não instalado — geração de cards desactivada")

from config import PROJECT_DIR, DESKTOP, GENERATE_IMAGES

W, H = 1080, 1080
CARD_SIZE = (W, H)

# Paleta Simula Project
BLACK      = (10, 10, 10)
RED        = (204, 26, 26)
RED_DARK   = (139, 0, 0)
GRAY_LIGHT = (232, 232, 232)
GRAY_MID   = (136, 136, 136)
GOLD       = (184, 150, 12)
WHITE      = (255, 255, 255)

ASSETS_DIR     = PROJECT_DIR / "assets"
FONT_BOLD      = ASSETS_DIR / "BarlowCondensed-Bold.ttf"
FONT_REGULAR   = ASSETS_DIR / "Barlow-Regular.ttf"
LOGO_WATERMARK = ASSETS_DIR / "logo-watermark.png"
CARDS_OUT      = DESKTOP / "SIMULA_CARDS_HOJE"

CATEGORY_TEMPLATE = {
    "sim_racing":   "news",
    "motorsport":   "news",
    "hardware":     "review",
    "nostalgia":    "editorial",
    "racing_games": "news",
    "esports":      "news",
}

CATEGORY_LABEL = {
    "sim_racing":   "SIM RACING",
    "motorsport":   "MOTORSPORT",
    "hardware":     "HARDWARE",
    "nostalgia":    "NOSTALGIA",
    "racing_games": "RACING GAMES",
    "esports":      "ESPORTS",
}

# Paleta de acento por categoria — alinhada com identidade Simula Project
# hardware usa RED_DARK em vez de azul para coerência visual
CATEGORY_ACCENT = {
    "sim_racing":   RED,
    "motorsport":   RED,
    "hardware":     RED_DARK,
    "nostalgia":    GOLD,
    "racing_games": RED,
    "esports":      RED,
}


def _load_font(path, size):
    try:
        return ImageFont.truetype(str(path), size)
    except (OSError, IOError):
        try:
            fallback_name = "arialbd.ttf" if path == FONT_BOLD else "arial.ttf"
            return ImageFont.truetype(fallback_name, size)
        except OSError:
            return ImageFont.load_default()


def _ensure_logo_alpha(logo):
    """
    Se o logo não tiver canal alpha útil (ex: RGB convertido para RGBA),
    detecta fundo branco/quase branco e torna-o transparente.
    Pixels mais escuros (a forma do logo) ficam com alpha proporcional.
    Se já tiver alpha real, preserva-o.
    """
    logo = logo.convert("RGBA")
    data = list(logo.getdata())

    # Verificar se já tem alpha útil (pelo menos 5% de pixels não-opacos)
    non_opaque = sum(1 for _, _, _, a in data if a < 250)
    if non_opaque > len(data) * 0.05:
        return logo

    # Sem alpha útil — converter brightness para alpha.
    # Fundo branco (>=250) → transparente. Logo (mais escuro) → visível.
    new_data = []
    for r, g, b, _ in data:
        brightness = (r + g + b) / 3
        if brightness >= 250:
            # Fundo — totalmente transparente
            new_data.append((r, g, b, 0))
        else:
            # Logo — mapear: quanto mais escuro, mais opaco
            # 215 → alpha ~180, 240 → alpha ~60
            alpha = int(255 * (1 - (brightness - 100) / 155)) if brightness > 100 else 255
            alpha = max(0, min(255, alpha))
            new_data.append((r, g, b, alpha))
    logo.putdata(new_data)
    return logo


def _load_watermark(max_size=130):
    if not LOGO_WATERMARK.exists():
        return None
    try:
        logo = Image.open(LOGO_WATERMARK)
        logo = _ensure_logo_alpha(logo)
        logo.thumbnail((max_size, max_size), Image.LANCZOS)
        return logo
    except Exception:
        return None


def _gradient_bar(draw, y_start, height, color):
    for i in range(height):
        alpha = int(255 * (i / height) ** 0.8)
        draw.line(
            [(0, y_start + i), (W, y_start + i)],
            fill=(color[0], color[1], color[2], alpha)
        )


def _wrap_title(title, max_chars=26):
    """Quebra título em máximo 3 linhas sem cortar palavras."""
    return textwrap.wrap(title, width=max_chars)[:3]


def _paste_watermark(img, opacity=0.40):
    wm = _load_watermark()
    if wm is None:
        return img
    data = [(r, g, b, int(a * opacity)) for r, g, b, a in wm.getdata()]
    wm.putdata(data)
    wx = W - wm.width - 40
    wy = H - wm.height - 45
    img.paste(wm, (wx, wy), wm)
    return img


def _news_card(article):
    img = Image.new("RGBA", CARD_SIZE, (*BLACK, 255))
    ov  = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    d   = ImageDraw.Draw(ov)

    cat    = article.get("category", "sim_racing")
    title  = article.get("title", "")
    source = article.get("source", "")
    accent = CATEGORY_ACCENT.get(cat, RED)
    label  = CATEGORY_LABEL.get(cat, "NOTÍCIA")

    d.rectangle([(0, 0), (W, 3)], fill=(*GOLD, 200))

    f_cat = _load_font(FONT_BOLD, 28)
    bw = len(label) * 17 + 30
    d.rectangle([(30, 18), (30 + bw, 60)], fill=(*accent, 220))
    d.text((45, 24), label, font=f_cat, fill=WHITE)

    _gradient_bar(d, H - 380, 380, BLACK)
    d.rectangle([(40, H - 310), (120, H - 306)], fill=(*RED, 255))

    f_title = _load_font(FONT_BOLD, 56)
    y = H - 295
    for line in _wrap_title(title):
        d.text((42, y + 2), line, font=f_title, fill=(0, 0, 0, 160))
        d.text((40, y),     line, font=f_title, fill=(*GRAY_LIGHT, 255))
        y += 68

    f_src = _load_font(FONT_REGULAR, 24)
    d.text((40, H - 52), f"via {source}", font=f_src, fill=(*GRAY_MID, 200))
    d.text((W - 140, H - 52), datetime.now().strftime("%d.%m.%Y"),
           font=f_src, fill=(*GRAY_MID, 150))

    img = Image.alpha_composite(img, ov)
    img = _paste_watermark(img)
    return img.convert("RGB")


def _review_card(article):
    img = _news_card(article).convert("RGBA")
    ov  = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    d   = ImageDraw.Draw(ov)
    cat   = article.get("category", "hardware")
    badge = "HARDWARE" if cat == "hardware" else "REVIEW"
    accent = CATEGORY_ACCENT.get(cat, RED_DARK)
    f_b = _load_font(FONT_BOLD, 22)
    bw = len(badge) * 14 + 20
    d.rectangle([(W - bw - 30, 18), (W - 30, 54)], fill=(*accent, 200))
    d.text((W - bw - 20, 24), badge, font=f_b, fill=WHITE)
    img = Image.alpha_composite(img, ov)
    return img.convert("RGB")


def _editorial_card(article):
    img = Image.new("RGBA", CARD_SIZE, (8, 8, 8, 255))
    ov  = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    d   = ImageDraw.Draw(ov)

    cat    = article.get("category", "nostalgia")
    title  = article.get("title", "")
    source = article.get("source", "")
    accent = CATEGORY_ACCENT.get(cat, GOLD)
    label  = CATEGORY_LABEL.get(cat, "EDITORIAL")

    for i in range(350):
        alpha = int(25 * (1 - i / 350))
        d.line([(0, i), (i, 0)], fill=(*accent, alpha))

    d.rectangle([(0, 0), (W, 4)], fill=(*accent, 220))

    f_cat = _load_font(FONT_BOLD, 26)
    d.text((40, 26), label, font=f_cat, fill=(*accent, 255))

    _gradient_bar(d, H - 400, 400, (8, 8, 8))
    d.rectangle([(40, H - 320), (120, H - 316)], fill=(*accent, 255))

    f_title = _load_font(FONT_BOLD, 54)
    y = H - 305
    for line in _wrap_title(title, max_chars=28):
        d.text((42, y + 2), line, font=f_title, fill=(0, 0, 0, 150))
        d.text((40, y),     line, font=f_title, fill=(*GRAY_LIGHT, 255))
        y += 66

    f_src = _load_font(FONT_REGULAR, 24)
    d.text((40, H - 52), f"via {source}", font=f_src, fill=(*GRAY_MID, 180))

    img = Image.alpha_composite(img, ov)
    img = _paste_watermark(img, opacity=0.35)
    return img.convert("RGB")


def _digest_cover_article(digest_articles, digest_pack, fallback_category, fallback_label):
    """
    Compatibilidade mínima para digests:
    - usa cover_hook/digest_theme como título de capa
    - usa notes_for_design como subtítulo curto se existir
    - não faz composição completa de carrossel; apenas cria um cover seguro
    """
    digest_articles = digest_articles or []
    digest_pack = digest_pack or {}
    lead_article = digest_articles[0] if digest_articles else {}

    return {
        "title": (
            digest_pack.get("cover_hook")
            or digest_pack.get("digest_theme")
            or lead_article.get("title", fallback_label)
        ),
        "source": (
            (digest_pack.get("notes_for_design") or "")[:60]
            or f"Carrossel editorial — {fallback_label}"
        ),
        "category": lead_article.get("category", fallback_category) or fallback_category,
        "link": lead_article.get("link", ""),
    }


def generate_card(article, index):
    if not PILLOW_AVAILABLE:
        return None
    try:
        CARDS_OUT.mkdir(parents=True, exist_ok=True)
        cat      = article.get("category", "sim_racing")
        template = CATEGORY_TEMPLATE.get(cat, "news")
        if template == "review":
            img = _review_card(article)
        elif template == "editorial":
            img = _editorial_card(article)
        else:
            img = _news_card(article)
        path = CARDS_OUT / f"card_{index:02d}_{cat}.png"
        img.save(str(path), "PNG")
        logger.info(f"Card gerado: {path.name}")
        return str(path)
    except Exception as e:
        logger.warning(f"Card {index} não gerado (não crítico): {e}")
        return None


def generate_instagram_cards(plan):
    if not GENERATE_IMAGES:
        return {}
    results = {}
    # Suporte actual a digests é deliberadamente mínimo:
    # gerar capas seguras para morning/afternoon digest sem redesenhar o sistema.
    # Se o pack não existir, o fallback mantém a lógica antiga por artigo.
    morning_digest = plan.get("instagram_morning_digest", []) or []
    afternoon_digest = plan.get("instagram_afternoon_digest", []) or []
    morning_pack = plan.get("instagram_morning_pack", {}) or {}
    afternoon_pack = plan.get("instagram_afternoon_pack", {}) or {}

    if morning_digest:
        morning_cover = _digest_cover_article(
            morning_digest,
            morning_pack,
            "sim_racing",
            "Morning Digest",
        )
        morning_path = generate_card(morning_cover, 1)
        if morning_path:
            results["morning_digest"] = morning_path
    else:
        ig_sim = plan.get("instagram_sim_racing")
        if ig_sim:
            sim_path = generate_card(ig_sim, 1)
            if sim_path:
                results["sim_racing"] = sim_path

    if afternoon_digest:
        afternoon_cover = _digest_cover_article(
            afternoon_digest,
            afternoon_pack,
            "motorsport",
            "Afternoon Digest",
        )
        moto_path = generate_card(afternoon_cover, 2)
        if moto_path:
            results["afternoon_digest"] = moto_path
    else:
        ig_moto = plan.get("instagram_motorsport")
        if ig_moto:
            moto_path = generate_card(ig_moto, 2)
            if moto_path:
                results["motorsport"] = moto_path
    if results:
        logger.info(f"Cards Instagram em: {CARDS_OUT}")
    return results
