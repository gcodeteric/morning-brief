"""
SimulaNewsMachine — Pipeline de agentes MiniMax M2.7
Cadeia: Analyst → Copywriter → ImageDir → VoiceDir → QA
Sistema híbrido: corre em paralelo com o formatter existente.
"""

import json
import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "").strip()
MINIMAX_BASE_URL = "https://api.minimax.io/v1"
MODEL = "MiniMax-M2.7"

client = OpenAI(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL) if MINIMAX_API_KEY else None

AGENT_PROMPTS = {

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


def run_agent(agent_name: str, user_input: str, context: str = "") -> str:
    # Proteção: key não configurada → não faz chamada, não rebenta dry-run
    if not MINIMAX_API_KEY or "COLOCA_AQUI" in MINIMAX_API_KEY or client is None:
        logger.warning("MiniMax API key não configurada — agente ignorado")
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
            temperature=0.75
        )
        return _clean_output(response.choices[0].message.content or "")
    except Exception as e:
        logger.warning(f"Agente {agent_name} falhou: {e}")
        return ""


def run_full_pipeline(article: dict) -> dict:
    """Corre os 5 agentes em cadeia. Retorna dict com todos os outputs."""
    summary = (
        f"Título: {article.get('title','')}\n"
        f"Fonte: {article.get('source','')}\n"
        f"Resumo: {(article.get('summary') or '')[:600]}\n"
        f"Score editorial: {article.get('score', 0)}/100\n"
        f"Link: {article.get('link','')}"
    )
    logger.info(f"Pipeline: '{article.get('title','')[:50]}'")

    analysis = run_agent("analyst", summary)
    raw_post = run_agent("copywriter", summary, analysis)

    instagram_pack = {}
    post = raw_post
    try:
        parsed_pack = json.loads(raw_post)
        if isinstance(parsed_pack, dict):
            instagram_pack = parsed_pack
            composed_post = _compose_instagram_post(instagram_pack)
            if composed_post:
                post = composed_post
    except Exception:
        pass

    img_prompt = run_agent("image_director", post, analysis)
    voice = run_agent("voice_director", post)
    qa_result = run_agent("qa", post)

    final_post = post
    try:
        qa_data = json.loads(qa_result)
        if not qa_data.get("approved") and qa_data.get("improved_post"):
            final_post = qa_data["improved_post"]
            logger.info("QA rejeitou → usando improved_post")
    except Exception:
        pass

    return {
        "article": article,
        "analysis": analysis,
        "post": final_post,
        "instagram_pack": instagram_pack,
        "image_prompt": img_prompt,
        "voice_script": voice,
        "qa": qa_result,
        "raw_post": raw_post,
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
        }

    summary = _build_digest_summary(digest_articles, digest_type)
    logger.info(f"Instagram digest pipeline: {digest_type} ({len(digest_articles)} stories)")

    analysis = run_agent("instagram_digest_analyst", summary)
    raw_post = run_agent("instagram_digest_copywriter", summary, analysis)

    instagram_pack = {}
    post = raw_post
    try:
        parsed_pack = json.loads(raw_post)
        if isinstance(parsed_pack, dict):
            instagram_pack = parsed_pack
            composed_post = _compose_instagram_digest_post(instagram_pack)
            if composed_post:
                post = composed_post
    except Exception:
        pass

    img_prompt = run_agent("image_director", post, analysis)
    voice = run_agent("voice_director", post)
    qa_result = run_agent("instagram_digest_qa", post)

    final_post = post
    try:
        qa_data = json.loads(qa_result)
        if not qa_data.get("approved") and qa_data.get("improved_post"):
            final_post = qa_data["improved_post"]
            logger.info("Instagram digest QA rejeitou → usando improved_post")
    except Exception:
        pass

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
    }
