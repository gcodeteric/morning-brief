"""
SimulaNewsMachine — Formatação do brief diário + 5 prompts para redes sociais.

Gera ficheiro .md completo no Desktop.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Mapeamento de categoria → emoji
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


def _format_article_highlight(article, index):
    """Formata artigo como destaque (posição 1-5)."""
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
    """Formata artigo compacto (posição 6-15)."""
    emoji = CATEGORY_EMOJI.get(article["category"], "📰")
    return f"{index}. {emoji} **{article['title']}** — {article['source']} | [Link]({article['link']})"


def _generate_news_block(selected):
    """Gera bloco de texto com as 15 notícias para injectar nos prompts."""
    lines = []
    for i, a in enumerate(selected, 1):
        emoji = CATEGORY_EMOJI.get(a["category"], "📰")
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

    # --- HEADER ---
    md.append(f"# SIMULA BRIEF — {dia_semana}, {data_str}")
    md.append("")
    md.append(f"**{total_before}** fontes analisadas | **{total_after}** novos após dedup | **{len(selected)}** selecionados")
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
    md.append("---")
    md.append("")
    md.append("## PROMPT 1 — INSTAGRAM + X/TWITTER")
    md.append("")
    md.append("```")
    md.append(f"""És o social media manager do Simula Project — o primeiro operador integrado de sim racing em Portugal. O teu tom é: inteligente, com humor subtil, educativo, sempre em PT-PT (português de Portugal). NUNCA vendes directamente. Crias conteúdo que faz a comunidade querer seguir-te.

CONTEXTO DA MARCA:
- Nome: Simula Project
- Posicionamento: Hub de sim racing, motorsport real, hardware, racing games e simuladores nostálgicos (ETS2, FS25, MSFS)
- Tom: Inteligente, humor subtil, educativo. Nunca corporativo. Nunca vendas.
- Idioma: PT-PT (português de Portugal)

NOTÍCIAS DE HOJE ({data_str}):
{news_block}

TAREFA:
Gera exactamente 4 posts usando 4 notícias DISTINTAS da lista acima:

1. **IG Post 1 (manhã, 09:00) — {"Carrossel" if now.weekday() % 2 == 0 else "Reel"}:**
   - {"Se carrossel: 5-7 slides, texto para cada slide, CTA no último" if now.weekday() % 2 == 0 else "Se reel: conceito visual, texto overlay por secção (3-5 secções), duração ~30s"}
   - Caption completa com hook forte na primeira linha
   - 15-20 hashtags relevantes (mix PT + EN)

2. **IG Post 2 (tarde, 18:00) — {"Reel" if now.weekday() % 2 == 0 else "Carrossel"}:**
   - {"Se reel: conceito visual, texto overlay por secção (3-5 secções), duração ~30s" if now.weekday() % 2 == 0 else "Se carrossel: 5-7 slides, texto para cada slide, CTA no último"}
   - Caption completa com hook forte
   - 15-20 hashtags

3. **X Post 1 (manhã, 09:30) — Thread ou tweet com imagem:**
   - Se thread: 3-5 tweets encadeados, primeiro tweet é hook
   - Se tweet único: texto + descrição da imagem a criar
   - 2-3 hashtags máximo

4. **X Post 2 (tarde, 18:30) — Take/reação:**
   - Opinião ou reação a uma notícia
   - Tom conversacional, convida à discussão
   - 2-3 hashtags máximo

REGRAS:
- Usa 4 notícias DISTINTAS (uma por post)
- Mínimo 1 notícia de Nostalgia ou Racing Games se houver na lista
- Cada post deve ter valor standalone (alguém que vê só esse post entende)
- Inclui emojis com moderação (não exagerar)
- Os hashtags devem ser relevantes e misturar PT + EN""")
    md.append("```")
    md.append("")

    # ----------------------------------------------------------------
    # PROMPT 2 — YOUTUBE SHORT (60s faceless)
    # ----------------------------------------------------------------
    md.append("---")
    md.append("")
    md.append("## PROMPT 2 — YOUTUBE SHORT (60s faceless)")
    md.append("")
    md.append("```")
    md.append(f"""És o produtor de conteúdo do Simula Project — o primeiro operador integrado de sim racing em Portugal. Vais criar um YouTube Short faceless (sem rosto, só gameplay/imagens + voiceover).

CONTEXTO DA MARCA:
- Nome: Simula Project
- Canal YouTube focado em sim racing, motorsport, hardware, racing games e simuladores
- Tom: Informativo, dinâmico, com personalidade. PT-PT.
- Formato: Faceless (gameplay footage + voiceover gerado por IA)

NOTÍCIAS DE HOJE ({data_str}):
{news_block}

TAREFA:
Escolhe a notícia com maior potencial viral da lista acima e gera TUDO para um YouTube Short de ~60 segundos:

1. **3 opções de título** (max 60 chars cada, com emoji, clickbait inteligente)

2. **Script de voiceover** (~150 palavras em PT-PT, pensado para ser lido pelo NotebookLLM):
   - Hook nos primeiros 3 segundos
   - Informação clara e concisa
   - Fecho com CTA subtil ("subscreve para mais")

3. **Plano visual segundo a segundo:**
   - 0-3s: [o que aparece]
   - 3-10s: [o que aparece]
   - (continuar até 60s)

4. **Gameplay/footage necessário:** lista exacta do que filmar ou onde encontrar footage

5. **Thumbnail concept:** descrição detalhada (texto, cores, layout)

6. **Descrição YouTube** (com a nota obrigatória abaixo)

7. **20 tags YouTube** (mix PT + EN)

8. **Música sugerida:** estilo/mood para biblioteca YouTube gratuita

NOTA OBRIGATÓRIA NA DESCRIÇÃO:
"Este vídeo utiliza narração gerada por inteligência artificial (IA). O conteúdo informativo foi verificado pela equipa Simula Project."

REGRAS:
- Máximo 60 segundos
- Primeiro 3 segundos são TUDO (hook visual + auditivo forte)
- Sem rosto, sem webcam
- Voiceover deve soar natural e informativo""")
    md.append("```")
    md.append("")

    # ----------------------------------------------------------------
    # PROMPT 3 — YOUTUBE LONGO (8-15 min faceless)
    # ----------------------------------------------------------------
    md.append("---")
    md.append("")
    md.append("## PROMPT 3 — YOUTUBE LONGO (8-15 min faceless)")
    md.append("")
    md.append("```")
    md.append(f"""És o produtor de conteúdo do Simula Project — o primeiro operador integrado de sim racing em Portugal. Vais criar um vídeo YouTube longo faceless (8-15 minutos, sem rosto, gameplay + voiceover).

CONTEXTO DA MARCA:
- Nome: Simula Project
- Canal YouTube focado em sim racing, motorsport, hardware, racing games e simuladores
- Tom: Informativo, profundo, com personalidade. PT-PT.
- Formato: Faceless (gameplay footage + voiceover gerado por IA)

NOTÍCIAS DE HOJE ({data_str}):
{news_block}

TAREFA:
Analisa as notícias acima e escolhe o melhor tema para um vídeo longo. Formatos possíveis:
- Review / Análise aprofundada
- Comparação (A vs B)
- Top 5 / Top 10
- Guia / Tutorial
- Resumo semanal de notícias

Gera TUDO:

1. **Formato escolhido e justificação** (1-2 frases)

2. **3 opções de título** (max 70 chars, SEO-friendly, com emoji)

3. **Script de voiceover COMPLETO com timestamps:**
   - [00:00] Intro + Hook (30s)
   - [00:30] Contexto (1-2 min)
   - [02:30] Secção principal (dividir em 3-5 blocos)
   - [XX:XX] Conclusão + CTA
   - Total: ~1500-2000 palavras em PT-PT

4. **Plano de filmagem por secção:**
   - Que gameplay/footage usar em cada parte
   - Transições sugeridas
   - Momentos para B-roll

5. **3 thumbnail concepts:** texto, cores, layout, emoção

6. **Descrição YouTube SEO** (com timestamps, links, nota IA)

7. **20 tags YouTube** (mix PT + EN, SEO-optimized)

8. **Cards e End Screen:** quando inserir e para que vídeos/playlists

NOTA OBRIGATÓRIA NA DESCRIÇÃO:
"Este vídeo utiliza narração gerada por inteligência artificial (IA). O conteúdo informativo foi verificado pela equipa Simula Project."

REGRAS:
- 8-15 minutos (sweet spot YouTube)
- Estrutura clara com timestamps
- Hook nos primeiros 30 segundos
- Cada secção deve ter valor (não encher)
- Pensar em SEO no título, descrição e tags""")
    md.append("```")
    md.append("")

    # ----------------------------------------------------------------
    # PROMPT 4 — REDDIT (2 posts)
    # ----------------------------------------------------------------
    md.append("---")
    md.append("")
    md.append("## PROMPT 4 — REDDIT (2 posts)")
    md.append("")
    md.append("```")
    md.append(f"""Vais criar 2 posts para Reddit sobre sim racing. ATENÇÃO: ZERO menção ao Simula Project. Estes posts são contribuições genuínas para a comunidade.

NOTÍCIAS DE HOJE ({data_str}):
{news_block}

TAREFA:
Gera 2 posts Reddit completos:

**POST 1 — Link post com novidade (r/simracing ou sub mais adequado):**
- Subreddit recomendado (r/simracing, r/iRacing, r/assettocorsa, r/granturismo, r/trucksim, etc.)
- Título (seguir convenções do sub — não clickbait)
- Link original da notícia
- Comentário inicial do OP (2-3 frases em inglês, dar contexto ou opinião)

**POST 2 — Discussion post (self post):**
- Subreddit recomendado
- Título (pergunta ou tema de discussão)
- Corpo do post (3-5 parágrafos em inglês):
  - Contexto da discussão
  - A tua perspectiva/experiência
  - Pergunta aberta para a comunidade
- Flair sugerida

REGRAS:
- Tudo em INGLÊS (Reddit internacional)
- ZERO menção ao Simula Project, zero auto-promoção
- Tom: membro genuíno da comunidade
- Seguir etiqueta de cada subreddit
- Não ser clickbait no título
- Adicionar valor real à discussão""")
    md.append("```")
    md.append("")

    # ----------------------------------------------------------------
    # PROMPT 5 — DISCORD (2 posts)
    # ----------------------------------------------------------------
    md.append("---")
    md.append("")
    md.append("## PROMPT 5 — DISCORD (2 posts)")
    md.append("")
    md.append("````")
    md.append(f"""Vais criar 2 posts para o servidor Discord do Simula Project. Usa formatação Discord markdown.

CONTEXTO:
- Servidor: Simula Project (comunidade portuguesa de sim racing)
- Canais disponíveis: #noticias, #discussao, #hardware, #setups, #off-topic
- Tom: casual, informativo, amigável. PT-PT.

NOTÍCIAS DE HOJE ({data_str}):
{news_block}

TAREFA:
Gera 2 posts Discord completos:

POST 1 — #noticias (notícia formatada):
  Canal: #noticias
  Formato Discord markdown com:
  - Emoji + título em bold
  - Resumo em 2-3 frases
  - Link original
  - Reacções sugeridas (emojis para o bot)
  - Tag de categoria

POST 2 — #discussao (pergunta/tema casual):
  Canal: #discussao
  Formato:
  - Pergunta ou tema que gere conversa
  - Contexto breve (2-3 frases)
  - Poll sugerida (se aplicável)
  - Tom casual, como se fosses um membro do server

REGRAS:
- PT-PT (português de Portugal)
- Usar formatação Discord: **bold**, *itálico*, > quote
- Emojis com moderação
- Tom casual mas informativo
- Não ser formal demais — é Discord, não email""")
    md.append("````")
    md.append("")

    # --- FOOTER ---
    md.append("---")
    md.append("")
    md.append(f"*Gerado automaticamente por SimulaNewsMachine v2.1 — {timestamp}*")
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
