"""
SimulaNewsMachine — Pipeline de agentes MiniMax M2.7
Cadeia: Analyst → Copywriter → ImageDir → VoiceDir → QA
Sistema híbrido: corre em paralelo com o formatter existente.
"""

import html
import json
import logging
import os
import re
from time import perf_counter

import requests
from openai import OpenAI

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - fallback covered by extraction cleanup
    BeautifulSoup = None

logger = logging.getLogger(__name__)

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "").strip()
MINIMAX_BASE_URL = "https://api.minimax.io/v1"
MODEL = "MiniMax-M2.7"
AGENT_TIMEOUT_SECONDS = float(os.environ.get("MINIMAX_TIMEOUT_SECONDS", "45"))
ARTICLE_FETCH_TIMEOUT_SECONDS = float(os.environ.get("ARTICLE_FETCH_TIMEOUT_SECONDS", "15"))
ARTICLE_READER_MAX_CHARS = int(os.environ.get("ARTICLE_READER_MAX_CHARS", "12000"))
ARTICLE_READER_MIN_CHARS = int(os.environ.get("ARTICLE_READER_MIN_CHARS", "350"))
ARTICLE_READER_USER_AGENT = "SimulaNewsMachine/2.2"

client = (
    OpenAI(
        api_key=MINIMAX_API_KEY,
        base_url=MINIMAX_BASE_URL,
        timeout=AGENT_TIMEOUT_SECONDS,
    )
    if MINIMAX_API_KEY else None
)

AGENT_PROMPTS = {

# ============================================================================
# Two-agent per-story workflow
# ============================================================================
"article_reader": """
És o agent article_reader do Simula Project.
Recebes:
- metadados da notícia
- URL original
- TEXTO REAL extraído do artigo

MISSÃO:
- ler o texto real do artigo
- resumir factualmente a notícia
- NUNCA escrever copy de publicação
- NUNCA trabalhar apenas do título se o texto do artigo for insuficiente

LÍNGUA:
- PT-PT rigoroso
- curto
- factual

SE O TEXTO EXTRAÍDO NÃO FOR SUFICIENTE:
- devolve EXATAMENTE:
{
  "status": "cannot_access_article",
  "url": "original url",
  "title": "original title"
}

SE FOR SUFICIENTE:
- devolve EXATAMENTE este JSON:
{
  "status": "ok",
  "url": "original url",
  "title": "original title",
  "article_summary": [
    "linha curta 1",
    "linha curta 2",
    "linha curta 3"
  ],
  "key_points": [
    "facto 1",
    "facto 2",
    "facto 3"
  ],
  "angle": "explica em 1 frase porque esta notícia importa",
  "tone_hint": "factual|breaking|community|product|motorsport|nostalgia"
}

REGRAS:
- article_summary = 2 ou 3 linhas curtas
- key_points = 2 a 4 factos curtos
- sem hype
- sem especulação
- sem marketing
- responder APENAS com JSON
""",

"platform_copywriter": """
És o agent platform_copywriter do Simula Project.
Recebes:
- metadados da notícia
- resumo factual já lido do artigo
- key_points
- angle
- tone_hint

MISSÃO:
- gerar output curto, específico e publicável para UMA notícia de cada vez
- NUNCA juntar histórias
- NUNCA criar digests
- NUNCA escrever a partir de title/source/score apenas
- NUNCA gerar prompts cinematográficos

LÍNGUA:
- PT-PT rigoroso
- natural
- curto
- sem tom corporativo

PROIBIDO:
- revolucionário
- incrível
- fantástico
- imperdível
- épico
- não percas

Devolve EXATAMENTE este JSON:
{
  "title": "original news title",
  "url": "original news url",
  "source": "source name",
  "category": "category",
  "score": 0,
  "article_summary": [
    "linha 1",
    "linha 2",
    "linha 3"
  ],
  "instagram": {
    "image_text": {
      "hook": "gancho curto",
      "line_1": "linha curta",
      "line_2": "linha curta"
    },
    "caption": {
      "title": "título curto",
      "body": [
        "linha curta 1",
        "linha curta 2",
        "linha curta 3",
        "linha curta 4"
      ],
      "link": "original news url"
    }
  },
  "x": {
    "post": [
      "linha curta 1",
      "linha curta 2",
      "original news url"
    ]
  },
  "youtube": {
    "title": "título curto de YouTube",
    "hook": "gancho curto",
    "description": [
      "linha curta 1",
      "linha curta 2",
      "linha curta 3"
    ],
    "voice_script": [
      "linha curta 1",
      "linha curta 2",
      "linha curta 3"
    ]
  },
  "reddit": {
    "title": "título para Reddit",
    "body": [
      "linha curta 1",
      "linha curta 2",
      "linha curta 3"
    ]
  },
  "discord": {
    "post": [
      "linha curta 1",
      "linha curta 2",
      "original news url"
    ]
  },
  "email": {
    "subject": "assunto curto",
    "body": [
      "linha curta 1",
      "linha curta 2",
      "linha curta 3"
    ],
    "link": "original news url"
  }
}

REGRAS:
- article_summary deve manter 2-3 linhas factuais
- Instagram: texto curto para imagem + caption curta
- X: directo e compacto
- YouTube: curto, claro, sem floreados
- Reddit: informativo, sem marketing
- Discord: útil e conversacional
- Email: curto e limpo
- responder APENAS com JSON
""",

# ============================================================================
# Single-article editorial prompts
# ============================================================================
"analyst": """
És um analista de conteúdo especializado em sim racing e motorsport.
Recebes um artigo e devolves EXATAMENTE este JSON (zero texto extra):
{
  "content_type": "LANÇAMENTO|EVENTO|COMUNIDADE|NOTÍCIA GERAL",
  "audience": "hardcore|casual|pai-gamer|nostalgia|misto",
  "emotion": "hype|informativo|polémico|inspirador|nostalgia",
  "twist": "facto ou ângulo que a maioria ignora (1-2 frases)",
  "hook_suggestion": "primeira linha sugerida para o post",
  "avoid": "o que NÃO dizer neste post",
  "instagram_format": "carousel_explainer|carousel_breaking|carousel_comparison|reel_fast_update",
  "visual_strength": 0,
  "why_it_matters": "explica em 1-2 frases porque esta notícia importa para a comunidade",
  "community_question": "uma pergunta aberta e forte para comentários"
}

REGRAS ADICIONAIS:
- "carousel_explainer" para notícias técnicas, updates e mudanças com contexto
- "carousel_breaking" para breaking news e anúncios fortes
- "carousel_comparison" para comparações, "vale a pena?" e mudanças de produto
- "reel_fast_update" apenas se a notícia for muito visual e rápida
- "visual_strength" vai de 0 a 10
- Se a notícia não for muito visual, tende para carousel, não Reel
""",

"copywriter": """
És o social media manager do Simula Project — primeiro hub integrado
de sim racing em Portugal.
Recebes os dados do artigo e a análise do Analyst como contexto.

IDENTIDADE DA MARCA:
• Tom: conversa entre pilotos na garagem — técnico, humano, nunca corporativo
• Língua: PT-PT rigoroso. "Tu" ou forma impessoal. NUNCA "você".

REGRAS:
• Usa o hook_suggestion do Analyst como ponto de partida (podes melhorar)
• O output serve primeiro Instagram
• Cada post gira em torno de UMA ideia central
• cover_hook curto e forte
• slides: máximo 5, 1 ideia por slide, texto curto, claro e escaneável
• caption: complementar os slides, não repetir tudo, máximo 4 parágrafos curtos
• 1 emoji por parágrafo máx, CTA implícito nunca forçado
• Inclui "porque isto importa" de forma natural
• Usa a community_question do Analyst como base
• PROIBIDO: "revolucionário" "incrível" "fantástico" "não percas" "imperdível"
• PROIBIDO: "épico"
• Evita o que o Analyst indicou em "avoid"

Devolve EXATAMENTE este JSON (zero texto extra):
{
  "format": "carousel_explainer|carousel_breaking|carousel_comparison|reel_fast_update",
  "cover_hook": "headline curta e forte para a capa",
  "slides": [
    "texto do slide 1",
    "texto do slide 2",
    "texto do slide 3",
    "texto do slide 4",
    "texto do slide 5"
  ],
  "caption": "caption completa em PT-PT",
  "community_question": "pergunta final para comentários",
  "cta_style": "implicit",
  "notes_for_design": "instruções curtas para layout visual"
}
""",

# ============================================================================
# Shared multimodal generation prompts
# ============================================================================
"image_director": """
Generates image prompts for DALL-E / GPT-4o for the Simula Project.

BRAND VISUAL IDENTITY:
• Colors: deep black background, neon red (#E63946) accents, white text
• Aesthetic: cinematic cockpit lighting, premium motorsport photography

RULES:
• No text overlays in the image
• Always end with: "No text. 16:9 ratio. Photorealistic. Sony A7R V with 35mm f/1.4."
• Under 120 words

OUTPUT: only the image prompt, nothing else.
""",

"voice_director": """
Generates ElevenLabs voice scripts in European Portuguese (PT-PT).

RULES:
• Duration: 30-45 seconds (~100-130 palavras)
• Mark [PAUSA] where narrator breathes
• Mark [ÊNFASE] on words to stress
• First word: number, question or strong verb
• Last line always: "SIMULA — onde a corrida começa."

OUTPUT: clean script only, ready to paste into ElevenLabs.
""",

# ============================================================================
# Single-article QA prompt
# ============================================================================
"qa": """
És o editor-chefe do Simula Project. Validas posts antes de publicar.
Devolves EXATAMENTE este JSON (zero texto extra):
{
  "scores": {
    "hook": 0,
    "depth": 0,
    "brand_voice": 0,
    "legal_clear": 0,
    "cta_quality": 0,
    "carousel_clarity": 0,
    "stop_scroll_value": 0
  },
  "average": 0.0,
  "approved": true/false,
  "hashtags": ["15 hashtags mix PT+EN específicas"],
  "issues": ["problemas — lista vazia se aprovado"],
  "improved_hook": "reescrito APENAS se hook < 7, senão null",
  "improved_post": "reescrito APENAS se average < 7.0, senão null"
}
REGRAS:
- "carousel_clarity" avalia se os slides seguem ordem lógica e são fáceis de consumir
- "stop_scroll_value" avalia se a capa / hook faz parar o scroll
- approved = true APENAS se average >= 7.0
- Se hook < 7, preencher improved_hook
- Se average < 7.0, preencher improved_post
""",

# ============================================================================
# Instagram digest prompts
# ============================================================================
"instagram_digest_analyst": """
És um analista editorial de Instagram para o Simula Project.
Recebes um conjunto de 4 a 7 notícias e devolves EXATAMENTE este JSON (zero texto extra):
{
  "digest_theme": "frase curta que resume o fio editorial do carrossel",
  "digest_type": "morning_digest|afternoon_digest",
  "cover_hook": "headline curta e forte para a capa",
  "why_this_set_matters": "porque este conjunto importa hoje",
  "ordering_logic": "explica a ordem ideal dos slides",
  "community_question": "pergunta forte para comentários",
  "visual_style": "editorial_clean|breaking_digest|comparison_digest"
}

REGRAS:
- morning_digest = ecossistema, comunidade, produto, gaming, nostalgia, PT
- afternoon_digest = impacto competitivo, motorsport, corrida, calendário, contexto
- Responder APENAS com JSON
""",

"instagram_digest_copywriter": """
És o social media manager do Simula Project.
Recebes um conjunto de notícias e a análise editorial do digest.

LÍNGUA:
- PT-PT rigoroso

TOM:
- orgânico
- claro
- editorial
- nunca corporativo

Devolve EXATAMENTE este JSON (zero texto extra):
{
  "format": "editorial_digest_carousel",
  "cover_hook": "strong cover headline",
  "digest_theme": "main theme of the carousel",
  "slides": [
    {
      "news_title": "short story headline",
      "mini_summary": "brief summary",
      "why_it_matters": "why it matters"
    }
  ],
  "caption_intro": "short caption opening",
  "caption_news_list": [
    "1. ...",
    "2. ...",
    "3. ..."
  ],
  "community_question": "final question",
  "cta_style": "implicit",
  "notes_for_design": "short design guidance"
}

REGRAS:
- máximo 7 story slides
- mínimo 4 se houver material suficiente, mas nunca inventar histórias
- 1 slide = 1 história
- headline curta e escaneável
- mini_summary curta
- why_it_matters curto
- não transformar isto num wall of text
- 1 ideia central por carrossel
- a caption resume o conjunto, não uma história isolada
- responder APENAS com JSON
""",

# ============================================================================
# Instagram digest QA prompt
# ============================================================================
"instagram_digest_qa": """
És o editor-chefe do Simula Project. Validas carrosséis editoriais antes de publicar.
Devolves EXATAMENTE este JSON (zero texto extra):
{
  "scores": {
    "hook": 0,
    "coherence_of_set": 0,
    "slide_clarity": 0,
    "depth": 0,
    "stop_scroll_value": 0,
    "brand_voice": 0,
    "cta_quality": 0
  },
  "average": 0.0,
  "approved": true/false,
  "hashtags": ["15 hashtags mix PT+EN específicas"],
  "issues": [],
  "improved_hook": null,
  "improved_post": null
}

REGRAS:
- Estás a avaliar um carrossel editorial de Instagram, não um post solto
- O cover hook tem de fazer parar o scroll sem soar barato ou clickbait
- O digest tem de orbitar em torno de uma ideia central clara
- A ordem dos slides tem de fazer sentido editorial
- Cada slide deve ter 1 história, com headline curta, mini_summary clara e why_it_matters relevante
- O conjunto não pode parecer um dump aleatório de notícias
- A densidade deve ser aceitável para Instagram: claro, escaneável e sem wall of text
- A caption deve complementar o carrossel e amarrar o digest, não repetir todos os slides
- A community_question tem de soar natural e abrir conversa real, não engagement bait
- O tom deve ser PT-PT natural, comunitário, editorial e não corporativo
- coherence_of_set: avalia se o conjunto faz sentido como digest
- slide_clarity: avalia se a ordem e densidade dos slides estão boas
- depth: avalia se o digest acrescenta contexto e filtro editorial
- stop_scroll_value: avalia a força do cover hook e da promessa editorial
- cta_quality: avalia se a pergunta final convida à conversa de forma orgânica
- approved = true APENAS se average >= 7.0
- Se hook < 7, preencher improved_hook
- Se average < 7.0, improved_post deve devolver um digest melhorado mantendo o MESMO JSON editorial do copywriter:
  {
    "format": "editorial_digest_carousel",
    "cover_hook": "...",
    "digest_theme": "...",
    "slides": [
      {
        "news_title": "...",
        "mini_summary": "...",
        "why_it_matters": "..."
      }
    ],
    "caption_intro": "...",
    "caption_news_list": ["1. ..."],
    "community_question": "...",
    "cta_style": "implicit",
    "notes_for_design": "..."
  }
- Se average >= 7.0, improved_post deve ser null
- responder APENAS com JSON
"""
}


def _clean_output(text: str) -> str:
    """Remove <think>, blocos ```json e artefactos de modelos de raciocínio."""
    import re
    # Remove blocos <think>
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Remove wrapper ```json ... ``` ou ``` ... ```
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    # Remove caracteres não-latinos isolados (artefactos de modelos multilíngue)
    text = re.sub(r'[^\x00-\x7FÀ-ÿ\u0080-\u024F\n\r\t{}\[\]",:./\-_@#!?()0-9 ]', '', text)
    return text.strip()


def _new_agent_metrics(scope: str) -> dict:
    return {
        "scope": scope,
        "timeout_seconds": AGENT_TIMEOUT_SECONDS,
        "calls_attempted": 0,
        "calls_succeeded": 0,
        "calls_failed": 0,
        "calls_timed_out": 0,
        "calls_skipped": 0,
        "durations": {},
        "parse_failures": [],
        "total_duration_sec": 0.0,
        "useful_output": False,
    }


def _record_duration(metrics: dict | None, agent_name: str, duration: float) -> None:
    if metrics is None:
        return
    metrics.setdefault("durations", {})[agent_name] = round(duration, 3)


def _record_parse_failure(metrics: dict | None, stage: str, error: Exception | str) -> None:
    if metrics is None:
        return
    metrics.setdefault("parse_failures", []).append({
        "stage": stage,
        "error": str(error)[:160],
    })


def _is_timeout_error(error: Exception) -> bool:
    error_name = type(error).__name__.lower()
    error_text = str(error).lower()
    return "timeout" in error_name or "timed out" in error_text or "deadline" in error_text


def _parse_agent_json(raw_text: str, label: str, metrics: dict | None = None) -> dict | None:
    if not raw_text:
        return None
    try:
        parsed = json.loads(raw_text)
        if not isinstance(parsed, dict):
            raise ValueError(f"esperado objecto JSON, veio {type(parsed).__name__}")
        return parsed
    except Exception as e:
        logger.warning("%s JSON inválido — fallback usado: %s", label, e)
        _record_parse_failure(metrics, label, e)
        return None


def _compose_instagram_post(instagram_pack: dict) -> str:
    """Converte o pack estruturado do Copywriter em texto legível para o brief."""
    if not isinstance(instagram_pack, dict) or not instagram_pack:
        return ""

    lines = []
    cover_hook = instagram_pack.get("cover_hook")
    slides = instagram_pack.get("slides", [])
    caption = instagram_pack.get("caption")
    community_question = instagram_pack.get("community_question")

    if cover_hook:
        lines.append(f"Cover Hook: {cover_hook}")

    if isinstance(slides, list) and slides:
        lines.append("Slides:")
        for i, slide in enumerate(slides[:5], 1):
            if slide:
                lines.append(f"{i}. {slide}")

    if caption:
        if lines:
            lines.append("")
        lines.append("Caption:")
        lines.append(caption)

    if community_question:
        if lines:
            lines.append("")
        lines.append("Pergunta à comunidade:")
        lines.append(community_question)

    return "\n".join(lines).strip()


def _compose_instagram_digest_post(instagram_pack: dict) -> str:
    """Converte um digest pack estruturado em texto legível para brief/email."""
    if not isinstance(instagram_pack, dict) or not instagram_pack:
        return ""

    lines = []
    cover_hook = instagram_pack.get("cover_hook")
    digest_theme = instagram_pack.get("digest_theme")
    slides = instagram_pack.get("slides", [])
    caption_intro = instagram_pack.get("caption_intro")
    caption_news_list = instagram_pack.get("caption_news_list", [])
    community_question = instagram_pack.get("community_question")

    if cover_hook:
        lines.append(f"Cover Hook: {cover_hook}")
    if digest_theme:
        lines.append(f"Tema: {digest_theme}")
    if isinstance(slides, list) and slides:
        lines.append("Slides:")
        for i, slide in enumerate(slides[:7], 1):
            if not isinstance(slide, dict):
                continue
            news_title = slide.get("news_title", "")
            mini_summary = slide.get("mini_summary", "")
            why_it_matters = slide.get("why_it_matters", "")
            lines.append(f"{i}. {news_title}")
            if mini_summary:
                lines.append(f"   Resumo: {mini_summary}")
            if why_it_matters:
                lines.append(f"   Porque importa: {why_it_matters}")
    if caption_intro:
        if lines:
            lines.append("")
        lines.append("Caption Intro:")
        lines.append(caption_intro)
    if isinstance(caption_news_list, list) and caption_news_list:
        lines.append("")
        lines.append("Caption News List:")
        for item in caption_news_list[:7]:
            if item:
                lines.append(str(item))
    if community_question:
        lines.append("")
        lines.append("Pergunta à comunidade:")
        lines.append(community_question)

    return "\n".join(lines).strip()


def _build_digest_summary(digest_articles, digest_type):
    lines = [
        f"Digest type: {digest_type}",
        f"Stories: {len(digest_articles)}",
        "",
    ]
    for i, article in enumerate(digest_articles[:7], 1):
        lines.append(
            f"{i}. [{article.get('category', 'unknown')}] "
            f"{article.get('title', '')} — {article.get('source', '')}"
        )
        summary = (article.get("summary") or "")[:260]
        if summary:
            lines.append(f"   Resumo: {summary}")
        lines.append(f"   Score: {article.get('score', 0)}")
        lines.append(f"   Link: {article.get('link', '')}")
    return "\n".join(lines).strip()


def _normalize_article(article: dict | None) -> dict:
    article = article or {}
    return {
        "title": str(article.get("title") or "").strip(),
        "source": str(article.get("source") or "").strip(),
        "summary": str(article.get("summary") or "").strip(),
        "score": int(article.get("score", 0) or 0),
        "link": str(article.get("link") or article.get("url") or "").strip(),
        "category": str(article.get("category") or "unknown").strip() or "unknown",
    }


def _clean_line(text, max_chars: int = 180) -> str:
    cleaned = html.unescape(str(text or ""))
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -•\t\r\n")
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip() + "…"
    return cleaned


def _normalize_lines(value, *, min_items: int = 0, max_items: int = 4, max_chars: int = 180) -> list[str]:
    if isinstance(value, str):
        raw_items = [part for part in re.split(r"[\n\r]+", value) if part.strip()]
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = []

    lines = []
    seen = set()
    for item in raw_items:
        line = _clean_line(item, max_chars=max_chars)
        lowered = line.lower()
        if not line or lowered in seen:
            continue
        seen.add(lowered)
        lines.append(line)
        if len(lines) >= max_items:
            break

    return lines if len(lines) >= min_items else []


def _metadata_summary_lines(article: dict) -> list[str]:
    article = _normalize_article(article)
    summary = _clean_line(article.get("summary", ""), max_chars=170)
    fallback = [
        summary,
        _clean_line(f"Fonte: {article.get('source', 'Fonte desconhecida')}", max_chars=120),
        _clean_line(f"Categoria: {article.get('category', 'unknown')}", max_chars=120),
    ]
    return _normalize_lines(fallback, max_items=3, max_chars=170)


def _extract_article_text(html_text: str) -> str:
    if not html_text:
        return ""

    best_text = ""
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "form", "nav", "header", "footer", "aside"]):
            tag.decompose()

        candidates = []
        for node in [soup.find("article"), soup.find("main"), soup.body, soup]:
            if node is None:
                continue
            text = node.get_text("\n", strip=True)
            text = html.unescape(text)
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{2,}", "\n", text)
            candidates.append(text.strip())
        best_text = max(candidates, key=len, default="")
    else:  # pragma: no cover - exercised only if bs4 is unavailable
        best_text = re.sub(r"<[^>]+>", "\n", html_text)
        best_text = html.unescape(best_text)

    lines = []
    seen = set()
    for line in best_text.splitlines():
        cleaned = _clean_line(line, max_chars=260)
        lowered = cleaned.lower()
        if len(cleaned) < 30 or lowered in seen:
            continue
        seen.add(lowered)
        lines.append(cleaned)
        if len("\n".join(lines)) >= ARTICLE_READER_MAX_CHARS:
            break

    return "\n".join(lines).strip()[:ARTICLE_READER_MAX_CHARS].strip()


def _fetch_article_payload(article: dict) -> dict:
    article = _normalize_article(article)
    url = article.get("link", "")
    if not url:
        return {"status": "cannot_access_article", "url": "", "title": article.get("title", ""), "text": ""}

    try:
        response = requests.get(
            url,
            timeout=ARTICLE_FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": ARTICLE_READER_USER_AGENT},
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.warning("Article fetch failed for %s: %s", url, exc)
        return {"status": "cannot_access_article", "url": url, "title": article.get("title", ""), "text": ""}

    extracted = _extract_article_text(response.text)
    if len(extracted) < ARTICLE_READER_MIN_CHARS:
        logger.warning("Article fetch too thin for %s (%d chars)", url, len(extracted))
        return {"status": "cannot_access_article", "url": url, "title": article.get("title", ""), "text": ""}

    return {"status": "ok", "url": url, "title": article.get("title", ""), "text": extracted}


def _build_article_reader_input(article: dict, article_text: str) -> str:
    article = _normalize_article(article)
    return (
        "METADADOS DA NOTÍCIA\n"
        f"Título: {article.get('title', '')}\n"
        f"Fonte: {article.get('source', '')}\n"
        f"Categoria: {article.get('category', '')}\n"
        f"Score: {article.get('score', 0)}\n"
        f"URL: {article.get('link', '')}\n\n"
        "TEXTO REAL EXTRAÍDO DO ARTIGO\n"
        f"{article_text}"
    ).strip()


def _build_platform_copywriter_input(article: dict, reader_output: dict) -> str:
    article = _normalize_article(article)
    reader_output = reader_output or {}
    payload = {
        "title": article.get("title", ""),
        "url": article.get("link", ""),
        "source": article.get("source", ""),
        "category": article.get("category", ""),
        "score": article.get("score", 0),
        "article_summary": reader_output.get("article_summary", []),
        "key_points": reader_output.get("key_points", []),
        "angle": reader_output.get("angle", ""),
        "tone_hint": reader_output.get("tone_hint", "factual"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_reader_output(payload: dict | None, article: dict) -> dict:
    article = _normalize_article(article)
    failure = {
        "status": "cannot_access_article",
        "url": article.get("link", ""),
        "title": article.get("title", ""),
    }
    if not isinstance(payload, dict):
        return failure

    status = str(payload.get("status") or "").strip().lower()
    if status != "ok":
        return failure

    article_summary = _normalize_lines(payload.get("article_summary", []), min_items=2, max_items=3, max_chars=170)
    key_points = _normalize_lines(payload.get("key_points", []), min_items=2, max_items=4, max_chars=170)
    angle = _clean_line(payload.get("angle", ""), max_chars=180)
    tone_hint = _clean_line(payload.get("tone_hint", "factual"), max_chars=40) or "factual"

    if not article_summary or not key_points or not angle:
        return failure

    return {
        "status": "ok",
        "url": article.get("link", ""),
        "title": article.get("title", ""),
        "article_summary": article_summary,
        "key_points": key_points,
        "angle": angle,
        "tone_hint": tone_hint,
    }


def _normalize_instagram_payload(payload: dict, article: dict, summary_lines: list[str]) -> dict:
    payload = payload if isinstance(payload, dict) else {}
    article = _normalize_article(article)
    image_text = payload.get("image_text", {}) if isinstance(payload.get("image_text"), dict) else {}
    caption = payload.get("caption", {}) if isinstance(payload.get("caption"), dict) else {}

    hook = _clean_line(image_text.get("hook") or article.get("title", ""), max_chars=90)
    line_1 = _clean_line(image_text.get("line_1") or (summary_lines[0] if summary_lines else ""), max_chars=110)
    line_2 = _clean_line(
        image_text.get("line_2") or (summary_lines[1] if len(summary_lines) > 1 else article.get("source", "")),
        max_chars=110,
    )
    caption_title = _clean_line(caption.get("title") or article.get("title", ""), max_chars=90)
    caption_body = _normalize_lines(caption.get("body", []), min_items=2, max_items=4, max_chars=170) or summary_lines[:4]

    return {
        "image_text": {
            "hook": hook,
            "line_1": line_1,
            "line_2": line_2,
        },
        "caption": {
            "title": caption_title,
            "body": caption_body[:4],
            "link": article.get("link", ""),
        },
    }


def _normalize_story_copy_payload(payload: dict | None, article: dict, reader_output: dict) -> dict | None:
    if not isinstance(payload, dict):
        return None

    article = _normalize_article(article)
    summary_lines = _normalize_lines(
        payload.get("article_summary", []) or reader_output.get("article_summary", []),
        min_items=2,
        max_items=3,
        max_chars=170,
    )
    if not summary_lines:
        summary_lines = _normalize_lines(reader_output.get("article_summary", []), min_items=2, max_items=3, max_chars=170)
    if not summary_lines:
        return None

    x_payload = payload.get("x", {}) if isinstance(payload.get("x"), dict) else {}
    youtube_payload = payload.get("youtube", {}) if isinstance(payload.get("youtube"), dict) else {}
    reddit_payload = payload.get("reddit", {}) if isinstance(payload.get("reddit"), dict) else {}
    discord_payload = payload.get("discord", {}) if isinstance(payload.get("discord"), dict) else {}
    email_payload = payload.get("email", {}) if isinstance(payload.get("email"), dict) else {}

    x_post = _normalize_lines(x_payload.get("post", []), min_items=2, max_items=3, max_chars=180)
    if article.get("link") and article.get("link") not in x_post:
        x_post = [*x_post[:2], article.get("link", "")]

    youtube_description = _normalize_lines(youtube_payload.get("description", []), min_items=2, max_items=3, max_chars=180) or summary_lines[:3]
    youtube_voice = _normalize_lines(youtube_payload.get("voice_script", []), min_items=2, max_items=3, max_chars=180) or summary_lines[:3]
    reddit_body = _normalize_lines(reddit_payload.get("body", []), min_items=2, max_items=3, max_chars=220) or summary_lines[:3]
    discord_post = _normalize_lines(discord_payload.get("post", []), min_items=2, max_items=3, max_chars=180)
    if article.get("link") and article.get("link") not in discord_post:
        discord_post = [*discord_post[:2], article.get("link", "")]
    email_body = _normalize_lines(email_payload.get("body", []), min_items=2, max_items=3, max_chars=180) or summary_lines[:3]

    instagram = _normalize_instagram_payload(payload.get("instagram", {}), article, summary_lines)

    return {
        "title": _clean_line(payload.get("title") or article.get("title", ""), max_chars=120),
        "url": article.get("link", ""),
        "source": article.get("source", ""),
        "category": article.get("category", ""),
        "score": article.get("score", 0),
        "article_summary": summary_lines,
        "instagram": instagram,
        "x": {"post": x_post[:3]},
        "youtube": {
            "title": _clean_line(youtube_payload.get("title") or article.get("title", ""), max_chars=100),
            "hook": _clean_line(youtube_payload.get("hook") or summary_lines[0], max_chars=90),
            "description": youtube_description[:3],
            "voice_script": youtube_voice[:3],
        },
        "reddit": {
            "title": _clean_line(reddit_payload.get("title") or article.get("title", ""), max_chars=120),
            "body": reddit_body[:3],
        },
        "discord": {"post": discord_post[:3]},
        "email": {
            "subject": _clean_line(email_payload.get("subject") or article.get("title", ""), max_chars=120),
            "body": email_body[:3],
            "link": article.get("link", ""),
        },
    }


def _build_story_platform_fallback(article: dict, reader_output: dict | None = None, *, reason: str = "cannot_access_article") -> dict:
    article = _normalize_article(article)
    reader_output = reader_output or {
        "status": "cannot_access_article",
        "url": article.get("link", ""),
        "title": article.get("title", ""),
    }
    summary_lines = (
        _normalize_lines(reader_output.get("article_summary", []), max_items=3, max_chars=170)
        if reader_output.get("status") == "ok"
        else _metadata_summary_lines(article)
    )
    if not summary_lines:
        summary_lines = [_clean_line(article.get("title", "Sem título"), max_chars=170)]

    base = {
        "title": article.get("title", ""),
        "url": article.get("link", ""),
        "source": article.get("source", ""),
        "category": article.get("category", ""),
        "score": article.get("score", 0),
        "article_summary": summary_lines[:3],
        "instagram": {
            "image_text": {
                "hook": _clean_line(article.get("title", ""), max_chars=90),
                "line_1": _clean_line(summary_lines[0] if summary_lines else "", max_chars=110),
                "line_2": _clean_line(summary_lines[1] if len(summary_lines) > 1 else article.get("source", ""), max_chars=110),
            },
            "caption": {
                "title": _clean_line(article.get("title", ""), max_chars=90),
                "body": summary_lines[:4],
                "link": article.get("link", ""),
            },
        },
        "x": {
            "post": _normalize_lines(
                [article.get("title", ""), summary_lines[0] if summary_lines else "", article.get("link", "")],
                min_items=2,
                max_items=3,
                max_chars=180,
            )[:3],
        },
        "youtube": {
            "title": _clean_line(article.get("title", ""), max_chars=100),
            "hook": _clean_line(summary_lines[0] if summary_lines else article.get("title", ""), max_chars=90),
            "description": summary_lines[:3],
            "voice_script": summary_lines[:3],
        },
        "reddit": {
            "title": _clean_line(article.get("title", ""), max_chars=120),
            "body": summary_lines[:3],
        },
        "discord": {
            "post": _normalize_lines(
                [article.get("title", ""), summary_lines[0] if summary_lines else "", article.get("link", "")],
                min_items=2,
                max_items=3,
                max_chars=180,
            )[:3],
        },
        "email": {
            "subject": _clean_line(article.get("title", ""), max_chars=120),
            "body": summary_lines[:3],
            "link": article.get("link", ""),
        },
    }
    base["status"] = "fallback"
    base["reader_status"] = reader_output.get("status", "cannot_access_article")
    base["copy_status"] = reason
    base["summary_source"] = "article_reader" if reader_output.get("status") == "ok" else "metadata_fallback"
    return base


def _build_legacy_instagram_pack(story_output: dict) -> dict:
    instagram = story_output.get("instagram", {}) if isinstance(story_output, dict) else {}
    image_text = instagram.get("image_text", {}) if isinstance(instagram.get("image_text"), dict) else {}
    caption = instagram.get("caption", {}) if isinstance(instagram.get("caption"), dict) else {}
    caption_body = _normalize_lines(caption.get("body", []), max_items=4, max_chars=180)
    caption_parts = [caption.get("title", ""), *caption_body]
    if caption.get("link"):
        caption_parts.append(caption.get("link", ""))
    slides = [image_text.get("line_1", ""), image_text.get("line_2", "")]
    slides = [line for line in slides if _clean_line(line, max_chars=120)]
    return {
        "format": "story_platform_workspace",
        "cover_hook": _clean_line(image_text.get("hook", ""), max_chars=90),
        "slides": slides,
        "caption": "\n".join(part for part in caption_parts if part).strip(),
        "community_question": "",
        "cta_style": "implicit",
        "notes_for_design": "Per-story output generated from article_reader + platform_copywriter.",
    }


def _compose_story_platform_post(story_output: dict) -> str:
    story_output = story_output or {}
    instagram = story_output.get("instagram", {}) if isinstance(story_output.get("instagram"), dict) else {}
    image_text = instagram.get("image_text", {}) if isinstance(instagram.get("image_text"), dict) else {}
    caption = instagram.get("caption", {}) if isinstance(instagram.get("caption"), dict) else {}
    lines = ["Resumo do artigo:"]
    for item in story_output.get("article_summary", [])[:3]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "Instagram image text:",
        image_text.get("hook", ""),
        image_text.get("line_1", ""),
        image_text.get("line_2", ""),
        "",
        "Instagram caption:",
        caption.get("title", ""),
        *caption.get("body", []),
    ])
    if caption.get("link"):
        lines.append(caption.get("link", ""))
    return "\n".join(line for line in lines if line).strip()


def _legacy_analysis_payload(story_output: dict, reader_output: dict) -> str:
    payload = {
        "why_it_matters": reader_output.get("angle", ""),
        "headline_hook": (
            story_output.get("instagram", {})
            .get("image_text", {})
            .get("hook", "")
        ),
        "community_question": "",
        "tone_hint": reader_output.get("tone_hint", "factual"),
        "article_summary": story_output.get("article_summary", []),
        "reader_status": reader_output.get("status", "cannot_access_article"),
        "copy_status": story_output.get("copy_status", ""),
    }
    return json.dumps(payload, ensure_ascii=False)


def _copywriter_output_payload(story_output: dict) -> dict:
    story_output = story_output or {}
    return {
        "title": story_output.get("title", ""),
        "url": story_output.get("url", ""),
        "source": story_output.get("source", ""),
        "category": story_output.get("category", ""),
        "score": story_output.get("score", 0),
        "article_summary": list(story_output.get("article_summary", []) or []),
        "instagram": dict(story_output.get("instagram", {}) or {}),
        "x": dict(story_output.get("x", {}) or {}),
        "youtube": dict(story_output.get("youtube", {}) or {}),
        "reddit": dict(story_output.get("reddit", {}) or {}),
        "discord": dict(story_output.get("discord", {}) or {}),
        "email": dict(story_output.get("email", {}) or {}),
    }


def run_agent(agent_name: str, user_input: str, context: str = "", metrics: dict | None = None) -> str:
    started_at = perf_counter()
    if metrics is not None:
        metrics["calls_attempted"] = metrics.get("calls_attempted", 0) + 1
    logger.info("Agent start: %s", agent_name)

    # Proteção: key não configurada → não faz chamada, não rebenta dry-run
    if not MINIMAX_API_KEY or "COLOCA_AQUI" in MINIMAX_API_KEY or client is None:
        duration = perf_counter() - started_at
        _record_duration(metrics, agent_name, duration)
        if metrics is not None:
            metrics["calls_skipped"] = metrics.get("calls_skipped", 0) + 1
        logger.warning("Agent skipped: %s — MiniMax API key não configurada", agent_name)
        return ""

    messages = []
    if context:
        messages.append({"role": "user", "content": f"Contexto:\n{context}"})
        messages.append({"role": "assistant", "content": "Entendido."})
    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": AGENT_PROMPTS[agent_name]},
                *messages
            ],
            max_tokens=1500,
            temperature=0.75,
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        cleaned = _clean_output(response.choices[0].message.content or "")
        duration = perf_counter() - started_at
        _record_duration(metrics, agent_name, duration)
        if metrics is not None:
            metrics["calls_succeeded"] = metrics.get("calls_succeeded", 0) + 1
        logger.info("Agent done: %s in %.2fs (%d chars)", agent_name, duration, len(cleaned))
        return cleaned
    except Exception as e:
        duration = perf_counter() - started_at
        _record_duration(metrics, agent_name, duration)
        if metrics is not None:
            if _is_timeout_error(e):
                metrics["calls_timed_out"] = metrics.get("calls_timed_out", 0) + 1
            else:
                metrics["calls_failed"] = metrics.get("calls_failed", 0) + 1
        if _is_timeout_error(e):
            logger.warning(
                "Agent timeout: %s after %.2fs (budget %.1fs): %s",
                agent_name, duration, AGENT_TIMEOUT_SECONDS, e,
            )
        else:
            logger.warning("Agent fail: %s after %.2fs: %s", agent_name, duration, e)
        return ""


def run_story_platform_pipeline(article: dict) -> dict:
    """Two-agent per-story workflow: article reader first, platform copy second."""
    normalized_article = _normalize_article(article)
    pipeline_started_at = perf_counter()
    metrics = _new_agent_metrics("story_platform")
    logger.info("Story platform pipeline: '%s'", normalized_article.get("title", "")[:60])

    fetched = _fetch_article_payload(normalized_article)
    if fetched.get("status") != "ok":
        result = _build_story_platform_fallback(
            normalized_article,
            {
                "status": "cannot_access_article",
                "url": normalized_article.get("link", ""),
                "title": normalized_article.get("title", ""),
            },
            reason="metadata_fallback",
        )
        result.update({
            "article": normalized_article,
            "reader_output": {
                "status": "cannot_access_article",
                "url": normalized_article.get("link", ""),
                "title": normalized_article.get("title", ""),
            },
            "copywriter_output": {},
            "analysis": _legacy_analysis_payload(result, {
                "status": "cannot_access_article",
                "angle": "",
                "tone_hint": "factual",
            }),
            "post": _compose_story_platform_post(result),
            "instagram_pack": _build_legacy_instagram_pack(result),
            "image_prompt": "",
            "voice_script": "\n".join(result.get("youtube", {}).get("voice_script", [])).strip(),
            "qa": "",
            "raw_post": "",
            "agent_metrics": metrics,
        })
        metrics["total_duration_sec"] = round(perf_counter() - pipeline_started_at, 3)
        metrics["useful_output"] = bool(result.get("post"))
        return result

    reader_input = _build_article_reader_input(normalized_article, fetched.get("text", ""))
    reader_raw = run_agent("article_reader", reader_input, metrics=metrics)
    reader_data = _normalize_reader_output(
        _parse_agent_json(reader_raw, "article_reader", metrics),
        normalized_article,
    )
    if reader_data.get("status") != "ok":
        result = _build_story_platform_fallback(normalized_article, reader_data, reason="metadata_fallback")
        result.update({
            "article": normalized_article,
            "reader_output": reader_data,
            "copywriter_output": {},
            "analysis": _legacy_analysis_payload(result, reader_data),
            "post": _compose_story_platform_post(result),
            "instagram_pack": _build_legacy_instagram_pack(result),
            "image_prompt": "",
            "voice_script": "\n".join(result.get("youtube", {}).get("voice_script", [])).strip(),
            "qa": "",
            "raw_post": "",
            "agent_metrics": metrics,
        })
        metrics["total_duration_sec"] = round(perf_counter() - pipeline_started_at, 3)
        metrics["useful_output"] = bool(result.get("post"))
        return result

    copy_raw = run_agent(
        "platform_copywriter",
        _build_platform_copywriter_input(normalized_article, reader_data),
        context=json.dumps(reader_data, ensure_ascii=False, indent=2),
        metrics=metrics,
    )
    structured_story = _normalize_story_copy_payload(
        _parse_agent_json(copy_raw, "platform_copywriter", metrics),
        normalized_article,
        reader_data,
    )
    copywriter_succeeded = structured_story is not None
    if structured_story is None:
        structured_story = _build_story_platform_fallback(
            normalized_article,
            reader_data,
            reason="copywriter_fallback",
        )
    else:
        structured_story["status"] = "ok"
        structured_story["reader_status"] = "ok"
        structured_story["copy_status"] = "ok"
        structured_story["summary_source"] = "article_reader"

    copywriter_output = _copywriter_output_payload(structured_story) if copywriter_succeeded else {}
    structured_story.update({
        "article": normalized_article,
        "reader_output": reader_data,
        "copywriter_output": copywriter_output,
        "analysis": _legacy_analysis_payload(structured_story, reader_data),
        "post": _compose_story_platform_post(structured_story),
        "instagram_pack": _build_legacy_instagram_pack(structured_story),
        "image_prompt": "",
        "voice_script": "\n".join(structured_story.get("youtube", {}).get("voice_script", [])).strip(),
        "qa": "",
        "raw_post": copy_raw,
        "agent_metrics": metrics,
    })
    metrics["total_duration_sec"] = round(perf_counter() - pipeline_started_at, 3)
    metrics["useful_output"] = bool(any([
        structured_story.get("post"),
        structured_story.get("instagram_pack"),
        structured_story.get("voice_script"),
    ]))
    return structured_story


def run_full_pipeline(article: dict) -> dict:
    """Backward-compatible wrapper for the current per-story agent entrypoint."""
    return run_story_platform_pipeline(article)


def run_instagram_digest_pipeline(digest_articles: list, digest_type: str) -> dict:
    """Corre pipeline dedicado para digest editorial de Instagram."""
    digest_articles = digest_articles or []
    if not digest_articles:
        return {
            "digest_type": digest_type,
            "articles": [],
            "analysis": "",
            "post": "",
            "instagram_pack": {},
            "image_prompt": "",
            "voice_script": "",
            "qa": "",
            "raw_post": "",
            "agent_metrics": _new_agent_metrics("instagram_digest"),
        }

    pipeline_started_at = perf_counter()
    metrics = _new_agent_metrics("instagram_digest")
    summary = _build_digest_summary(digest_articles, digest_type)
    logger.info(f"Instagram digest pipeline: {digest_type} ({len(digest_articles)} stories)")

    analysis = run_agent("instagram_digest_analyst", summary, metrics=metrics)
    raw_post = run_agent("instagram_digest_copywriter", summary, analysis, metrics=metrics)

    instagram_pack = {}
    post = raw_post
    parsed_pack = _parse_agent_json(raw_post, "instagram_digest_copywriter", metrics)
    if parsed_pack:
        instagram_pack = parsed_pack
        composed_post = _compose_instagram_digest_post(instagram_pack)
        if composed_post:
            post = composed_post
    elif raw_post:
        logger.info("Instagram digest copywriter fallback para texto bruto")

    img_prompt = run_agent("image_director", post, analysis, metrics=metrics)
    voice = run_agent("voice_director", post, metrics=metrics)
    qa_result = run_agent("instagram_digest_qa", post, metrics=metrics)

    final_post = post
    qa_data = _parse_agent_json(qa_result, "instagram_digest_qa", metrics)
    if qa_data and not qa_data.get("approved") and qa_data.get("improved_post"):
        improved_post = str(qa_data.get("improved_post") or "")
        improved_pack = _parse_agent_json(improved_post, "instagram_digest_qa.improved_post", metrics)
        if improved_pack:
            instagram_pack = improved_pack
            final_post = _compose_instagram_digest_post(improved_pack) or improved_post
            logger.info("Instagram digest QA rejeitou → usando improved_post estruturado")
        else:
            final_post = improved_post
            logger.info("Instagram digest QA rejeitou → usando improved_post em texto")

    metrics["total_duration_sec"] = round(perf_counter() - pipeline_started_at, 3)
    metrics["useful_output"] = bool(any([final_post, instagram_pack, img_prompt, voice]))

    return {
        "digest_type": digest_type,
        "articles": digest_articles,
        "analysis": analysis,
        "post": final_post,
        "instagram_pack": instagram_pack,
        "image_prompt": img_prompt,
        "voice_script": voice,
        "qa": qa_result,
        "raw_post": raw_post,
        "agent_metrics": metrics,
    }
