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
  "avoid": "o que NÃO dizer neste post"
}
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
• Estrutura: Hook → Contexto → Twist → Fechamento (4 parágrafos máx)
• 1 emoji por parágrafo máx, CTA implícito nunca forçado
• PROIBIDO: "revolucionário" "incrível" "fantástico" "não percas" "imperdível"
• Evita o que o Analyst indicou em "avoid"

OUTPUT: post completo PT-PT sem hashtags (vêm do QA).
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
    "hook": 0-10,
    "depth": 0-10,
    "brand_voice": 0-10,
    "legal_clear": 0-10,
    "cta_quality": 0-10
  },
  "average": float,
  "approved": true/false,
  "hashtags": ["15 hashtags mix PT+EN específicas"],
  "issues": ["problemas — lista vazia se aprovado"],
  "improved_hook": "reescrito APENAS se hook < 7, senão null",
  "improved_post": "reescrito APENAS se average < 7.0, senão null"
}
THRESHOLD: approved = true APENAS se average >= 7.0
"""
}


def _clean_output(text: str) -> str:
    """Remove blocos <think> de modelos de raciocínio como MiniMax M2.7."""
    import re
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return text.strip()


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
    post = run_agent("copywriter", summary, analysis)
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
        "image_prompt": img_prompt,
        "voice_script": voice,
        "qa": qa_result,
        "raw_post": post,
    }
