# AUDIT REPORT ULTRA

Data: 2026-03-25  
Repositório: `gcodeteric/morning-brief`

## 1. Veredito Geral

Estado final: **PRONTO COM RESSALVAS**

Resumo executivo:
- A cobertura editorial e operacional pedida na Fase 0 está presente no código real.
- Não foi necessário patch pré-auditoria para fechar cobertura obrigatória.
- O pipeline real continua a gerar o brief em `--dry-run` e em execução normal controlada.
- Foi encontrada **1 falha funcional real** com impacto material: `curator.py` não tolera artigos incompletos e pode abortar a curadoria com `KeyError`.
- Foram encontradas **fragilidades operacionais e divergências documentais** que não quebram o brief, mas prejudicam observabilidade e manutenção.

## 2. Cobertura Obrigatória

Referência base: [PRE_AUDIT_COVERAGE_REPORT.md](/C:/Users/berna/Desktop/Simula_Project/morning-brief/PRE_AUDIT_COVERAGE_REPORT.md)

### Matriz final

| ID | Item | Estado final | Evidência |
|---|---|---|---|
| A1 | Instagram prompt/editorial pack | IMPLEMENTADO | [formatter.py:339](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L339), [agents.py:70](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py#L70) |
| A2 | Carrossel editorial por defeito | IMPLEMENTADO | [formatter.py:377](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L377) |
| A3 | `cover_hook/slides/caption/community_question/notes_for_design` | IMPLEMENTADO | [agents.py:70](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py#L70) |
| A4 | `instagram_pack` aparece no brief | IMPLEMENTADO | [formatter.py:610](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L610) |
| A5 | X/Twitter threads | IMPLEMENTADO | [formatter.py:393](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L393) |
| A6 | Link só no tweet final | IMPLEMENTADO | [formatter.py:411](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L411) |
| A7 | Estrutura coerente por thread | IMPLEMENTADO | [formatter.py:411](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L411) |
| A8 | YouTube Short diário | IMPLEMENTADO | [formatter.py:426](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L426) |
| A9 | YouTube Weekly só ao domingo | IMPLEMENTADO | [formatter.py:456](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L456) |
| A10 | Weekly documentado | IMPLEMENTADO | [planner.py:260](/C:/Users/berna/Desktop/Simula_Project/morning-brief/planner.py#L260), [formatter.py:463](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L463) |
| A11 | Reddit 1–3 posts | IMPLEMENTADO | [formatter.py:499](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L499) |
| A12 | Reddit exclui shorts/promo/fraco | IMPLEMENTADO | [planner.py:54](/C:/Users/berna/Desktop/Simula_Project/morning-brief/planner.py#L54) |
| A13 | Discord output | IMPLEMENTADO | [formatter.py:530](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L530) |
| A14 | Discord silêncio explícito | IMPLEMENTADO | [formatter.py:556](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L556) |
| B15 | `agent_outputs` em `curated` | IMPLEMENTADO | [main.py:164](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L164) |
| B16 | `analysis` | IMPLEMENTADO | [agents.py:263](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py#L263) |
| B17 | `post` | IMPLEMENTADO | [agents.py:264](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py#L264) |
| B18 | `image_prompt` | IMPLEMENTADO | [agents.py:266](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py#L266) |
| B19 | `voice_script` | IMPLEMENTADO | [agents.py:267](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py#L267) |
| B20 | `qa` | IMPLEMENTADO | [agents.py:268](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py#L268) |
| B21 | `instagram_pack` | IMPLEMENTADO | [agents.py:265](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py#L265) |
| C22 | Alternativas por canal | IMPLEMENTADO | [planner.py:298](/C:/Users/berna/Desktop/Simula_Project/morning-brief/planner.py#L298), [formatter.py:254](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L254) |
| C23 | `manual_overrides.json` opcional | IMPLEMENTADO | [manual_overrides.py:12](/C:/Users/berna/Desktop/Simula_Project/morning-brief/manual_overrides.py#L12) |
| C24 | Launcher para overrides | IMPLEMENTADO | [abrir_overrides_json.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/abrir_overrides_json.bat) |
| C25 | Brief usa seleção final | IMPLEMENTADO | [main.py:176](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L176), [main.py:198](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L198) |
| C26 | Email usa seleção final | IMPLEMENTADO | [main.py:242](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L242) |
| C27 | Email anexa `.md` | IMPLEMENTADO | [email_digest.py:213](/C:/Users/berna/Desktop/Simula_Project/morning-brief/email_digest.py#L213), [email_digest.py:365](/C:/Users/berna/Desktop/Simula_Project/morning-brief/email_digest.py#L365) |
| C28 | Email anexa cards | IMPLEMENTADO | [email_digest.py:205](/C:/Users/berna/Desktop/Simula_Project/morning-brief/email_digest.py#L205), [email_digest.py:370](/C:/Users/berna/Desktop/Simula_Project/morning-brief/email_digest.py#L370) |

Resultado da Fase 0:
- **Sem gaps bloqueadores**
- **Sem patch pré-auditoria**
- Divergências documentais mantidas para auditoria, não para correção nesta fase

## 3. Metodologia

Inspeção real executada:
- leitura integral dos ficheiros centrais do pipeline e operacionais
- validação da cobertura obrigatória antes de auditar
- testes sintáticos, imports, integração real `dry-run`, integração controlada com diretórios temporários, testes dirigidos por módulo, probes de fragilidade

Ficheiros auditados diretamente:
- [main.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py)
- [formatter.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py)
- [planner.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/planner.py)
- [manual_overrides.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/manual_overrides.py)
- [agents.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py)
- [email_digest.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/email_digest.py)
- [card_generator.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/card_generator.py)
- [alerts.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/alerts.py)
- [scanner.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/scanner.py)
- [curator.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/curator.py)
- [config.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/config.py)
- [news_sources.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/news_sources.py)
- [feeds.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/feeds.py)
- [channel_id_extractor.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/channel_id_extractor.py)
- [feed_validator.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/feed_validator.py)
- [audit_report_generator.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/audit_report_generator.py)
- [extract_youtube_ids.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/extract_youtube_ids.py)
- [README.md](/C:/Users/berna/Desktop/Simula_Project/morning-brief/README.md)
- [abrir_overrides_json.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/abrir_overrides_json.bat)
- [data/manual_overrides.example.json](/C:/Users/berna/Desktop/Simula_Project/morning-brief/data/manual_overrides.example.json)

## 4. Testes Executados

### 4.1 Sintaxe / Imports

Resultados:
- `PASS` `py_compile` de todos os `.py` relevantes
- `PASS` imports individuais de `main`, `formatter`, `planner`, `manual_overrides`, `agents`, `email_digest`, `card_generator`, `alerts`, `scanner`, `curator`, `config`, `news_sources`, `feeds`, `channel_id_extractor`, `feed_validator`, `audit_report_generator`, `extract_youtube_ids`
- `PASS` ausência de circular imports material nos módulos centrais

### 4.2 Integração real

Comandos / execuções reais:
- `python main.py --dry-run`
- execução controlada de `main.main(dry_run=False)` com paths temporários para `brief`, `archive`, `run_summary` e `alerts`
- geração dirigida de brief com `formatter.format_brief(...)`
- geração dirigida de digest com `build_email_digest(...)`
- envio real para SMTP stub local

Evidência:

```text
Scan completo: 27 OK, 23 vazios, 0 falhas, 100 artigos
MiniMax API key não configurada — agente ignorado
   → 3 posts gerados pelo pipeline
Manual overrides: ficheiro não existe, a usar escolhas principais
DRY RUN concluído — 15 artigos seleccionados, brief NÃO guardado
=== Concluido com sucesso ===
```

Execução normal controlada em diretório temporário:

```json
{
  "brief_exists": true,
  "archive_exists": true,
  "summary_exists": true,
  "alerts_exists": true,
  "summary": {
    "feeds_total": 2,
    "feeds_ok": 2,
    "feeds_fail": 0,
    "articles_scanned": 2,
    "articles_after_dedup": 1,
    "articles_selected": 1,
    "status": "OK"
  }
}
```

SMTP stub:

```json
{
  "subject": "Simula Daily Content Pack — 25/03/2026",
  "attachments": ["brief.md", "card1.png", "card2.png"],
  "sent": true,
  "markdown_attached": true,
  "cards_attached": true,
  "uses_final_pick": true
}
```

### 4.3 Resultados por bloco

| Bloco | Resultado |
|---|---|
| Planner | PASS |
| Formatter | PASS |
| Manual overrides | PASS |
| Agents | PASS |
| Email digest | PASS |
| Cards | PASS |
| Alerts | PASS |
| Scanner básico | PASS |
| Curator básico | PASS |
| Curator com artigos incompletos | **FAIL** |
| Main `dry-run` real | PASS |
| Main normal controlado | PASS |

### 4.4 Testes dirigidos executados

Passaram:
- `planner.empty`
- `planner.single_category_fallback`
- `planner.one_article_no_dup`
- `planner.all_shorts_no_yt_daily`
- `planner.discord_threshold`
- `planner.reddit_promo_filter`
- `planner.sunday_weekly`
- `formatter.plan_none`
- `formatter.instagram_pack_and_overrides`
- `formatter.incomplete_article`
- `formatter.agent_outputs_empty`
- `formatter.discord_silence`
- `formatter.sunday_vs_nonday`
- `manual_overrides.absent`
- `manual_overrides.invalid_json`
- `manual_overrides.resolve_0`
- `manual_overrides.resolve_1`
- `manual_overrides.resolve_2`
- `manual_overrides.fallback_when_missing_alt`
- `main.manual_overrides_valid_applied`
- `main.manual_overrides_invalid_survives`
- `main.email_invalid_survives`
- `main.empty_selected`
- `main.one_article`
- `pipeline.full_mock`
- `agents.valid_json_contract`
- `agents.invalid_copywriter_json_fallback`
- `agents.qa_improved_post_fallback`
- `email_digest.build`
- `email_digest.invalid_smtp_silent`
- `email_digest.smtp_stub`
- `cards.valid_assets`
- `cards.rgb_watermark`
- `cards.rgba_watermark`
- `cards.missing_assets_noncritical`
- `cards.no_pillow_fallback`
- `alerts.create`
- `alerts.remove_stale`
- `curator.basic_pipeline`
- `curator.cross_day_title_dedup`
- `scanner.mocked_scan`

Falhou:
- `curator.incomplete_article` → `KeyError: 'link'`

Probe adicional:
- `news_sources.missing_praw_probe` confirmou que a ausência de `praw` impede o import do módulo inteiro

## 5. Saúde Técnica do Pipeline

### Estado técnico

- O pipeline central continua funcional com `scan -> curate -> planner -> formatter`.
- `manual_overrides` é opcional e não quebra o run quando ausente ou inválido.
- `agent_outputs` é sempre injectado em `curated`, e o brief ignora blocos vazios.
- `email_digest` usa a seleção final resolvida e falha silenciosamente quando SMTP está incompleto.
- `alerts` funciona e limpa ficheiro stale quando não há alertas.
- `cards` comportam-se de forma não crítica com/sem assets e com/sem Pillow.

### Estado editorial

- Instagram está no estado mais rico do sistema: prompt editorial, pack estruturado, alternativas por canal e exposição do `instagram_pack` no brief.
- X/Twitter, YouTube, Reddit e Discord mantêm prompts coerentes e compatíveis com o pipeline actual.
- YouTube Weekly usa memória semanal real via `weekly_cache.json`, não proxy diário.

## 6. Falhas e Fragilidades

### ALTO

#### 6.1 `curator.py` não tolera artigos incompletos e pode abortar a curadoria inteira

Localização:
- [curator.py:219](/C:/Users/berna/Desktop/Simula_Project/morning-brief/curator.py#L219)
- [curator.py:403](/C:/Users/berna/Desktop/Simula_Project/morning-brief/curator.py#L403)
- [curator.py:420](/C:/Users/berna/Desktop/Simula_Project/morning-brief/curator.py#L420)
- [curator.py:439](/C:/Users/berna/Desktop/Simula_Project/morning-brief/curator.py#L439)
- [curator.py:506](/C:/Users/berna/Desktop/Simula_Project/morning-brief/curator.py#L506)
- [curator.py:572](/C:/Users/berna/Desktop/Simula_Project/morning-brief/curator.py#L572)

Evidência real:
- teste dirigido `curator.incomplete_article`
- input mínimo: `{'title': 'Incomplete only'}`
- resultado: `KeyError: 'link'`

O que acontece:
- a curadoria assume `priority`, `link`, `title`, `source` e `category` por indexação directa
- um único artigo malformado pode abortar toda a curadoria

O que era esperado:
- descartar ou normalizar entradas incompletas de forma silenciosa, sem impedir o brief

Impacto:
- uma entrada parcialmente corrompida vinda de API/feed/harness pode parar a geração do brief

### MÉDIO

#### 6.2 O passo 2.5 comunica sucesso mesmo quando o pipeline MiniMax não gerou nada

Localização:
- [main.py:151](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L151)
- [main.py:159](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L159)
- [main.py:161](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L161)
- [agents.py:196](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py#L196)

Evidência real:

```text
MiniMax API key não configurada — agente ignorado
MiniMax API key não configurada — agente ignorado
...
   → 3 posts gerados pelo pipeline
```

O que acontece:
- `run_full_pipeline()` devolve dicts vazios de conteúdo quando a key não existe
- `main.py` conta esses dicts como “posts gerados” e faz log `✓` por artigo

O que era esperado:
- logar que houve `0 outputs úteis` ou `pipeline indisponível`, em vez de sugerir sucesso editorial

Impacto:
- observabilidade enganadora
- o operador pode pensar que os posts/QA/image/voice foram gerados quando não foram

### BAIXO

#### 6.3 `news_sources.py` acopla Reddit a todas as fontes API no import do módulo

Localização:
- [news_sources.py:7](/C:/Users/berna/Desktop/Simula_Project/morning-brief/news_sources.py#L7)
- [news_sources.py:10](/C:/Users/berna/Desktop/Simula_Project/morning-brief/news_sources.py#L10)
- [scanner.py:178](/C:/Users/berna/Desktop/Simula_Project/morning-brief/scanner.py#L178)

Evidência real:

```json
{"status": "FAILS_AT_IMPORT", "error": "ImportError", "detail": "simulated missing praw"}
```

O que acontece:
- `praw` é importado no topo de `news_sources.py`
- se `praw` faltar, o módulo inteiro falha a importar
- isso desativa também NewsAPI e GNews, apesar de não dependerem de Reddit

O que era esperado:
- import lazy de `praw` dentro de `fetch_reddit_simracing()`

Impacto:
- blast radius desnecessário numa dependência opcional

#### 6.4 O log `Scan completo` não inclui a augmentação posterior por APIs

Localização:
- [scanner.py:174](/C:/Users/berna/Desktop/Simula_Project/morning-brief/scanner.py#L174)
- [scanner.py:178](/C:/Users/berna/Desktop/Simula_Project/morning-brief/scanner.py#L178)

O que acontece:
- o scanner fecha o sumário de RSS antes de anexar NewsAPI/GNews/Reddit
- quando as APIs estão activas, a contagem do log pode divergir do total final retornado

Impacto:
- ruído operacional e leitura difícil do run

### NOTA / DIVERGÊNCIA

#### 6.5 Documentação ainda descreve o estado antigo de 5 prompts e do passo de formatting

Localização:
- [formatter.py:2](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L2)
- [formatter.py:185](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py#L185)
- [README.md:11](/C:/Users/berna/Desktop/Simula_Project/morning-brief/README.md#L11)
- [README.md:68](/C:/Users/berna/Desktop/Simula_Project/morning-brief/README.md#L68)

Divergência:
- o código real gera **6 prompts**
- o pipeline real usa **Passo 3: Planning** e **Passo 4: Formatting**
- o texto legado ainda fala em **5 prompts** e **Passo 3: Formatting**

Impacto:
- onboarding/documentação ligeiramente desalinhados com o produto real

## 7. Robustez Operacional

O que ficou confirmado:
- `locking` preservado em [main.py:23](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L23)
- `archive` preservado em [main.py:201](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L201)
- `run_summary` preservado em [main.py:206](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L206)
- `dry-run` preservado em [main.py:267](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py#L267)
- `selected_by_category` continua a sair em `run_summary`
- `manual_overrides` é aplicado antes de `formatter` e antes de `email_digest`
- `agent_outputs` não quebra o brief quando vazio
- `cards` e `email` continuam não críticos
- `alerts` não rebenta o pipeline

## 8. Recomendações Priorizadas

1. **Endurecer `curator.py` contra artigos incompletos**  
   Aplicar defaults ou descarte defensivo antes de `_score_article()` e das três camadas de dedup. Este é o único bug com capacidade real de abortar a curadoria.

2. **Corrigir a observabilidade do passo 2.5 em `main.py`**  
   Contar apenas outputs úteis do agent pipeline, ou marcar explicitamente `pipeline indisponível` quando a key não está configurada.

3. **Desacoplar `praw` do import global de `news_sources.py`**  
   Mover o import de `praw` para dentro de `fetch_reddit_simracing()` para não matar NewsAPI/GNews quando Reddit falha por dependência.

4. **Alinhar `scanner.py` com o total final retornado**  
   Reemitir um sumário final após anexar fontes API, ou renomear o log actual para `Scan RSS completo`.

5. **Actualizar documentação e docstrings legadas**  
   Corrigir `5 prompts` / `Passo 3: Formatting` em [README.md](/C:/Users/berna/Desktop/Simula_Project/morning-brief/README.md) e [formatter.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py).

## 9. Estado Final

Conclusão final:
- **Cobertura obrigatória**: completa
- **Saúde do pipeline principal**: boa
- **Saúde editorial**: boa, especialmente Instagram
- **Saúde operacional**: boa com ressalvas de observabilidade
- **Bloqueadores absolutos para uso interno**: nenhum
- **Risco que merece fix prioritário**: tolerância a artigos incompletos no `curator`

Veredito:
- **PRONTO COM RESSALVAS**

As ressalvas são reais e reproduzidas, mas não invalidam o funcionamento global actual do sistema quando os inputs normais do scanner/feeds estão saudáveis.
