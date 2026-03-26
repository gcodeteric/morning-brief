# SimulaNewsMachine

Windows-first content pipeline for Simula Project. It scans sim racing and related sources, curates a daily shortlist, plans channel selections, applies optional overrides, generates a Markdown brief, and optionally enriches the run with MiniMax outputs, cards, email delivery, and a Streamlit dashboard.

## What it does

Current pipeline in [main.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py):

1. Scans RSS feeds plus optional API supplements.
2. Curates and scores stories, then selects a top 15.
3. Runs an optional MiniMax article pipeline on the top 3 stories.
4. Builds the editorial plan.
5. Applies optional manual overrides.
6. Runs an optional Instagram digest agent pipeline for morning and afternoon digests.
7. Formats the final brief to the Desktop.
8. Optionally generates cards.
9. Optionally sends an email digest.
10. Persists run summary and latest dashboard snapshot on normal runs.

Failure model:

- scanning, curation, planning, and brief generation are core
- agents, cards, API supplements, email, alerts, and dashboard snapshot are optional
- optional failures should degrade gracefully and must not stop the brief from being generated

## Current output model

Core outputs today:

- Daily Markdown brief at `~/Desktop/SIMULA_BRIEF_HOJE.md`
- Archived copy in `archive/`
- Run summary in `data/run_summary.json`
- Latest dashboard snapshot in `data/dashboard_latest_snapshot.json` on normal successful runs

Editorial outputs:

- Instagram Morning Digest
  - grouped carousel for `sim_racing`, `nostalgia`, `racing_games`, and PT-related stories when available
- Instagram Afternoon Digest
  - grouped carousel for `motorsport`
- X / Twitter operational prompts
- YouTube daily prompt
- YouTube weekly prompt on Sundays only
- Reddit candidate block
- Discord post block or explicit silence

Optional agent outputs:

- article-level `agent_outputs` for the top 3 selected stories
- structured Instagram digest packs for morning and afternoon
- `image_prompt`
- `voice_script`
- `qa`

Optional delivery outputs:

- social cards in `~/Desktop/SIMULA_CARDS_HOJE`
- mobile-friendly email digest using the final resolved selection

## Project structure

Main runtime modules:

- [main.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/main.py): orchestration, logging, optional delivery, snapshot write
- [scanner.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/scanner.py): RSS scan plus optional API supplementation hook
- [curator.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/curator.py): normalization, filtering, dedup, scoring, top 15 selection
- [planner.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/planner.py): channel planning, digest grouping, alternatives, weekly YouTube memory
- [manual_overrides.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/manual_overrides.py): loads and applies optional override choices
- [formatter.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/formatter.py): final brief rendering and operator prompts
- [agents.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py): MiniMax agent flows for article outputs and Instagram digests
- [email_digest.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/email_digest.py): builds and optionally sends the email digest
- [card_generator.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/card_generator.py): local social card generation with safe fallback
- [news_sources.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/news_sources.py): optional NewsAPI, GNews, and Reddit supplementation
- [config.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/config.py): central configuration and filesystem paths

Dashboard modules:

- [dashboard_app.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/dashboard_app.py): Streamlit app
- [dashboard_data.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/dashboard_data.py): centralized dashboard data layer
- [dashboard_components.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/dashboard_components.py): UI helpers and copy UX helpers
- [dashboard_overrides.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/dashboard_overrides.py): safe override helpers for the dashboard

Supporting files:

- [feeds.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/feeds.py): feed registry and optional YouTube feed expansion
- [setup_scheduler.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/setup_scheduler.bat): Windows scheduled-task helper
- [INICIAR_DASHBOARD.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/INICIAR_DASHBOARD.bat): one-click dashboard launcher
- [SIMULA_CONTROL_CENTER.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/SIMULA_CONTROL_CENTER.bat): Windows control-center launcher
- [launch_dashboard.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/launch_dashboard.py): readiness-aware dashboard startup helper
- [data/manual_overrides.example.json](/C:/Users/berna/Desktop/Simula_Project/morning-brief/data/manual_overrides.example.json): neutral override example
- [PROMPT_MAP.md](/C:/Users/berna/Desktop/Simula_Project/morning-brief/PROMPT_MAP.md): where prompts and generated fields live
- [DASHBOARD_DATA_ARCHITECTURE.md](/C:/Users/berna/Desktop/Simula_Project/morning-brief/DASHBOARD_DATA_ARCHITECTURE.md): dashboard snapshot/data layer overview

## Daily workflow

Typical operator flow today:

1. Double-click [INICIAR_DASHBOARD.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/INICIAR_DASHBOARD.bat) to open the dashboard with a readiness check.
2. If you need to run the pipeline first, use [SIMULA_CONTROL_CENTER.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/SIMULA_CONTROL_CENTER.bat) and choose `Run pipeline + open dashboard`.
3. Work from the dashboard first:
   - Instagram Morning Digest
   - Instagram Afternoon Digest
   - X
   - YouTube
   - Reddit
   - Discord
4. If agents are configured, review structured digest packs, image prompts, voice scripts, and QA.
5. If needed, adjust `data/manual_overrides.json` from the dashboard or the control center.
6. Open the latest brief on the Desktop when you need the full Markdown artifact.
7. If email digest is enabled, use the mobile-friendly delivery as a secondary operating surface.

## Dashboard

The internal Streamlit dashboard is an operational layer on top of the CLI pipeline. It does not replace the main run flow.

What it provides:

- latest run status and freshness state
- curated story browser with direct links
- Morning / Afternoon Instagram digest control
- agent outputs, image prompts, voice scripts, QA, cards, and brief access
- guided override editing and preview

Launch options:

- Windows one-click: [INICIAR_DASHBOARD.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/INICIAR_DASHBOARD.bat)
- Windows control center: [SIMULA_CONTROL_CENTER.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/SIMULA_CONTROL_CENTER.bat)
- CLI:

```bash
python -m streamlit run dashboard_app.py
```

The launcher helper [launch_dashboard.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/launch_dashboard.py) waits for the dashboard URL to respond before opening the browser.

Dashboard data model:

- prefers `data/dashboard_latest_snapshot.json`
- falls back to `run_summary.json`, brief file, overrides, and cards when the snapshot is missing
- dry runs do not refresh the snapshot on purpose

## Quick Launch

Windows-first launcher entry points:

- [INICIAR_DASHBOARD.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/INICIAR_DASHBOARD.bat)
  - starts the dashboard
  - waits until the local Streamlit endpoint is reachable
  - opens the browser only after readiness succeeds
- [SIMULA_CONTROL_CENTER.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/SIMULA_CONTROL_CENTER.bat)
  - opens the operator menu
  - `1. Run pipeline + open dashboard`
  - `2. Open dashboard only`
  - `3. Open manual overrides file`
  - `4. Open latest brief folder`
  - `5. Open cards folder`
  - `6. Exit`

These launchers are a Windows convenience layer. They respect the current project configuration rather than bypassing it.

## Manual overrides

Overrides are optional and live at:

- `data/manual_overrides.json`

Recommended current format:

```json
{
  "instagram_morning_digest": 0,
  "instagram_afternoon_digest": 0,
  "youtube_daily": 0,
  "discord_post": 0
}
```

Meaning:

- `0` = primary selection
- `1` = alternative 1
- `2` = alternative 2

Current Instagram override model is digest-based:

- `instagram_morning_digest`
- `instagram_afternoon_digest`

Legacy single-story Instagram keys are still supported for compatibility where relevant:

- `instagram_sim_racing`
- `instagram_motorsport`

If the file does not exist, the system uses planner primaries. Dashboard-created override files are neutral by default and do not silently activate alternatives.

## Installation

Real setup steps that still match the repository:

1. Install Python 3.11+.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optional but useful one-time steps:

```bash
python channel_id_extractor.py
python feed_validator.py
```

Notes:

- the repository already includes 50 static feeds in [feeds.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/feeds.py)
- `channel_id_extractor.py` can append more YouTube-derived feeds into `data/extracted_channel_ids.json`
- some feeds may fail or be empty on a given day without breaking the system

Optional environment variables:

- `MINIMAX_API_KEY`
- `MINIMAX_TIMEOUT_SECONDS`
- `NEWSAPI_KEY`
- `GNEWS_KEY`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`

## Running the system

Normal run:

```bash
python main.py
```

Dry run:

```bash
python main.py --dry-run
```

Dry-run behavior:

- exercises the pipeline without writing the brief, archive copy, run summary, seen-links state, cards, or snapshot
- still logs the real planning and optional agent fallback behavior

Windows scheduler helper:

- double-click [setup_scheduler.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/setup_scheduler.bat)
- it creates a daily scheduled task for `python main.py` at `05:00`

Windows launchers:

- [INICIAR_DASHBOARD.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/INICIAR_DASHBOARD.bat)
  - starts the dashboard and opens the browser only after readiness succeeds
- [SIMULA_CONTROL_CENTER.bat](/C:/Users/berna/Desktop/Simula_Project/morning-brief/SIMULA_CONTROL_CENTER.bat)
  - operator menu for pipeline, dashboard, overrides, brief folder, and cards folder

## Tests

The repository contains executable `unittest` coverage in `tests/` for critical behavior, including:

- planner
- manual overrides
- dashboard overrides
- agents
- formatter
- dashboard data layer
- email digest
- dashboard launcher helper
- CLI summary wording

Run all tests:

```bash
python -m unittest discover -s tests -v
```

Useful validation command for a non-writing end-to-end check:

```bash
python main.py --dry-run
```

## Optional features

MiniMax agents:

- configured via `MINIMAX_API_KEY`
- explicit timeout support is in [agents.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/agents.py)
- failure is non-critical and should fall back safely

Cards:

- controlled by `GENERATE_IMAGES` in [config.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/config.py)
- require Pillow plus assets in `assets/`
- current digest support in [card_generator.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/card_generator.py) is intentionally minimal and safe

Email digest:

- controlled by SMTP settings in [config.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/config.py)
- uses the final resolved selection after planner plus overrides
- can attach the Markdown brief and generated cards

API news supplementation:

- lives in [news_sources.py](/C:/Users/berna/Desktop/Simula_Project/morning-brief/news_sources.py)
- adds low-priority stories on top of RSS feeds
- disabled unless the relevant API credentials exist

Dashboard convenience layer:

- optional
- safe if snapshot or optional outputs are missing
- strongest when run from a normal successful pipeline execution

## Prompt and output discoverability

For maintainers and LLM-assisted changes:

- use [PROMPT_MAP.md](/C:/Users/berna/Desktop/Simula_Project/morning-brief/PROMPT_MAP.md) for prompt locations and output field names
- use [DASHBOARD_DATA_ARCHITECTURE.md](/C:/Users/berna/Desktop/Simula_Project/morning-brief/DASHBOARD_DATA_ARCHITECTURE.md) for snapshot and fallback behavior

High-level boundaries:

- scanner / curator / planner define content selection
- manual overrides only choose among persisted variants
- agents enrich content but are optional
- formatter owns the brief and channel prompt rendering
- dashboard reads latest persisted state and should not redefine editorial logic

## Current limitations

- MiniMax outputs cannot be fully validated without a configured API key.
- Dashboard fallback mode is intentionally partial if the latest structured snapshot is missing.
- Digest card generation is still cover-level compatibility, not a full carousel design system.
- The repository contains historical audit/context Markdown files; treat the code and this README as the source of truth when they diverge.
