# SimulaNewsMachine — Project Context

## 1. Project Purpose

SimulaNewsMachine is a Windows-first content operations pipeline for Simula Project. Its job is to turn a noisy stream of sim racing, motorsport, hardware, racing game, nostalgia, and Portugal-relevant news into a daily operational pack that an operator can use quickly.

In practice, the system is built to:

- scan multiple sources every day
- deduplicate and score stories
- select a curated top 15
- plan channel-specific outputs
- optionally enrich the selection with MiniMax-generated assets
- produce a Markdown brief for daily execution
- optionally generate social cards and an email digest
- expose the latest run through a Streamlit dashboard

The brief is the primary output. Everything else exists to enrich, deliver, or inspect the same underlying daily selection.

## 2. Current Real Scope

### Core pipeline

The critical path is:

- scan sources
- curate and score stories
- plan channel selections
- apply manual overrides if present
- format the daily brief

This path must keep working even if optional systems fail.

### Optional subsystems

Optional subsystems currently implemented:

- MiniMax article-level agent pipeline
- MiniMax Instagram digest agent pipeline
- API news supplementation via NewsAPI, GNews, and Reddit
- social card generation with Pillow
- email digest delivery via SMTP
- dashboard latest-run snapshot persistence
- alerts

All of these are designed as non-critical layers. Failure should be logged and should not prevent brief generation.

### Operator-facing tools

Operator-facing surfaces currently in the repo:

- the Markdown brief on the Desktop
- the Streamlit dashboard
- Windows batch launchers for dashboard/control-center usage
- optional email digest for mobile use
- manual overrides file

## 3. End-to-End Pipeline

The real execution order in `main.py` is:

1. `scanner.scan_all_feeds()`
2. `curator.curate_articles(raw_articles)`
3. optional top-3 article agent enrichment through `agents.run_full_pipeline(...)`
4. `planner.plan(curated)`
5. optional `manual_overrides.load_manual_overrides()` + `apply_manual_overrides(...)`
6. optional Instagram digest enrichment through `agents.run_instagram_digest_pipeline(...)`
7. optional `card_generator.generate_instagram_cards(plan)`
8. `formatter.format_brief(curated, OUTPUT_FILE, plan=..., card_paths=...)`
9. archive the brief
10. write `data/run_summary.json`
11. write `data/dashboard_latest_snapshot.json`
12. optional alerts
13. optional email digest build and send

Important behavior:

- dry runs execute the pipeline but intentionally skip state-writing outputs such as brief, archive, seen-links, cards, and dashboard snapshot
- the planner and formatter remain the backbone of the operator workflow even when all agent features are disabled

## 4. Core Modules and Responsibilities

### `main.py`

Responsibility:

- top-level orchestration
- logging setup
- lock-file handling
- normal vs dry-run behavior
- optional subsystem sequencing
- runtime summary persistence

Consumes:

- all core modules
- config flags

Produces:

- brief
- archive copy
- run summary
- dashboard snapshot
- optional cards
- optional email send

Criticality:

- critical

### `scanner.py`

Responsibility:

- read all configured feeds
- apply time-window filtering
- normalize raw entries into article dicts
- optionally supplement with API-based stories

Consumes:

- feed definitions from `feeds.py`
- timeout settings from `config.py`
- optional API layer in `news_sources.py`

Produces:

- raw article list
- scan stats

Criticality:

- critical

### `curator.py`

Responsibility:

- normalize incomplete stories
- filter noisy/low-value content
- deduplicate by URL, title similarity, and seen-links history
- score stories
- enforce category/source constraints
- return the selected top 15

Consumes:

- raw article list from scanner
- seen-links history
- curation/scoring constants from `config.py`

Produces:

- curated output dict with selected stories and metadata

Criticality:

- critical

### `planner.py`

Responsibility:

- map curated stories to channel selections
- build Morning / Afternoon Instagram digests
- build digest alternatives
- choose X, YouTube, Reddit, and Discord slots
- maintain weekly YouTube memory cache

Consumes:

- curated output
- weekly cache file

Produces:

- plan dict used by overrides, formatter, email digest, cards, snapshot, and dashboard

Criticality:

- critical

### `manual_overrides.py`

Responsibility:

- load optional persisted override integers
- resolve primary vs alternative selections
- annotate plan with `manual_overrides_applied` and `override_summary`

Consumes:

- planner output
- `data/manual_overrides.json`

Produces:

- updated plan dict

Criticality:

- optional but operationally important

### `formatter.py`

Responsibility:

- render the final Markdown brief
- render planner selections and alternatives
- render Instagram digest outputs when available
- render prompt blocks for Instagram, X, YouTube, Reddit, and Discord
- render article-level MiniMax output section when useful output exists

Consumes:

- curated output
- resolved plan
- optional card paths

Produces:

- `SIMULA_BRIEF_HOJE.md`

Criticality:

- critical

### `agents.py`

Responsibility:

- define prompt contracts for article and digest agent flows
- call the OpenAI-compatible MiniMax endpoint
- parse structured JSON outputs
- convert structured Instagram packs into readable text fallbacks
- collect agent timing and failure metrics

Consumes:

- article or digest input summary
- `MINIMAX_API_KEY`
- `MINIMAX_TIMEOUT_SECONDS`

Produces:

- article-level output dicts with `analysis`, `post`, `instagram_pack`, `image_prompt`, `voice_script`, `qa`, `agent_metrics`
- digest-level output dicts with similar fields plus `digest_type`

Criticality:

- optional

### `email_digest.py`

Responsibility:

- build a mobile-friendly text and HTML email from the final resolved plan
- attach the Markdown brief when available
- optionally attach generated cards
- send via SMTP if configuration is complete

Consumes:

- curated output
- resolved plan
- brief path
- optional card paths
- SMTP config

Produces:

- email digest payload dict
- optional SMTP send side effect

Criticality:

- optional

### `card_generator.py`

Responsibility:

- generate local PNG social cards using Pillow and local assets
- fall back safely if Pillow or assets are missing
- provide minimal safe cover support for Instagram digests

Consumes:

- resolved plan
- assets in `assets/`

Produces:

- card path mapping, typically under `~/Desktop/SIMULA_CARDS_HOJE`

Criticality:

- optional

### `dashboard_app.py`

Responsibility:

- Streamlit operator UI
- run overview
- story browsing
- Morning / Afternoon digest control
- brief inspection
- prompt/script/QA inspection
- guided override editing

Consumes:

- normalized dashboard context from `dashboard_data.py`
- override helpers from `dashboard_overrides.py`

Produces:

- no critical pipeline data
- user interactions over latest persisted state

Criticality:

- optional

### `dashboard_data.py`

Responsibility:

- centralized dashboard data access layer
- snapshot load/save
- fallback loading from run summary, brief, overrides, and cards
- normalization of stories, outputs, digests, and runtime context
- selection summary export

Consumes:

- snapshot
- run summary
- brief
- overrides
- cards folder
- config paths

Produces:

- dashboard context dict
- dashboard snapshot file

Criticality:

- optional, but critical to dashboard reliability

### `news_sources.py`

Responsibility:

- low-priority API-based supplements for the scanner
- NewsAPI, GNews, and Reddit integration

Consumes:

- API credentials from environment

Produces:

- additional article dicts compatible with curation

Criticality:

- optional

## 5. Data Contracts / Key Runtime Structures

The project relies heavily on Python dict contracts shared across modules. These are not strict typed schemas, so compatibility depends on preserving the expected keys and fallback behavior.

### Curated output

Practical shape returned by `curator.curate_articles(...)`:

- `selected`: list of normalized article dicts
- `total_before_dedup`
- `total_after_dedup`
- `categories`
- later in `main.py`, `agent_outputs` is attached to this dict

Article dicts are expected to expose, when possible:

- `title`
- `summary`
- `link`
- `source`
- `category`
- `priority`
- `score`
- `published`
- `no_date`

### Planner output

The plan dict is a central shared contract. It includes, at minimum:

- `instagram_morning_digest`
- `instagram_morning_digest_alternatives`
- `instagram_afternoon_digest`
- `instagram_afternoon_digest_alternatives`
- legacy compatibility fields such as `instagram_sim_racing` and `instagram_motorsport`
- `x_thread_1`
- `x_thread_2`
- `youtube_daily`
- `youtube_daily_alternatives`
- `youtube_weekly`
- `reddit_candidates`
- `discord_post`
- `discord_post_alternatives`
- `is_sunday`

Later stages may add:

- `manual_overrides_applied`
- `override_summary`
- `instagram_morning_output`
- `instagram_morning_pack`
- `instagram_afternoon_output`
- `instagram_afternoon_pack`

### Override structure

Overrides are integer variant selectors, not arbitrary content replacements.

Typical current structure:

```json
{
  "instagram_morning_digest": 0,
  "instagram_afternoon_digest": 1,
  "youtube_daily": 0,
  "discord_post": 0
}
```

Resolution rules:

- `0` means primary
- `1` means alternative 1 if present, otherwise primary
- `2` means alternative 2 if present, otherwise primary
- invalid values fall back to primary

### Agent outputs

Article-level `run_full_pipeline(...)` returns a dict with:

- `article`
- `analysis`
- `post`
- `instagram_pack`
- `image_prompt`
- `voice_script`
- `qa`
- `raw_post`
- `agent_metrics`

Digest-level `run_instagram_digest_pipeline(...)` returns a similar dict with:

- `digest_type`
- `articles`
- `analysis`
- `post`
- `instagram_pack`
- `image_prompt`
- `voice_script`
- `qa`
- `raw_post`
- `agent_metrics`

### Instagram digest pack

Current practical structured digest pack fields:

- `format`
- `cover_hook`
- `digest_theme`
- `slides`
  - typically list of dicts with `news_title`, `mini_summary`, `why_it_matters`
- `caption_intro`
- `caption_news_list`
- `community_question`
- `cta_style`
- `notes_for_design`

These packs are consumed by:

- `formatter.py`
- `email_digest.py`
- `card_generator.py` in minimal cover mode
- `dashboard_app.py`

### Email digest payload

`build_email_digest(...)` returns a dict including:

- `subject`
- `text_body`
- `html_body`
- `attachments`
- `markdown_attachment`
- `card_attachments`

`send_email_digest(...)` consumes that payload plus SMTP config and returns a boolean.

### Dashboard snapshot and context

The latest-run snapshot stored in `data/dashboard_latest_snapshot.json` is a lightweight structured state bundle for the dashboard.

Practical contents include:

- timestamp and status metadata
- curated stories
- plan
- agent outputs
- digest packs
- card paths
- brief path
- override summary
- run summary

`dashboard_data.build_dashboard_context()` then normalizes this into a UI-facing dict with stable top-level sections such as:

- `status`
- `brief`
- `overrides`
- `instagram`
- `channels`
- `cards`
- `paths`
- `freshness`
- `agent_runtime`
- backward-compatible `snapshot` / `run_summary` / `runtime`

## 6. Current Instagram Model

Instagram is no longer modeled as “one story = one post”.

### Morning Digest

The morning digest is a grouped editorial carousel intended to cover the Simula ecosystem:

- `sim_racing`
- `nostalgia`
- `racing_games`
- PT / Portugal-related stories when available

The planner tries to build a varied but coherent set, typically targeting 5 to 7 stories, with 4 as the practical minimum before the digest becomes thin.

### Afternoon Digest

The afternoon digest is motorsport-only and is allowed to be more homogeneous.

### Alternatives

Each digest has up to two alternatives:

- `instagram_morning_digest_alternatives`
- `instagram_afternoon_digest_alternatives`

Overrides only switch between these persisted variants. They do not persist custom story-level rearrangements.

### Agent-generated digest packs

If MiniMax is configured, the digest pipeline can add:

- structured digest pack
- readable digest post text
- image prompt
- voice script
- QA output

If MiniMax is not configured or fails:

- the digest selection still exists
- the brief still renders
- the dashboard still shows the selected stories

### Cards and dashboard relationship

Cards:

- digest cards are cover-level compatibility only
- they reuse digest pack fields when available
- otherwise they fall back to older article-based logic

Dashboard:

- shows Morning and Afternoon as distinct operational sections
- exposes active variant and alternatives
- shows digest pack, QA, image prompt, voice script, card path, and story links
- supports session-only preview edits of story order/add/remove, but persists only override integers

## 7. Other Channel Outputs

### X / Twitter

The planner chooses:

- `x_thread_1`
- `x_thread_2`

The brief renders explicit prompt blocks for both threads. The system does not persist fully generated X threads as a separate first-class artifact unless they happen to come through the article-level agent output path.

### YouTube

The planner chooses:

- `youtube_daily`
- `youtube_daily_alternatives`
- `youtube_weekly` on Sundays via weekly cache accumulation

The brief renders:

- a daily YouTube Short prompt
- a Sunday-only weekly YouTube prompt when `is_sunday` is true

### Reddit

The planner persists up to 3 eligible Reddit candidates based on score and eligibility filters. The brief renders an operator prompt for Reddit posting strategy.

### Discord

The planner either selects a single `discord_post` above threshold or explicitly yields silence. The brief renders the Discord prompt or an explicit “do not post” equivalent.

### Email digest

The email digest uses the final resolved selection and can include:

- Morning Digest section
- Afternoon Digest section
- other channel selections
- hashtags, image prompts, voice scripts when available
- Markdown brief attachment
- cards if configured and present

## 8. Dashboard Role

The dashboard is an internal operations console layered on top of persisted latest-run state.

### What it is for

- inspect the latest run quickly
- browse curated stories with source links
- inspect Morning and Afternoon digests
- inspect prompts, scripts, QA, cards, and brief
- adjust override integers safely
- export a selection summary

### What data it consumes

Primary source:

- `data/dashboard_latest_snapshot.json`

Fallback sources:

- `data/run_summary.json`
- latest brief
- `data/manual_overrides.json`
- cards folder

### What is persisted vs session-only

Persisted:

- manual override integers
- latest snapshot data from normal runs

Session-only in Streamlit:

- draft digest story add/remove/reorder preview
- copy-ready buffers
- current page navigation state

The dashboard explicitly warns that story-level draft edits are not written back to the pipeline state.

## 9. Persistence / Runtime Artifacts

Important real artifacts in the repository/runtime:

- `~/Desktop/SIMULA_BRIEF_HOJE.md`
- `archive/YYYY-MM-DD_brief.md`
- `data/run_summary.json`
- `data/dashboard_latest_snapshot.json`
- `data/manual_overrides.json`
- `data/manual_overrides.example.json`
- `data/seen_links.json`
- `data/weekly_cache.json`
- `data/extracted_channel_ids.json` when YouTube channel extraction is used
- `logs/YYYY-MM-DD.log`
- `~/Desktop/SIMULA_CARDS_HOJE/*.png` when cards are generated
- `data/alerts.json` when alert thresholds trigger

No database is used. Persistence is file-based.

## 10. Optional Dependencies / Graceful Degradation

### MiniMax key missing

If `MINIMAX_API_KEY` is missing:

- agent calls are skipped
- agent pipelines return safe empty/fallback outputs
- the brief still renders
- digest selection still works

### Agent timeout or parsing failure

If the agent endpoint stalls or returns invalid JSON:

- timeouts are logged
- structured parsing falls back safely
- useful outputs are tracked separately from structurally present-but-empty outputs

### Email config missing

If SMTP config is incomplete:

- email digest build still works when called
- send returns `False`
- the pipeline continues

### Card assets missing or Pillow missing

If Pillow is unavailable or assets are missing:

- card generation fails gracefully
- the rest of the run continues

### Reddit dependency missing

If `praw` is not installed:

- Reddit supplementation returns an empty list
- RSS and other API supplements still work

### Snapshot missing

If the dashboard snapshot is missing:

- the dashboard falls back to run summary, brief, overrides, and cards
- this is explicitly partial, not equivalent to a full latest-run structured state

### Dry run

Dry runs are intentionally non-writing:

- they do not refresh the dashboard snapshot
- they should not overwrite the last real operational state

## 11. Testing / Validation State

The repository currently contains executable `unittest` coverage under `tests/`.

Covered areas include:

- planner behavior
- manual overrides
- dashboard override safety
- agent JSON/fallback behavior
- formatter behavior including MiniMax section suppression
- dashboard data layer
- email digest build/send fallback
- dashboard launcher helper
- CLI summary wording

Coverage is meaningful but still partial. It focuses on critical contracts and fallback behavior rather than full exhaustive end-to-end simulation of every external dependency.

Notably, live MiniMax quality cannot be fully validated without a configured API key.

## 12. Known Risks / Limitations

- The plan dict is a shared loose contract across many modules; changes to field names or shapes can ripple widely.
- Historical Markdown docs in `Info/` may drift from code and should not be treated as the primary source of truth.
- Dashboard fallback mode is intentionally partial when snapshot data is absent.
- Dashboard story-level digest editing is preview-only and not persisted.
- Digest card generation is intentionally minimal and does not implement a full carousel asset system.
- MiniMax quality and latency still depend on external configuration and runtime conditions.
- The project is Windows-first in operator workflow and launch tooling, even though much of the Python code is otherwise portable.

## 13. Safe Modification Guidelines

This section is intentionally explicit for future maintainers and LLMs.

### Trust order

Use this trust order when sources disagree:

1. code
2. current README and current technical docs such as `PROJECT_CONTEXT.md`
3. historical audit/context markdown

### Preserve non-critical failure behavior

Do not turn optional systems into hard dependencies. If you modify:

- agents
- cards
- email
- dashboard snapshot
- API supplements

the brief path must still survive their failure.

### Preserve shared plan contracts

Be careful with the plan dict. It is consumed by:

- manual overrides
- formatter
- email digest
- card generator
- dashboard snapshot
- dashboard UI

Renaming or reshaping plan fields without coordinated updates will break operator workflows.

### Be careful with agent JSON contracts

`agents.py` depends on structured JSON for:

- article Instagram packs
- digest packs
- QA fallback

If prompt structure changes, update parsing and downstream consumers together.

### Do not silently change override semantics

Overrides currently mean “pick persisted variant 0/1/2”. They do not mean arbitrary story-level custom selection. Keep that distinction clear.

### Preserve operator-facing clarity

If you modify:

- formatter
- dashboard
- email digest

preserve direct links, explicit fallback states, and honest wording about what is actually persisted.

### Test fallback paths, not just happy paths

Useful validation after changes typically includes:

- `python -m unittest discover -s tests -v`
- `python main.py --dry-run`
- missing optional config scenarios
- missing snapshot / missing overrides / missing cards scenarios

### Prefer small compatibility-first changes

The system already has a coherent architecture. Changes should usually be:

- targeted
- backward-compatible where practical
- explicit about runtime contracts

## 14. Current Status Verdict

SimulaNewsMachine is a real, working daily content operations pipeline with a strong core flow and good graceful-degradation behavior. It is beyond prototype stage, but still depends on loose dict contracts and environment-driven optional systems. In current form, it is best described as operationally useful and structurally coherent, with optional layers that are intentionally softer than the core brief path.
