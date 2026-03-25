# PRE-AUDIT COVERAGE REPORT

Data: 2026-03-25
Repositório: `gcodeteric/morning-brief`

## Resultado da Fase 0

Foi feita uma inspeção real ao código e uma validação dirigida dos outputs editoriais antes da auditoria ultra.

Conclusão desta fase:
- Não foram encontrados gaps bloqueadores na cobertura obrigatória.
- Não foi necessário aplicar patch pré-auditoria.
- Foram encontradas divergências documentais e algumas fragilidades não bloqueadoras, a analisar na auditoria ultra.

## Evidência usada na Fase 0

Comandos e validações reais:
- leitura integral de `main.py`, `formatter.py`, `planner.py`, `manual_overrides.py`, `agents.py`, `card_generator.py`, `email_digest.py`, `alerts.py`, `scanner.py`, `curator.py`, `config.py`, `news_sources.py`, `feeds.py`, `channel_id_extractor.py`, `README.md`, `abrir_overrides_json.bat`, `data/manual_overrides.example.json`
- `python main.py --dry-run`
- geração dirigida de brief temporário com `plan` completo, `instagram_pack`, overrides e domingo
- geração dirigida de `email_digest` com brief real em disco

## Matriz de cobertura obrigatória

| ID | Item obrigatório | Estado | Evidência real | Notas |
|---|---|---|---|---|
| A1 | Instagram: prompt/editorial pack para Instagram | IMPLEMENTADO | `formatter.py` contém `PROMPT 1 — INSTAGRAM`; `agents.py` gera `instagram_pack` | O prompt foi reforçado para carrossel editorial |
| A2 | Instagram: carrossel editorial por defeito | IMPLEMENTADO | `formatter.py` inclui a regra `O formato por defeito deve ser carrossel editorial.` | Reel fica condicionado a força visual |
| A3 | Instagram: output com cover hook / slides / caption / community question / notes for design | IMPLEMENTADO | `agents.py` `copywriter` devolve JSON com esses campos | Validado com stub JSON |
| A4 | Instagram: `instagram_pack` aparece no brief | IMPLEMENTADO | `formatter.py` renderiza `**Formato Instagram:**`, `**Cover Hook:**`, `**Slides:**`, `**Caption:**`, `**Pergunta à comunidade:**`, `**Notas para design:**` | Validado com brief temporário |
| A5 | X / Twitter: prompt para threads | IMPLEMENTADO | `formatter.py` contém `PROMPT 2 — X/TWITTER (2 threads)` | Estrutura de 3 tweets por thread |
| A6 | X / Twitter: link apenas no tweet final | IMPLEMENTADO | Regra explícita no prompt: `Link APENAS no tweet 3` | Cobertura via prompt, não via enforcement programático |
| A7 | X / Twitter: estrutura coerente por thread | IMPLEMENTADO | `Hook`, `Contexto/opinião`, `Pergunta + link` | |
| A8 | YouTube Short: prompt/output diário | IMPLEMENTADO | `formatter.py` contém `PROMPT 3 — YOUTUBE SHORT (~60s)` | Inclui título, script, plano visual, footage, thumbnail, descrição, tags |
| A9 | YouTube Weekly: só ao domingo | IMPLEMENTADO | `formatter.py` só injeta `PROMPT 4` quando `is_sunday=True` | |
| A10 | YouTube Weekly: proxy/documentação explícita se não houver memória real | IMPLEMENTADO | O código real já usa memória semanal real em `planner.py` via `weekly_cache.json`; `formatter.py` documenta isso | Diverge da fase antiga de proxy |
| A11 | Reddit: output para 1–3 posts elegíveis | IMPLEMENTADO | `formatter.py` contém `PROMPT 5 — REDDIT (1-3 posts)` | |
| A12 | Reddit: exclusão de fraco/promocional/shorts | IMPLEMENTADO | `planner.py::_reddit_eligible()` filtra shorts, score baixo e promo | |
| A13 | Discord: output de post | IMPLEMENTADO | `formatter.py` contém `PROMPT 6 — DISCORD` | |
| A14 | Discord: silêncio explícito se não houver artigo bom | IMPLEMENTADO | `formatter.py` escreve `DISCORD — SILÊNCIO HOJE` quando `discord_post` é `None` | Confirmado por leitura do código |
| B15 | `agent_outputs` em `curated` | IMPLEMENTADO | `main.py` define sempre `curated["agent_outputs"] = agent_outputs or []` | |
| B16 | `analysis` no output dos agentes | IMPLEMENTADO | `agents.py::run_full_pipeline()` devolve `analysis` | |
| B17 | `post` no output dos agentes | IMPLEMENTADO | `agents.py::run_full_pipeline()` devolve `post` | Mantém compatibilidade |
| B18 | `image_prompt` no output dos agentes | IMPLEMENTADO | `agents.py::run_full_pipeline()` devolve `image_prompt` | |
| B19 | `voice_script` no output dos agentes | IMPLEMENTADO | `agents.py::run_full_pipeline()` devolve `voice_script` | |
| B20 | `qa` no output dos agentes | IMPLEMENTADO | `agents.py::run_full_pipeline()` devolve `qa` | |
| B21 | `instagram_pack` no output dos agentes | IMPLEMENTADO | `agents.py::run_full_pipeline()` devolve `instagram_pack` | Campo novo adicional |
| C22 | Alternativas por canal no planner | IMPLEMENTADO | `planner.py` devolve listas `*_alternatives` | Validado em teste dirigido |
| C23 | `manual_overrides.json` opcional | IMPLEMENTADO | `manual_overrides.py::load_manual_overrides()` devolve `{}` se não existir | `main.py --dry-run` confirmou comportamento base |
| C24 | Batch/launcher para abrir overrides | IMPLEMENTADO | `abrir_overrides_json.bat` cria e abre `data\\manual_overrides.json` | |
| C25 | Regeneração do brief com seleção final | IMPLEMENTADO | `main.py` aplica overrides antes de `format_brief(...)` | |
| C26 | Email digest usa a seleção final resolvida | IMPLEMENTADO | `main.py` passa `editorial_plan` já resolvido a `build_email_digest(...)` | Validado em teste dirigido |
| C27 | Email digest anexa `.md` final | IMPLEMENTADO | `email_digest.py` expõe `markdown_attachment` e `send_email_digest()` anexa quando ativado | Validado com SMTP stub |
| C28 | Email digest pode anexar cards se existirem | IMPLEMENTADO | `email_digest.py` agrega `card_attachments` e anexa se `attach_cards=True` | Validado com SMTP stub |

## Itens em falta antes da auditoria

Nenhum item bloqueador foi encontrado como `AUSENTE`.

## Itens marcados como frágeis ou divergentes, mas não bloqueadores

- Divergência de intenção antiga: `youtube_weekly` já não é proxy diário; o código real usa memória semanal via `weekly_cache.json`.
- Divergência documental: o `README.md` continua a dizer que o sistema inclui `5 prompts`, quando o código real gera `6 prompts`.
- Divergência documental: a docstring de `formatter.py` ainda menciona `5 prompts`, mas o output real já inclui 6 prompts e a secção `agent_outputs`.
- Cobertura de X/Twitter está implementada ao nível de prompt editorial, não de validação estrutural automática.

## O que foi corrigido antes da auditoria

Nada.

## O que ficou apenas documentado nesta fase

- Divergências documentais entre código real e texto legado.
- Fragilidades não bloqueadoras a validar e classificar na auditoria ultra.

## Decisão de avanço

Sem gaps bloqueadores na cobertura obrigatória, a auditoria ultra completa pode avançar a partir do código real atual.
