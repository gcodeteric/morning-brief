"""
SimulaNewsMachine — Pipeline de agentes MiniMax M2.7
Cadeia: Analyst → Copywriter → ImageDir → VoiceDir → QA
Sistema híbrido: corre em paralelo com o formatter existente.
"""

import json
import logging
import os
from time import perf_counter
from openai import OpenAI

logger = logging.getLogger(__name__)

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "").strip()
MINIMAX_BASE_URL = "https://api.minimax.io/v1"
MODEL = "MiniMax-M2.7"
AGENT_TIMEOUT_SECONDS = float(os.environ.get("MINIMAX_TIMEOUT_SECONDS", "45"))

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


def run_full_pipeline(article: dict) -> dict:
    """Corre os 5 agentes em cadeia. Retorna dict com todos os outputs."""
    pipeline_started_at = perf_counter()
    metrics = _new_agent_metrics("single_article")
    summary = (
        f"Título: {article.get('title','')}\n"
        f"Fonte: {article.get('source','')}\n"
        f"Resumo: {(article.get('summary') or '')[:600]}\n"
        f"Score editorial: {article.get('score', 0)}/100\n"
        f"Link: {article.get('link','')}"
    )
    logger.info(f"Pipeline: '{article.get('title','')[:50]}'")

    analysis = run_agent("analyst", summary, metrics=metrics)
    raw_post = run_agent("copywriter", summary, analysis, metrics=metrics)

    instagram_pack = {}
    post = raw_post
    parsed_pack = _parse_agent_json(raw_post, "copywriter", metrics)
    if parsed_pack:
        instagram_pack = parsed_pack
        composed_post = _compose_instagram_post(instagram_pack)
        if composed_post:
            post = composed_post
    elif raw_post:
        logger.info("Copywriter fallback para texto bruto no pipeline single-article")

    img_prompt = run_agent("image_director", post, analysis, metrics=metrics)
    voice = run_agent("voice_director", post, metrics=metrics)
    qa_result = run_agent("qa", post, metrics=metrics)

    final_post = post
    qa_data = _parse_agent_json(qa_result, "qa", metrics)
    if qa_data and not qa_data.get("approved") and qa_data.get("improved_post"):
        improved_post = str(qa_data.get("improved_post") or "")
        improved_pack = _parse_agent_json(improved_post, "qa.improved_post", metrics)
        if improved_pack:
            instagram_pack = improved_pack
            final_post = _compose_instagram_post(improved_pack) or improved_post
            logger.info("QA rejeitou → usando improved_post estruturado")
        else:
            final_post = improved_post
            logger.info("QA rejeitou → usando improved_post em texto")

    metrics["total_duration_sec"] = round(perf_counter() - pipeline_started_at, 3)
    metrics["useful_output"] = bool(any([final_post, instagram_pack, img_prompt, voice]))

    return {
        "article": article,
        "analysis": analysis,
        "post": final_post,
        "instagram_pack": instagram_pack,
        "image_prompt": img_prompt,
        "voice_script": voice,
        "qa": qa_result,
        "raw_post": raw_post,
        "agent_metrics": metrics,
    }


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
