# SimulaNewsMachine — Safe Modification Guide

## 1. Purpose of This Guide

This guide explains how to modify the current SimulaNewsMachine codebase without breaking its core pipeline, graceful-degradation model, shared runtime contracts, or operator workflow.

It is written for:

- engineers maintaining the repository
- future LLMs modifying the project
- handoffs between chats, tools, or sessions

It is intentionally practical. It is not a marketing document and not a full architecture spec.

## 2. Code Is the Source of Truth

Use this trust order when sources disagree:

1. code
2. current active docs such as `README.md` and `PROJECT_CONTEXT.md`
3. older historical Markdown under `Info/` or audit-style files

This repository has evolved. Historical docs may still describe older behavior. Safe changes should always start by locating the real implementation in code before editing.

## 3. Core Architectural Safety Rules

These rules are grounded in the current codebase and should be preserved unless the architecture is intentionally redesigned.

- The core path `scanner -> curator -> planner -> formatter` must continue to produce a useful brief.
- Optional subsystems must remain optional:
  - MiniMax agent pipelines
  - API supplements
  - card generation
  - email digest sending
  - dashboard snapshot persistence
  - dashboard itself
- The brief must still be generated when optional layers fail, are disabled, or are not configured.
- Shared dict contracts must remain stable enough for downstream modules to keep working.
- Operator-facing outputs must remain readable and useful even when structured enrichments are missing.
- Dry run must remain non-writing for operational state files.
- Dashboard and launchers must not silently misrepresent state freshness or persistence.

## 4. Critical Shared Contracts

This is the most fragile part of the repository. Many modules communicate through loosely structured dicts rather than strict typed models.

### 4.1 Curated output contract

`curator.curate_articles(...)` returns a dict that is expected to contain at least:

- `selected`
- `total_before_dedup`
- `total_after_dedup`
- `categories`

Later in `main.py`, `agent_outputs` is attached to this same dict.

What depends on it:

- `main.py`
- `planner.py`
- `formatter.py`
- `email_digest.py`
- snapshot persistence in `dashboard_data.py`

What breaks if changed carelessly:

- top-story selection display
- planner inputs
- final brief structure
- dashboard story browser

### 4.2 Planner output contract

The `plan` dict is the single most important shared contract in the repo.

Current important keys include:

- `instagram_morning_digest`
- `instagram_morning_digest_alternatives`
- `instagram_afternoon_digest`
- `instagram_afternoon_digest_alternatives`
- `instagram_sim_racing`
- `instagram_motorsport`
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

What depends on it:

- `manual_overrides.py`
- `formatter.py`
- `email_digest.py`
- `card_generator.py`
- `dashboard_data.py`
- `dashboard_app.py`

What breaks if changed carelessly:

- override resolution
- digest rendering
- email digest sections
- dashboard preview/export
- card selection

### 4.3 Override contract

Overrides are integer variant selectors, not arbitrary content edits.

Current semantics:

- `0` = primary
- `1` = alternative 1
- `2` = alternative 2
- invalid or unavailable alternative -> fallback to primary

Important file paths:

- `data/manual_overrides.json`
- `data/manual_overrides.example.json`

What depends on it:

- `manual_overrides.py`
- `dashboard_overrides.py`
- `dashboard_app.py`
- `dashboard_data.py`

What breaks if changed carelessly:

- operators accidentally activating alternatives
- mismatch between UI preview and actual run behavior
- misleading saved override state

### 4.4 Agent output contract

`agents.py` returns dicts that may include:

- `analysis`
- `post`
- `instagram_pack`
- `image_prompt`
- `voice_script`
- `qa`
- `raw_post`
- `agent_metrics`

Digest pipeline also includes:

- `digest_type`
- `articles`

The structured `instagram_pack` is consumed by:

- `formatter.py`
- `email_digest.py`
- `card_generator.py`
- `dashboard_app.py`

What breaks if changed carelessly:

- readable operator output can degrade into raw JSON
- digest pack rendering disappears
- QA repair path stops working
- dashboard and email lose structured detail

### 4.5 Dashboard context contract

`dashboard_data.build_dashboard_context()` normalizes runtime state into a UI-facing dict with stable sections such as:

- `status`
- `brief`
- `overrides`
- `instagram`
- `channels`
- `cards`
- `paths`
- `freshness`
- `agent_runtime`
- compatibility keys like `snapshot`, `run_summary`, `runtime`

What depends on it:

- `dashboard_app.py`

What breaks if changed carelessly:

- Streamlit pages fail or become misleading
- freshness labels drift from actual data source
- export summary becomes inaccurate

## 5. Modules That Are Safe to Change Carefully

These areas are usually lower risk if edits stay narrow and contracts are preserved.

### `dashboard_components.py`

Usually safe for:

- visual cleanup
- copy-ready UX improvements
- clearer empty states
- section/header consistency

Still be careful not to hide warnings or remove operator-critical status signals.

### `launch_dashboard.py`

Usually safe for:

- Windows launcher hardening
- readiness flow improvements
- clearer path-opening behavior
- safe local port fallback logic

Do not let launcher changes imply that the pipeline or dashboard is healthy when startup actually failed.

### `README.md`, `PROJECT_CONTEXT.md`, `PROMPT_MAP.md`, `DASHBOARD_DATA_ARCHITECTURE.md`

Usually safe for:

- reality-alignment updates
- launcher/docs workflow clarification
- prompt discoverability

But still verify all claims against code before editing.

### Tests under `tests/`

Usually safe for:

- adding targeted regression coverage
- clarifying expected fallback behavior
- guarding shared contracts

Do not weaken tests just to make a patch pass.

## 6. Modules That Are High Risk

### `curator.py`

High risk because it controls:

- normalization of incomplete inputs
- filtering
- dedup
- scoring
- diversity guarantees
- seen-links persistence

Dangerous edits:

- changing score math casually
- changing source/category guarantees without checking editorial consequences
- changing seen-links behavior without validating cross-day dedup
- tightening filters without testing low-data days

### `planner.py`

High risk because it defines the shared `plan` contract and the whole editorial selection model.

Dangerous edits:

- renaming plan keys
- changing digest alternative shapes
- changing digest semantics without updating formatter, dashboard, email, and overrides together
- introducing duplicates or incompatible empty states

### `agents.py`

High risk because it mixes external API behavior, structured JSON contracts, readable fallbacks, and QA repair logic.

Dangerous edits:

- changing prompt schemas without updating parsers
- returning raw JSON where operator-facing text is expected
- breaking `improved_post` reparsing
- turning missing MiniMax config into a fatal error
- hiding timing/failure information that operators rely on

### `formatter.py`

High risk because it is the primary operator-facing output layer.

Dangerous edits:

- removing links or useful context
- rendering misleading empty sections
- changing fallback behavior when `plan` is missing
- breaking prompt discoverability
- breaking Instagram digest rendering

### `dashboard_data.py`

High risk because it normalizes many loose runtime structures into one context contract for the UI.

Dangerous edits:

- changing normalized keys without updating `dashboard_app.py`
- collapsing freshness states
- making snapshot absence look equivalent to full structured state
- making export summaries diverge from actual resolved variants

### `dashboard_app.py`

High risk because it is a workflow tool, not just a viewer.

Dangerous edits:

- implying session-only edits are fully persisted
- hiding fallback mode
- making source links or prompts harder to find
- scattering action buttons away from the content they affect
- losing Morning vs Afternoon separation

## 7. Failure Philosophy That Must Be Preserved

The current system uses graceful degradation on purpose. Future patches should preserve that philosophy unless the architecture is intentionally redesigned.

### MiniMax missing or failing

If `MINIMAX_API_KEY` is missing, invalid, slow, or returns bad JSON:

- the run should continue
- the brief should still be generated
- planner selections should still exist
- digest story groups should still exist
- operator-facing fallback output should remain readable

### SMTP config missing

If email settings are incomplete:

- email send should fail safely
- the rest of the pipeline should continue

### Card generation unavailable

If Pillow or assets are missing:

- card generation should fail safely
- the run should continue

### Snapshot missing

If `data/dashboard_latest_snapshot.json` is missing:

- the dashboard should fall back to run summary, brief, overrides, and cards
- that mode should stay explicitly partial

### Overrides missing or invalid

If override files do not exist or contain invalid JSON:

- planner primaries should still be used
- the run should continue

### Optional dependencies missing

If optional libraries like `praw` are missing:

- related supplementation should return empty results
- scanning should still work

## 8. Safe Rules for Editing the Agent Layer

`agents.py` is especially sensitive.

### Keep JSON contracts stable

The prompt output schemas and the parsing code are tightly coupled. If you change one, change the other in the same patch.

### Preserve the distinction between `post` and `instagram_pack`

- `instagram_pack` is the structured representation
- `post` is the human-readable operator-facing representation

Downstream tools expect both concepts to remain coherent.

### Preserve QA repair behavior

When QA returns `improved_post`:

- structured JSON should be reparsed like a normal generated pack
- readable text should be rebuilt from the structured pack
- invalid JSON should still degrade gracefully

Do not let raw JSON leak into operator-facing fields unless there is no safe alternative.

### Keep agent timing/failure visibility

Current code exposes:

- per-agent duration
- timeouts
- parse failures
- useful output signals

Do not remove this visibility without replacing it with something equally useful.

### Do not casually change prompt shape

Prompt rewrites in `agents.py` can silently break:

- `formatter.py`
- `email_digest.py`
- `dashboard_app.py`
- `card_generator.py`

If prompt shape must change, update tests and downstream consumers together.

## 9. Safe Rules for Editing Instagram Logic

Instagram is now digest-based, not single-story-first.

### Preserve Morning vs Afternoon semantics

Current model:

- Morning Digest = sim racing / nostalgia / racing games / PT-related when available
- Afternoon Digest = motorsport

Do not collapse them back into generic per-story slots unless the whole system is intentionally redesigned.

### Preserve digest alternative semantics

Planner creates alternatives, overrides select among them, and the dashboard previews them.

Do not change alternatives into arbitrary custom edits without redesigning:

- overrides
- dashboard
- snapshot persistence
- export summary

### Preserve downstream compatibility

Instagram digests affect:

- `formatter.py`
- `email_digest.py`
- `dashboard_data.py`
- `dashboard_app.py`
- `card_generator.py`

Any change to digest structure should be treated as a multi-module change.

### Keep fallback story-only mode honest

If digest packs are missing:

- selected stories should still be shown
- the UI and brief should say structured pack is missing, not pretend it exists

## 10. Safe Rules for Editing the Dashboard

### Preserve snapshot vs fallback distinction

The dashboard is strongest when using the latest structured snapshot. When it falls back to files, it is intentionally partial.

Do not flatten those two states into one generic “latest data” claim.

### Keep session-only vs persisted state explicit

Persisted:

- override integers
- latest-run snapshot

Session-only:

- draft digest story reordering/add/remove preview
- copy-ready buffers

Do not label a session-only preview as if it were saved pipeline state.

### Keep direct links and asset discoverability obvious

The operator uses the dashboard to move quickly between:

- stories
- source URLs
- digest packs
- prompts
- voice scripts
- cards
- brief

Do not bury these under raw JSON or distant controls.

### Preserve operational clarity

Important UI honesty rules:

- show freshness state
- show data source
- show missing optional assets calmly
- keep Morning and Afternoon visually distinct

## 11. Safe Rules for Editing Overrides

### Preserve integer selector semantics

Overrides are variant selectors, not content payloads.

### Neutral defaults matter

Auto-created override files must not silently activate alternatives. Safe default behavior is:

- empty file
- or all-zero values

### Keep file creation safe

`dashboard_overrides.ensure_overrides_file()` must stay safe-by-default. Creating the file should not change editorial output.

### Do not drift override meaning silently

If you change how a channel resolves alternatives, update:

- `manual_overrides.py`
- `dashboard_overrides.py`
- `dashboard_data.py`
- dashboard preview/export
- relevant tests

## 12. Safe Rules for Editing Formatter / Brief Output

### The brief must always be generated

The formatter is part of the core path. It should remain resilient even when:

- `plan` is missing
- agent outputs are missing
- card paths are missing

### Avoid misleading empty sections

Do not render a section just because a dict exists. Render it because there is meaningful content.

This matters especially for:

- MiniMax/generated sections
- digest pack sections
- optional prompt blocks

### Preserve operator readability

Keep:

- links
- titles
- scores
- alternatives
- clear labels for structured packs and prompts

The brief is an operational artifact, not just a debug dump.

## 13. Safe Rules for Editing Email Digest

### Keep email optional

`send_email_digest(...)` must remain non-fatal when SMTP config is missing or sending fails.

### Preserve final-selection dependence

Email must reflect the resolved plan after overrides, not raw planner primaries unless those are the resolved result.

### Preserve mobile usefulness

The email is designed as a mobile-friendly operational surface. Avoid changes that:

- create giant unreadable blocks
- hide links
- collapse Morning and Afternoon digest distinctions

## 14. Safe Rules for Editing Cards / Assets

### Cards are optional

Never make brief generation depend on card generation success.

### Respect asset constraints

`card_generator.py` depends on:

- Pillow
- local fonts/logo in `assets/`

Changes should remain safe when those are missing.

### Preserve current digest compatibility expectations

Current digest support is intentionally minimal:

- digest cover compatibility
- not a full carousel design system

Do not document or imply stronger behavior unless you actually implement it.

## 15. Safe Rules for Editing News Sources

### API sources are supplementary

RSS feeds are the main source base. API sources are lower-priority enrichment.

### Keep optional dependencies optional

If NewsAPI, GNews, or Reddit credentials are missing:

- supplementation should return empty results
- scanning should still succeed

### Do not make scanning brittle

A single slow or failing optional source should not poison the whole scan.

## 16. Testing Rules Before Any Patch Is Considered Done

This repo should not be modified on happy-path confidence alone.

Minimum validation for most patches:

- run `python -m py_compile` on modified Python files
- import modified modules
- add or run targeted tests for the changed behavior
- run `python -m unittest discover -s tests -v`
- run `python main.py --dry-run`

Also test fallback paths when relevant:

- missing MiniMax key
- invalid JSON
- missing overrides
- invalid override values
- missing snapshot
- missing cards
- missing SMTP config
- missing optional dependencies

For operator-facing patches, also check:

- brief readability
- dashboard clarity
- direct link presence
- no misleading success/freshness/persistence wording

## 17. Dangerous Anti-Patterns in This Repository

Avoid these repository-specific mistakes:

- changing shared dict keys casually
- turning optional features into required runtime dependencies
- trusting stale docs over current code
- returning raw JSON into operator-facing output when structured output should be composed into readable text
- silently changing override semantics
- hiding whether the dashboard is using snapshot or fallback data
- implying session-only edits are persisted
- rendering empty “generated” sections that suggest useful output exists when it does not
- changing Instagram digest semantics in one module only
- broad refactors across planner/formatter/dashboard without updating tests

## 18. Safe Patch Strategy

Use this approach for future changes:

1. inspect the real code first
2. locate the actual implementation points
3. identify the contract boundaries that will be touched
4. patch narrowly
5. validate both happy path and fallback path
6. report honestly what changed and what remains environment-dependent

Good repository-specific habits:

- prefer compatibility-first changes
- keep operator workflow intact
- update tests in the same patch when shared behavior changes
- keep batch launcher and dashboard behavior honest and predictable

## 19. Final Safety Checklist

Before finalizing a patch, verify:

- code changes follow current code behavior, not stale docs
- the brief still generates on `python main.py --dry-run`
- optional subsystems still fail gracefully
- shared `plan` keys still satisfy downstream consumers
- override behavior is still neutral and predictable
- agent JSON contracts still parse cleanly
- dashboard freshness/persistence wording is still honest
- links, prompts, scripts, and digest packs are still discoverable
- tests for the changed behavior exist and pass
- the final report states any remaining limitation clearly
