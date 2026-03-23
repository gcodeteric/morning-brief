"""
SimulaNewsMachine — Formatação do brief diário + 5 prompts para redes sociais.

Gera ficheiro .md completo no Desktop.
"""

import logging
from datetime import datetime

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
REGRA EDITORIAL OBRIGATORIA:
Se alguma das noticias for fraca, redundante, excessivamente promocional ou sem substancia suficiente para gerar conteudo de qualidade, responde:
"NAO PUBLICAR — [motivo]"
E melhor nao publicar do que publicar conteudo fraco. A reputacao do Simula Project depende da qualidade, nao da quantidade."""

# FIX 3.2 — Notas legais PT/UE para prompts de redes sociais
NOTAS_LEGAIS_SOCIAL = """
REGRAS LEGAIS OBRIGATORIAS (Portugal/UE):
- Se mencionares produto cedido para review: incluir #OFERTA no inicio da legenda/post
- Se incluires link de afiliado: indicar "link de afiliado — posso ganhar comissao"
- NUNCA inventar claims de performance de hardware nao verificados
- Cumprir Codigo da Publicidade Portugues (DL 330/90) + RGPD"""

NOTA_IA_YOUTUBE = '"Este video utiliza narracao gerada por inteligencia artificial (IA). O conteudo informativo foi verificado pela equipa Simula Project."'


def _format_article_highlight(article, index):
    """Formata artigo como destaque (posicao 1-5)."""
    emoji = CATEGORY_EMOJI.get(article["category"], "📰")
    title = article["title"]
    source = article["source"]
    summary = article.get("summary", "")[:200]
    link = article["link"]
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
    emoji = CATEGORY_EMOJI.get(article["category"], "📰")
    return f"{index}. {emoji} **{article['title']}** — {article['source']} | [Link]({article['link']})"


def _generate_news_block(selected):
    """Gera bloco de texto com as 15 noticias para injectar nos prompts."""
    lines = []
    for i, a in enumerate(selected, 1):
        lines.append(f"{i}. [{a['category'].upper()}] {a['title']} — {a['source']}")
        if a.get("summary"):
            lines.append(f"   Resumo: {a['summary'][:150]}")
        lines.append(f"   Link: {a['link']}")
        lines.append("")
    return "\n".join(lines)


def format_brief(curated, output_path):
    """Gera o ficheiro .md completo com brief + 5 prompts."""
    selected = curated["selected"]
    categories = curated["categories"]
    total_before = curated["total_before_dedup"]
    total_after = curated["total_after_dedup"]

    now = datetime.now()
    dia_semana = DIAS_SEMANA.get(now.weekday(), "")
    data_str = now.strftime("%d/%m/%Y")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    news_block = _generate_news_block(selected)

    # ========================================================================
    # CONSTRUIR O MARKDOWN
    # ========================================================================
    md = []

    # --- HEADER --- (FIX 3.3: "artigos recolhidos" em vez de "fontes analisadas")
    md.append(f"# SIMULA BRIEF — {dia_semana}, {data_str}")
    md.append("")
    md.append(f"**{total_before}** artigos recolhidos | **{total_after}** novos após dedup | **{len(selected)}** selecionados")
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

    # ====================================================================
    # SECÇÃO 2: 5 PROMPTS
    # ====================================================================
    md.append("---")
    md.append("")
    md.append("# 🚀 PROMPTS PARA REDES SOCIAIS")
    md.append("")
    md.append("*Copia cada prompt abaixo e cola directamente no Claude Sonnet.*")
    md.append("")

    # ----------------------------------------------------------------
    # PROMPT 1 — INSTAGRAM + X/TWITTER
    # ----------------------------------------------------------------
    ig_manha = "Carrossel" if now.weekday() % 2 == 0 else "Reel"
    ig_tarde = "Reel" if now.weekday() % 2 == 0 else "Carrossel"
    ig_manha_desc = (
        "Se carrossel: 5-7 slides, texto para cada slide, CTA no ultimo"
        if now.weekday() % 2 == 0 else
        "Se reel: conceito visual, texto overlay por seccao (3-5 seccoes), duracao ~30s"
    )
    ig_tarde_desc = (
        "Se reel: conceito visual, texto overlay por seccao (3-5 seccoes), duracao ~30s"
        if now.weekday() % 2 == 0 else
        "Se carrossel: 5-7 slides, texto para cada slide, CTA no ultimo"
    )

    md.append("---")
    md.append("")
    md.append("## PROMPT 1 — INSTAGRAM + X/TWITTER")
    md.append("")
    md.append("````")
    md.append(f"""Es o social media manager do Simula Project — o primeiro operador integrado de sim racing em Portugal. O teu tom e: inteligente, com humor subtil, educativo, sempre em PT-PT (portugues de Portugal). NUNCA vendes directamente. Crias conteudo que faz a comunidade querer seguir-te.

CONTEXTO DA MARCA:
- Nome: Simula Project
- Posicionamento: Hub de sim racing, motorsport real, hardware, racing games e simuladores nostalgicos (ETS2, FS25, MSFS)
- Tom: Inteligente, humor subtil, educativo. Nunca corporativo. Nunca vendas.
- Idioma: PT-PT (portugues de Portugal)

NOTICIAS DE HOJE ({data_str}):
{news_block}

TAREFA:
Gera exactamente 4 posts usando 4 noticias DISTINTAS da lista acima:

1. **IG Post 1 (manha, 09:00) — {ig_manha}:**
   - {ig_manha_desc}
   - Caption completa com hook forte na primeira linha
   - 15-20 hashtags relevantes (mix PT + EN)

2. **IG Post 2 (tarde, 18:00) — {ig_tarde}:**
   - {ig_tarde_desc}
   - Caption completa com hook forte
   - 15-20 hashtags

3. **X Post 1 (manha, 09:30) — Thread ou tweet com imagem:**
   - Se thread: 3-5 tweets encadeados, primeiro tweet e hook
   - Se tweet unico: texto + descricao da imagem a criar
   - 2-3 hashtags maximo

4. **X Post 2 (tarde, 18:30) — Take/reaccao:**
   - Opiniao ou reaccao a uma noticia
   - Tom conversacional, convida a discussao
   - 2-3 hashtags maximo

REGRAS:
- Usa 4 noticias DISTINTAS (uma por post)
- Minimo 1 noticia de Nostalgia ou Racing Games se houver na lista
- Cada post deve ter valor standalone (alguem que ve so esse post entende)
- Inclui emojis com moderacao (nao exagerar)
- Os hashtags devem ser relevantes e misturar PT + EN
{NOTAS_LEGAIS_SOCIAL}
{REGRA_NAO_PUBLICAR}""")
    md.append("````")
    md.append("")

    # ----------------------------------------------------------------
    # PROMPT 2 — YOUTUBE SHORT (60s faceless)
    # ----------------------------------------------------------------
    md.append("---")
    md.append("")
    md.append("## PROMPT 2 — YOUTUBE SHORT (60s faceless)")
    md.append("")
    md.append("````")
    md.append(f"""Es o produtor de conteudo do Simula Project — o primeiro operador integrado de sim racing em Portugal. Vais criar um YouTube Short faceless (sem rosto, so gameplay/imagens + voiceover).

CONTEXTO DA MARCA:
- Nome: Simula Project
- Canal YouTube focado em sim racing, motorsport, hardware, racing games e simuladores
- Tom: Informativo, dinamico, com personalidade. PT-PT.
- Formato: Faceless (gameplay footage + voiceover gerado por IA)

NOTICIAS DE HOJE ({data_str}):
{news_block}

TAREFA:
Escolhe a noticia com maior potencial viral da lista acima e gera TUDO para um YouTube Short de ~60 segundos:

1. **3 opcoes de titulo** (max 60 chars cada, com emoji, clickbait inteligente)

2. **Script de voiceover** (~150 palavras em PT-PT, pensado para ser lido pelo NotebookLLM):
   - Hook nos primeiros 3 segundos
   - Informacao clara e concisa
   - Fecho com CTA subtil ("subscreve para mais")

3. **Plano visual segundo a segundo:**
   - 0-3s: [o que aparece]
   - 3-10s: [o que aparece]
   - (continuar ate 60s)

4. **Gameplay/footage necessario:** lista exacta do que filmar ou onde encontrar footage

5. **Thumbnail concept:** descricao detalhada (texto, cores, layout)

6. **Descricao YouTube** (com a nota obrigatoria abaixo)

7. **20 tags YouTube** (mix PT + EN)

8. **Musica sugerida:** estilo/mood para biblioteca YouTube gratuita

NOTA OBRIGATORIA NA DESCRICAO:
{NOTA_IA_YOUTUBE}
{NOTAS_LEGAIS_SOCIAL}
{REGRA_NAO_PUBLICAR}

REGRAS:
- Maximo 60 segundos
- Primeiro 3 segundos sao TUDO (hook visual + auditivo forte)
- Sem rosto, sem webcam
- Voiceover deve soar natural e informativo""")
    md.append("````")
    md.append("")

    # ----------------------------------------------------------------
    # PROMPT 3 — YOUTUBE LONGO (8-15 min faceless)
    # ----------------------------------------------------------------
    md.append("---")
    md.append("")
    md.append("## PROMPT 3 — YOUTUBE LONGO (8-15 min faceless)")
    md.append("")
    md.append("````")
    md.append(f"""Es o produtor de conteudo do Simula Project — o primeiro operador integrado de sim racing em Portugal. Vais criar um video YouTube longo faceless (8-15 minutos, sem rosto, gameplay + voiceover).

CONTEXTO DA MARCA:
- Nome: Simula Project
- Canal YouTube focado em sim racing, motorsport, hardware, racing games e simuladores
- Tom: Informativo, profundo, com personalidade. PT-PT.
- Formato: Faceless (gameplay footage + voiceover gerado por IA)

NOTICIAS DE HOJE ({data_str}):
{news_block}

TAREFA:
Analisa as noticias acima e escolhe o melhor tema para um video longo. Formatos possiveis:
- Review / Analise aprofundada
- Comparacao (A vs B)
- Top 5 / Top 10
- Guia / Tutorial
- Resumo semanal de noticias

Gera TUDO:

1. **Formato escolhido e justificacao** (1-2 frases)

2. **3 opcoes de titulo** (max 70 chars, SEO-friendly, com emoji)

3. **Script de voiceover COMPLETO com timestamps:**
   - [00:00] Intro + Hook (30s)
   - [00:30] Contexto (1-2 min)
   - [02:30] Seccao principal (dividir em 3-5 blocos)
   - [XX:XX] Conclusao + CTA
   - Total: ~1500-2000 palavras em PT-PT

4. **Plano de filmagem por seccao:**
   - Que gameplay/footage usar em cada parte
   - Transicoes sugeridas
   - Momentos para B-roll

5. **3 thumbnail concepts:** texto, cores, layout, emocao

6. **Descricao YouTube SEO** (com timestamps, links, nota IA)

7. **20 tags YouTube** (mix PT + EN, SEO-optimized)

8. **Cards e End Screen:** quando inserir e para que videos/playlists

NOTA OBRIGATORIA NA DESCRICAO:
{NOTA_IA_YOUTUBE}
{NOTAS_LEGAIS_SOCIAL}
{REGRA_NAO_PUBLICAR}

REGRAS:
- 8-15 minutos (sweet spot YouTube)
- Estrutura clara com timestamps
- Hook nos primeiros 30 segundos
- Cada seccao deve ter valor (nao encher)
- Pensar em SEO no titulo, descricao e tags""")
    md.append("````")
    md.append("")

    # ----------------------------------------------------------------
    # PROMPT 4 — REDDIT (2 posts)
    # ----------------------------------------------------------------
    md.append("---")
    md.append("")
    md.append("## PROMPT 4 — REDDIT (2 posts)")
    md.append("")
    md.append("````")
    md.append(f"""Vais criar 2 posts para Reddit sobre sim racing. ATENCAO: ZERO mencao ao Simula Project. Estes posts sao contribuicoes genuinas para a comunidade.

NOTICIAS DE HOJE ({data_str}):
{news_block}

TAREFA:
Gera 2 posts Reddit completos:

**POST 1 — Link post com novidade (r/simracing ou sub mais adequado):**
- Subreddit recomendado (r/simracing, r/iRacing, r/assettocorsa, r/granturismo, r/trucksim, etc.)
- Titulo (seguir convencoes do sub — nao clickbait)
- Link original da noticia
- Comentario inicial do OP (2-3 frases em ingles, dar contexto ou opiniao)

**POST 2 — Discussion post (self post):**
- Subreddit recomendado
- Titulo (pergunta ou tema de discussao)
- Corpo do post (3-5 paragrafos em ingles):
  - Contexto da discussao
  - A tua perspectiva/experiencia
  - Pergunta aberta para a comunidade
- Flair sugerida

REGRAS:
- Tudo em INGLES (Reddit internacional)
- ZERO mencao ao Simula Project, zero auto-promocao
- Tom: membro genuino da comunidade
- Seguir etiqueta de cada subreddit
- Nao ser clickbait no titulo
- Adicionar valor real a discussao
{NOTAS_LEGAIS_SOCIAL}
{REGRA_NAO_PUBLICAR}""")
    md.append("````")
    md.append("")

    # ----------------------------------------------------------------
    # PROMPT 5 — DISCORD (2 posts)
    # ----------------------------------------------------------------
    md.append("---")
    md.append("")
    md.append("## PROMPT 5 — DISCORD (2 posts)")
    md.append("")
    md.append("````")
    md.append(f"""Vais criar 2 posts para o servidor Discord do Simula Project. Usa formatacao Discord markdown.

CONTEXTO:
- Servidor: Simula Project (comunidade portuguesa de sim racing)
- Canais disponiveis: #noticias, #discussao, #hardware, #setups, #off-topic
- Tom: casual, informativo, amigavel. PT-PT.

NOTICIAS DE HOJE ({data_str}):
{news_block}

TAREFA:
Gera 2 posts Discord completos:

POST 1 — #noticias (noticia formatada):
  Canal: #noticias
  Formato Discord markdown com:
  - Emoji + titulo em bold
  - Resumo em 2-3 frases
  - Link original
  - Reaccoes sugeridas (emojis para o bot)
  - Tag de categoria

POST 2 — #discussao (pergunta/tema casual):
  Canal: #discussao
  Formato:
  - Pergunta ou tema que gere conversa
  - Contexto breve (2-3 frases)
  - Poll sugerida (se aplicavel)
  - Tom casual, como se fosses um membro do server

REGRAS:
- PT-PT (portugues de Portugal)
- Usar formatacao Discord: **bold**, *italico*, > quote
- Emojis com moderacao
- Tom casual mas informativo
- Nao ser formal demais — e Discord, nao email
{NOTAS_LEGAIS_SOCIAL}
{REGRA_NAO_PUBLICAR}""")
    md.append("````")
    md.append("")

    # --- FOOTER ---
    md.append("---")
    md.append("")
    md.append(f"*Gerado automaticamente por SimulaNewsMachine v2.2 — {timestamp}*")
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
