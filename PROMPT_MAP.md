# Prompt Map

Este documento serve para maintainers encontrarem rapidamente onde vivem os prompts, que funções os usam e em que campos os outputs são guardados.

## 1. Text / Editorial Prompts

### Instagram digest prompts

- Ficheiro: [agents.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py)
- Local: `AGENT_PROMPTS`
- Chaves actuais:
  - `instagram_digest_analyst`
  - `instagram_digest_copywriter`
  - `instagram_digest_qa`

Função que corre este fluxo:

- `run_instagram_digest_pipeline(digest_articles, digest_type)`

Outputs principais:

- `instagram_pack`
- `post`
- `image_prompt`
- `voice_script`
- `qa`

### Single-article editorial prompts

- Ficheiro: [agents.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py)
- Local: `AGENT_PROMPTS`
- Chaves actuais:
  - `analyst`
  - `copywriter`
  - `qa`

Função que corre este fluxo:

- `run_full_pipeline(article)`

### X / YouTube / Reddit / Discord prompts

- Ficheiro: [formatter.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py)
- Renderização actual:
  - `PROMPT 2 — X/TWITTER`
  - `PROMPT 3 — YOUTUBE SHORT`
  - `PROMPT 4 — YOUTUBE SEMANAL`
  - `PROMPT 5 — REDDIT`
  - `PROMPT 6 — DISCORD`

### Instagram operational prompt in the brief

- Ficheiro: [formatter.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py)
- Renderização actual:
  - `PROMPT 1 — INSTAGRAM (2 carrosséis editoriais com imagem)`

Este prompt operacional usa:

- `instagram_morning_digest`
- `instagram_afternoon_digest`
- `instagram_morning_pack`
- `instagram_afternoon_pack`

## 2. Image Prompts

- Ficheiro: [agents.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py)
- Prompt/system prompt:
  - `AGENT_PROMPTS["image_director"]`
- Funções que o usam:
  - `run_full_pipeline(article)`
  - `run_instagram_digest_pipeline(digest_articles, digest_type)`

Campo onde o output é guardado:

- `image_prompt`

Onde aparece depois:

- brief renderizado por [formatter.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py)
- email digest em [email_digest.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/email_digest.py)

## 3. Voice Prompts

- Ficheiro: [agents.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py)
- Prompt/system prompt:
  - `AGENT_PROMPTS["voice_director"]`
- Funções que o usam:
  - `run_full_pipeline(article)`
  - `run_instagram_digest_pipeline(digest_articles, digest_type)`

Campo onde o output é guardado:

- `voice_script`

Onde aparece depois:

- brief renderizado por [formatter.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py)
- email digest em [email_digest.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/email_digest.py)

## 4. QA Prompts

- Ficheiro: [agents.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py)
- Prompt/system prompt:
  - `AGENT_PROMPTS["qa"]`
  - `AGENT_PROMPTS["instagram_digest_qa"]`

Campos devolvidos:

- `qa`
- dentro de `qa`: `scores`, `average`, `approved`, `hashtags`, `issues`, `improved_hook`, `improved_post`

Como afecta fallback:

- `run_full_pipeline(article)` usa `improved_post` se `approved` for falso e houver conteúdo melhorado
- `run_instagram_digest_pipeline(...)` faz o mesmo para o digest pack/post do Instagram

## 5. Data Flow

Fluxo actual, em alto nível:

1. [planner.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/planner.py) selecciona artigos e digests
2. [manual_overrides.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/manual_overrides.py) resolve a selecção final, se existir `manual_overrides.json`
3. [agents.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py) gera:
   - packs estruturados
   - texto final
   - prompt de imagem
   - script de voz
   - QA
4. [formatter.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py) renderiza tudo no brief `.md`
5. [email_digest.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/email_digest.py) usa a selecção final resolvida para o email
6. [card_generator.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/card_generator.py) gera cards com fallback seguro

## 6. Naming Map

Campos actuais relevantes no código:

- `instagram_morning_digest`
- `instagram_morning_digest_alternatives`
- `instagram_afternoon_digest`
- `instagram_afternoon_digest_alternatives`
- `instagram_morning_output`
- `instagram_morning_pack`
- `instagram_afternoon_output`
- `instagram_afternoon_pack`
- `instagram_pack`
- `agent_outputs`
- `image_prompt`
- `voice_script`
- `qa`
- `override_summary`
- `manual_overrides_applied`

Compatibilidade antiga ainda presente em alguns pontos:

- `instagram_sim_racing`
- `instagram_motorsport`

Esses campos continuam úteis como fallback/compatibilidade, mas o modelo recomendado de Instagram é agora por digest.

## 7. Card Generator Limitation

Estado actual:

- [card_generator.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/card_generator.py) tem suporte mínimo para digests
- reutiliza `cover_hook` e `notes_for_design` quando existirem
- não faz um redesign completo de cover específico por carrossel
- se faltar pack, cai para fallback seguro com os campos antigos
