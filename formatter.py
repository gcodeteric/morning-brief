"""
SimulaNewsMachine — Formatação do brief diário + 6 prompts para redes sociais.

Gera ficheiro .md completo no Desktop.
"""

import json
import logging
from datetime import datetime

DAY_CONTEXT = {
    0: "É segunda-feira — menciona brevemente o que aconteceu no fim-de-semana.",
    4: "É sexta-feira — podes antecipar o que vem aí este fim-de-semana.",
    5: "É sábado — foca no que está a acontecer hoje em pista ou online.",
    6: "É domingo — tom mais calmo, foco no resumo da semana.",
}
# Restantes dias: sem contexto extra

logger = logging.getLogger(__name__)

# Mapeamento de categoria -> emoji
CATEGORY_EMOJI = {
    "sim_racing": "🏎️",
    "motorsport": "🏁",
    "hardware": "🎮",
    "nostalgia": "🕹️",
    "racing_games": "🎲",
    "esports": "🏆",
    "community": "👥",
    "deals": "💰",
    "portugal": "🇵🇹",
}

DIAS_SEMANA = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sábado",
    6: "Domingo",
}

# FIX 3.1 — Regra editorial obrigatória para todos os prompts
REGRA_NAO_PUBLICAR = """
REGRA EDITORIAL OBRIGATÓRIA:
Se alguma das notícias for fraca, redundante, excessivamente promocional ou sem substância suficiente para gerar conteúdo de qualidade, responde:
"NÃO PUBLICAR — [motivo]"
É melhor não publicar do que publicar conteúdo fraco. A reputação do Simula Project depende da qualidade, não da quantidade."""

# FIX 3.2 — Notas legais PT/UE para prompts de redes sociais
NOTAS_LEGAIS_SOCIAL = """
REGRAS LEGAIS OBRIGATÓRIAS (Portugal/UE):
- Se mencionares produto cedido para review: incluir #OFERTA no início da legenda/post
- Se incluíres link de afiliado: indicar "link de afiliado — posso ganhar comissão"
- NUNCA inventar claims de performance de hardware não verificados
- Cumprir Código da Publicidade Português (DL 330/90) + RGPD"""

NOTA_IA_YOUTUBE = '"Este vídeo utiliza narração gerada por inteligência artificial (IA). O conteúdo informativo foi verificado pela equipa Simula Project."'


def _format_article_highlight(article, index):
    """Formata artigo como destaque (posicao 1-5)."""
    category = article.get("category", "unknown")
    emoji = CATEGORY_EMOJI.get(category, "📰")
    title = article.get("title") or "Sem título"
    source = article.get("source") or "Fonte desconhecida"
    summary = (article.get("summary") or "")[:200]
    link = article.get("link", "")
    score = article.get("score", 0)

    lines = [
        f"### {index}. {emoji} **{title}**",
        f"📡 {source} | Score: {score}",
        "",
    ]
    if summary:
        lines.append(f"> {summary}")
        lines.append("")
    lines.append(f"🔗 {link}")
    lines.append("")
    return "\n".join(lines)


def _format_article_compact(article, index):
    """Formata artigo compacto (posicao 6-15)."""
    category = article.get("category", "unknown")
    emoji = CATEGORY_EMOJI.get(category, "📰")
    title = article.get("title") or "Sem título"
    source = article.get("source") or "Fonte desconhecida"
    link = article.get("link", "")
    return f"{index}. {emoji} **{title}** — {source} | [Link]({link})"


def _generate_news_block(selected):
    """Gera bloco de texto com as 15 noticias para injectar nos prompts."""
    lines = []
    for i, a in enumerate(selected, 1):
        category = str(a.get("category") or "unknown").upper()
        title = a.get("title") or "Sem título"
        source = a.get("source") or "Fonte desconhecida"
        summary = a.get("summary") or ""
        link = a.get("link", "")
        lines.append(f"{i}. [{category}] {title} — {source}")
        if summary:
            lines.append(f"   Resumo: {summary[:400]}")
        lines.append(f"   Link: {link}")
        lines.append("")
    return "\n".join(lines)


def _format_channel_options(channel_name, primary, alternatives):
    primary = primary or {}
    alternatives = alternatives or []

    def _format_option(label, article):
        if not article:
            return [
                f"{label}:",
                "Sem artigo disponível.",
                "",
            ]
        return [
            f"{label}:",
            f"- Título: {article.get('title', 'Sem título')}",
            f"- Fonte: {article.get('source', 'Fonte desconhecida')}",
            f"- Categoria: {article.get('category', 'unknown')}",
            f"- Score: {article.get('score', 0)}",
            f"- Link: {article.get('link', '')}",
            "",
        ]

    lines = [f"## {channel_name}", ""]
    lines.extend(_format_option("Principal", primary))

    if alternatives:
        for i, article in enumerate(alternatives[:2], 1):
            lines.extend(_format_option(f"Alternativa {i}", article))
    else:
        lines.append("Sem alternativa disponível.")
        lines.append("")

    return "\n".join(lines)


def _enrich_article(article: dict) -> dict:
    """Expande o artigo com campos calculados para prompts mais ricos."""
    summary = article.get("summary") or ""
    title   = article.get("title") or ""
    source  = article.get("source") or ""
    score   = article.get("score", 0)
    category = article.get("category", "unknown")

    # Detecta tipo de conteúdo para guiar o tom
    is_product_news = any(w in title.lower() for w in [
        "launch", "release", "new", "announce", "novo", "lançamento", "review"
    ])
    is_event_news = any(w in title.lower() for w in [
        "race", "championship", "winner", "round", "corrida", "campeonato"
    ])
    is_opinion = any(w in source.lower() for w in [
        "reddit", "forum", "community", "r/"
    ])

    content_type = (
        "LANÇAMENTO/PRODUTO" if is_product_news else
        "EVENTO/COMPETIÇÃO"  if is_event_news   else
        "COMUNIDADE/OPINIÃO" if is_opinion       else
        "NOTÍCIA GERAL"
    )

    # Expande summary — usa os primeiros 600 chars se disponível
    full_summary = (article.get("summary") or "")[:600]

    return {
        **article,
        "full_summary":  full_summary,
        "content_type":  content_type,
        "is_high_score": score >= 80,
        "word_count_est": len(full_summary.split()),
    }


def format_brief(curated, output_path, plan=None, card_paths=None):
    """Gera o ficheiro .md completo com brief + 6 prompts."""
    selected = curated["selected"]
    categories = curated["categories"]
    total_before = curated["total_before_dedup"]
    total_after = curated["total_after_dedup"]

    now = datetime.now()
    dia_semana = DIAS_SEMANA.get(now.weekday(), "")
    data_str = now.strftime("%d/%m/%Y")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    news_block = _generate_news_block(selected)
    if plan is None:
        # Fallback genérico de compatibilidade: mantém o brief funcional
        # mesmo sem planner. Não representa seleção editorial real por canal.
        plan = {
            "instagram_sim_racing": selected[0] if selected else None,
            "instagram_motorsport": selected[1] if len(selected) > 1 else None,
            "x_thread_1": selected[0] if selected else None,
            "x_thread_2": selected[1] if len(selected) > 1 else None,
            "youtube_daily": selected[0] if selected else None,
            "youtube_weekly": selected[:5],
            "reddit_candidates": selected[:3],
            "discord_post": selected[0] if selected else None,
            "is_sunday": datetime.now().weekday() == 6,
        }
    if card_paths is None:
        card_paths = {}

    # ========================================================================
    # CONSTRUIR O MARKDOWN
    # ========================================================================
    md = []

    # --- HEADER --- (FIX 3.3: "artigos recolhidos" em vez de "fontes analisadas")
    md.append(f"# SIMULA BRIEF — {dia_semana}, {data_str}")
    md.append("")
    md.append(f"**{total_before}** artigos recolhidos | **{total_after}** únicos hoje | **{len(selected)}** selecionados")
    md.append("")
    md.append("---")
    md.append("")

    # --- DESTAQUES (1-5) ---
    md.append("## 🔥 DESTAQUES")
    md.append("")
    highlights = selected[:5]
    for i, article in enumerate(highlights, 1):
        md.append(_format_article_highlight(article, i))

    # --- RESTANTES (6-15) ---
    if len(selected) > 5:
        md.append("---")
        md.append("")
        md.append("## 📋 RESTANTES")
        md.append("")
        for i, article in enumerate(selected[5:], 6):
            md.append(_format_article_compact(article, i))
        md.append("")

    # --- DISTRIBUIÇÃO ---
    md.append("---")
    md.append("")
    md.append("## 📊 DISTRIBUIÇÃO POR CATEGORIA")
    md.append("")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        emoji = CATEGORY_EMOJI.get(cat, "📰")
        md.append(f"- {emoji} **{cat}**: {count}")
    md.append("")

    # --- ESCOLHAS DO PLANNER E ALTERNATIVAS ---
    md.append("---")
    md.append("")
    md.append("# 🎛️ ESCOLHAS DO PLANNER E ALTERNATIVAS")
    md.append("")
    md.append(_format_channel_options(
        "Instagram — Sim Racing",
        plan.get("instagram_sim_racing"),
        plan.get("instagram_sim_racing_alternatives", []),
    ))
    md.append(_format_channel_options(
        "Instagram — Motorsport",
        plan.get("instagram_motorsport"),
        plan.get("instagram_motorsport_alternatives", []),
    ))
    md.append(_format_channel_options(
        "X/Twitter — Thread 1",
        plan.get("x_thread_1"),
        plan.get("x_thread_1_alternatives", []),
    ))
    md.append(_format_channel_options(
        "X/Twitter — Thread 2",
        plan.get("x_thread_2"),
        plan.get("x_thread_2_alternatives", []),
    ))
    md.append(_format_channel_options(
        "YouTube — Daily",
        plan.get("youtube_daily"),
        plan.get("youtube_daily_alternatives", []),
    ))
    md.append(_format_channel_options(
        "Discord",
        plan.get("discord_post"),
        plan.get("discord_post_alternatives", []),
    ))

    if plan.get("manual_overrides_applied"):
        md.append("## Overrides manuais aplicados")
        for channel, alt_idx in (plan.get("override_summary") or {}).items():
            md.append(f"- {channel} → alternativa {alt_idx}")
        md.append("")

    md.append("## Recomendação editorial Instagram")
    md.append("- Ritmo recomendado nesta fase: 1 post a cada 2 dias")
    md.append("- Prioridade: qualidade > frequência")
    md.append("- Só subir para diário quando houver consistência editorial e visual durante várias semanas")
    md.append("")

    # ====================================================================
    # SECÇÃO 2: PROMPTS EDITORIAIS v3
    # ====================================================================
    ig_sim      = plan.get("instagram_sim_racing")
    ig_moto     = plan.get("instagram_motorsport")
    x1          = plan.get("x_thread_1")
    x2          = plan.get("x_thread_2")
    yt          = plan.get("youtube_daily")
    reddit_arts = plan.get("reddit_candidates", [])
    discord_art = plan.get("discord_post")
    is_sunday   = plan.get("is_sunday", False)
    ig_sim_e    = _enrich_article(ig_sim)      if ig_sim      else {}
    ig_moto_e   = _enrich_article(ig_moto)     if ig_moto     else {}
    x1_e        = _enrich_article(x1)          if x1          else {}
    x2_e        = _enrich_article(x2)          if x2          else {}
    yt_e        = _enrich_article(yt)          if yt          else {}
    discord_e   = _enrich_article(discord_art) if discord_art else {}

    card_sim_path  = card_paths.get("sim_racing",  "Desktop/SIMULA_CARDS_HOJE/card_01_sim_racing.png")
    card_moto_path = card_paths.get("motorsport",  "Desktop/SIMULA_CARDS_HOJE/card_02_motorsport.png")

    day_context = DAY_CONTEXT.get(now.weekday(), "")
    ig_manha = "Carrossel" if now.weekday() % 2 == 0 else "Reel"
    ig_tarde = "Reel"      if now.weekday() % 2 == 0 else "Carrossel"

    reddit_block = _generate_news_block(reddit_arts) if reddit_arts else "Sem artigos elegíveis hoje."

    md.append("---")
    md.append("")
    md.append("# 🚀 PROMPTS PARA REDES SOCIAIS")
    md.append("")
    md.append("*Copia cada prompt e cola directamente no Claude Sonnet.*")
    md.append("")

    # ── PROMPT 1: INSTAGRAM ──────────────────────────────────────────────
    md.append("---")
    md.append("")
    md.append("## PROMPT 1 — INSTAGRAM (2 posts com imagem)")
    md.append("")
    md.append("````")
    md.append(f"""És o social media manager do Simula Project — o primeiro operador integrado de sim racing em Portugal.
Tom: inteligente, humor subtil, educativo. PT-PT. NUNCA vendas directamente.

CONTEXTO DA MARCA:
- Simula Project: hub de sim racing, motorsport, hardware, racing games e simuladores nostálgicos
- Idioma: PT-PT (português de Portugal)
- Imagens branded já geradas em:
  POST 1: {card_sim_path}
  POST 2: {card_moto_path}

POST 1 — SIM RACING (publicar 09:00):
Tipo: {ig_sim_e.get('content_type', 'N/A')}
Notícia: {ig_sim_e.get('title', 'N/A')}
Fonte: {ig_sim_e.get('source', 'N/A')}
Contexto completo: {ig_sim_e.get('full_summary', 'N/A')}
Link: {ig_sim_e.get('link', '')}
Score: {ig_sim_e.get('score', 0)}/100
{f"CONTEXTO DO DIA: {day_context}" if day_context else ""}

POST 2 — MOTORSPORT (publicar 18:00):
Tipo: {ig_moto_e.get('content_type', 'N/A')}
Notícia: {ig_moto_e.get('title', 'N/A')}
Fonte: {ig_moto_e.get('source', 'N/A')}
Contexto completo: {ig_moto_e.get('full_summary', 'N/A')}
Link: {ig_moto_e.get('link', '')}
Score: {ig_moto_e.get('score', 0)}/100
{f"CONTEXTO DO DIA: {day_context}" if day_context else ""}

TAREFA — Para CADA post gera:
0. Para cada post, estrutura primeiro a lógica editorial antes de escrever a caption
1. Caption completa (hook forte primeira linha, máx 2200 chars)
2. POST 1 — formato {ig_manha}: {"5-7 slides, texto por slide, CTA no último" if ig_manha == "Carrossel" else "conceito visual, texto overlay 3-5 secções, ~30s"}
   POST 2 — formato {ig_tarde}: {"conceito visual, texto overlay 3-5 secções, ~30s" if ig_tarde == "Reel" else "5-7 slides, texto por slide, CTA no último"}
3. 15-20 hashtags por post (mix PT + EN, específicas do tema)

REGRAS:
- O formato por defeito deve ser carrossel editorial.
- Só usar Reel se a notícia tiver força visual clara e funcionar bem em formato rápido.
- Cada post deve centrar-se numa ideia principal, não num resumo genérico da notícia.
- Estrutura editorial recomendada: Hook -> O que aconteceu -> Porque importa -> O detalhe que quase ninguém viu -> Pergunta final
- Cada post tem valor standalone
- Emojis com moderação
- Nunca preços, nunca venda directa
{NOTAS_LEGAIS_SOCIAL}
{REGRA_NAO_PUBLICAR}""")
    md.append("````")
    md.append("")

    # ── PROMPT 2: X/TWITTER ──────────────────────────────────────────────
    md.append("---")
    md.append("")
    md.append("## PROMPT 2 — X/TWITTER (2 threads)")
    md.append("")
    md.append("````")
    md.append(f"""És o gestor de X/Twitter do Simula Project.
Tom: directo, opinativo, convida à discussão. PT-PT. Sem imagens. Texto + link.

THREAD 1 — SIM RACING (publicar 09:30):
Tipo: {x1_e.get('content_type', 'N/A')}
Notícia: {x1_e.get('title', 'N/A')}
Contexto completo: {x1_e.get('full_summary', '')}
Link: {x1_e.get('link', '')}

THREAD 2 — MOTORSPORT (publicar 18:30):
Tipo: {x2_e.get('content_type', 'N/A')}
Notícia: {x2_e.get('title', 'N/A')}
Contexto completo: {x2_e.get('full_summary', '')}
Link: {x2_e.get('link', '')}

TAREFA — Para CADA notícia, gera thread de 3 tweets:
- Tweet 1: Hook forte (máx 280 chars). SEM LINK.
- Tweet 2: Contexto ou opinião (máx 280 chars). SEM LINK.
- Tweet 3: Pergunta aberta à comunidade + link original + máx 3 hashtags

REGRAS:
- Link APENAS no tweet 3 (X penaliza links no tweet 1)
- Tom conversacional, não corporativo
{REGRA_NAO_PUBLICAR}""")
    md.append("````")
    md.append("")

    # ── PROMPT 3: YOUTUBE SHORT ───────────────────────────────────────────
    md.append("---")
    md.append("")
    md.append("## PROMPT 3 — YOUTUBE SHORT (~60s)")
    md.append("")
    md.append("````")
    md.append(f"""És o produtor de conteúdo do Simula Project.
Vais criar um YouTube Short faceless (~60 segundos). PT-PT.

NOTÍCIA SELECCIONADA:
Tipo: {yt_e.get('content_type', 'N/A')}
Notícia: {yt_e.get('title', 'N/A')} — {yt_e.get('source', '')}
Contexto completo: {yt_e.get('full_summary', '')}
Link: {yt_e.get('link', '')}

TAREFA:
1. 3 opções de título (máx 60 chars, emoji, hook forte)
2. Script voiceover (~150 palavras PT-PT, hook nos primeiros 3s, CTA subtil no fim)
3. Plano visual segundo a segundo (0s → 60s)
4. Lista de footage necessário
5. Thumbnail concept (texto, cores, layout)
6. Descrição YouTube com nota IA obrigatória
7. 20 tags YouTube (mix PT + EN)
8. Mood musical sugerido (biblioteca gratuita YouTube)

NOTA OBRIGATÓRIA NA DESCRIÇÃO:
{NOTA_IA_YOUTUBE}
{NOTAS_LEGAIS_SOCIAL}
{REGRA_NAO_PUBLICAR}""")
    md.append("````")
    md.append("")

    # ── PROMPT 4: YOUTUBE SEMANAL (só ao domingo) ─────────────────────────
    if is_sunday:
        yt_weekly = plan.get("youtube_weekly", [])
        weekly_block = _generate_news_block(yt_weekly)
        md.append("---")
        md.append("")
        md.append("## PROMPT 4 — YOUTUBE SEMANAL (8-12 min) 📅 DOMINGO")
        md.append("")
        md.append("*Artigos acumulados ao longo da semana (memória semanal real via weekly_cache.json).*")
        md.append("")
        md.append("````")
        md.append(f"""És o produtor de conteúdo do Simula Project.
Vais criar o RESUMO SEMANAL de sim racing — vídeo YouTube faceless 8-12 minutos. PT-PT.

MELHORES NOTÍCIAS DA SEMANA ({data_str}):
{weekly_block}

TAREFA:
1. Tema central da semana (1 frase que resume o que aconteceu)
2. 3 opções de título (máx 70 chars, SEO, emoji)
3. Script completo com timestamps:
   [00:00] Intro "Esta semana em sim racing..." (30s)
   [00:30] Notícia mais importante (2-3 min)
   [03:00] Segunda notícia (1-2 min)
   [05:00] Terceira notícia (1-2 min)
   [07:00] Hardware/Reviews da semana (1-2 min)
   [09:00] O que vem aí — próxima semana (30s)
   [09:30] CTA + subscrição
   Total: ~1800-2200 palavras PT-PT
4. Plano de footage por secção
5. 3 thumbnail concepts
6. Descrição YouTube SEO com timestamps
7. 20 tags (mix PT + EN)

NOTA OBRIGATÓRIA NA DESCRIÇÃO:
{NOTA_IA_YOUTUBE}
{NOTAS_LEGAIS_SOCIAL}
{REGRA_NAO_PUBLICAR}""")
        md.append("````")
        md.append("")

    # ── PROMPT 5: REDDIT ─────────────────────────────────────────────────
    md.append("---")
    md.append("")
    md.append("## PROMPT 5 — REDDIT (1-3 posts)")
    md.append("")
    md.append("````")
    md.append(f"""Vais criar posts Reddit sobre sim racing.
ZERO menção ao Simula Project. Contribuições genuínas à comunidade. Tudo em INGLÊS.

NOTÍCIAS ELEGÍVEIS (score alto, sem shorts, sem conteúdo promocional):
{reddit_block}

{"TAREFA — Para cada notícia elegível (máx 3), escolhe o tipo mais adequado:" if reddit_arts else "HOJE NÃO HÁ ARTIGOS COM SUBSTÂNCIA SUFICIENTE PARA REDDIT. Não publicar."}

TIPO A — Link Post:
- Subreddit mais adequado (r/simracing, r/iRacing, r/assettocorsa, r/granturismo, r/trucksim, etc.)
- Título informativo, não clickbait
- Link original da notícia
- Comentário do OP: 2-3 frases em inglês com contexto genuíno

TIPO B — Discussion Post (se gerar debate):
- Subreddit mais adequado
- Título como pergunta ou tema de discussão
- Corpo: contexto + perspectiva pessoal + pergunta aberta
- Flair sugerida

REGRAS: inglês, zero auto-promoção, tom de membro genuíno da comunidade
{REGRA_NAO_PUBLICAR}""")
    md.append("````")
    md.append("")

    # ── PROMPT 6: DISCORD ────────────────────────────────────────────────
    md.append("---")
    md.append("")
    md.append("## PROMPT 6 — DISCORD")
    md.append("")
    md.append("````")
    if discord_art:
        cat_label = discord_art.get("category", "").upper().replace("_", " ")
        md.append(f"""Vais criar 1 post para o servidor Discord do Simula Project.
Formatação Discord markdown. PT-PT. Tom casual e amigável.

CANAL: #noticias-dia

NOTÍCIA:
{discord_art.get('title', 'N/A')} — {discord_art.get('source', 'N/A')}
Contexto completo: {discord_e.get('full_summary', '')}
Link: {discord_art.get('link', '')}

FORMATO OBRIGATÓRIO:
> 📰 **[{cat_label}] {discord_art.get('title', 'N/A')}**
> [resumo em 2-3 frases claras e directas]
> 🔗 {discord_art.get('link', '')}
Reacções sugeridas: [3 emojis relevantes para o tema]

REGRAS:
- **bold** para títulos, > para quote block, *itálico* para destaques
- Emojis com moderação
- Tom casual — é Discord, não email
{REGRA_NAO_PUBLICAR}""")
    else:
        md.append("DISCORD — SILÊNCIO HOJE\nNenhum artigo atingiu o threshold mínimo de qualidade. Não publicar.")
    md.append("````")
    md.append("")

    # --- FOOTER ---
    md.append("---")
    md.append("")
    md.append(f"*Gerado automaticamente por SimulaNewsMachine v2.2 — {timestamp}*")
    md.append("")

    # --- AGENT OUTPUTS (MiniMax M2.7) ---
    agent_outputs = curated.get("agent_outputs", [])
    if agent_outputs:
        md.append("---")
        md.append("")
        md.append("# 🤖 POSTS GERADOS — PIPELINE MINIMAX M2.7")
        md.append("")
        md.append("*Score mínimo aprovação: 7.0/10*")
        md.append("")
        for i, output in enumerate(agent_outputs, 1):
            article  = output.get("article", {})
            post     = output.get("post", "")
            qa_raw   = output.get("qa", "")
            img      = output.get("image_prompt", "")
            voice    = output.get("voice_script", "")
            instagram_pack = output.get("instagram_pack", {})

            # Parse QA — tolerante a falhas parciais
            qa_score    = "N/A"
            qa_approved = False
            hashtags    = []
            try:
                qa_data     = json.loads(qa_raw)
                qa_score    = qa_data.get("average", "N/A")
                qa_approved = qa_data.get("approved", False)
                hashtags    = qa_data.get("hashtags", [])
                issues      = qa_data.get("issues", [])
            except Exception:
                issues = []

            # Não mostrar bloco vazio se agente falhou
            if not post and not img and not voice:
                continue

            status = "✅ APROVADO" if qa_approved else "⚠️ REVISTO PELO QA"
            qa_display = f"{qa_score}/10" if qa_score != "N/A" else "não disponível"

            md.append(f"## Post {i} — {article.get('title','')[:60]}")
            md.append(f"**Status:** {status} | **Score QA:** {qa_display}")
            if issues:
                md.append(f"**Issues:** {', '.join(issues)}")
            md.append("")

            if isinstance(instagram_pack, dict) and instagram_pack:
                slides = instagram_pack.get("slides", [])
                md.append(f"**Formato Instagram:** {instagram_pack.get('format', 'N/A')}")
                md.append("")
                md.append(f"**Cover Hook:** {instagram_pack.get('cover_hook', '')}")
                md.append("")
                if isinstance(slides, list) and slides:
                    md.append("**Slides:**")
                    for j, slide in enumerate(slides[:5], 1):
                        md.append(f"{j}. {slide}")
                    md.append("")
                if instagram_pack.get("caption"):
                    md.append(f"**Caption:** {instagram_pack.get('caption', '')}")
                    md.append("")
                if instagram_pack.get("community_question"):
                    md.append(f"**Pergunta à comunidade:** {instagram_pack.get('community_question', '')}")
                    md.append("")
                if instagram_pack.get("notes_for_design"):
                    md.append(f"**Notas para design:** {instagram_pack.get('notes_for_design', '')}")
                    md.append("")

            if post:
                md.append(post)
                md.append("")
            if hashtags:
                md.append("**Hashtags:** " + " ".join(hashtags))
                md.append("")
            if img:
                md.append("**Prompt de Imagem:**")
                md.append(f"```\n{img}\n```")
                md.append("")
            if voice:
                md.append("**Script de Voz (ElevenLabs):**")
                md.append(f"```\n{voice}\n```")
                md.append("")

    # ========================================================================
    # ESCREVER FICHEIRO
    # ========================================================================
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md))
        logger.info(f"Brief guardado em {output_path}")
    except Exception as e:
        logger.error(f"Erro ao guardar brief: {e}")
        raise
