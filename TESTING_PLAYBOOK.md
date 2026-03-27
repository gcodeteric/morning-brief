# SimulaNewsMachine — Testing Playbook

## 1. Purpose of This Playbook
This file defines the repository-specific testing rules for SimulaNewsMachine. It exists to keep future patches honest, repeatable, and safe against regressions in the core brief pipeline, optional subsystems, dashboard workflow, and shared data contracts.

This playbook is code-aligned. If it ever diverges from the implementation, trust the code and update this document.

## 2. Testing Philosophy of This Repository
SimulaNewsMachine is not a generic web app. It is a content operations pipeline with a strict reliability requirement:

- The daily brief must keep generating.
- Optional layers must remain optional.
- Operator-facing output must stay readable and trustworthy.
- Shared dict contracts between modules must not drift silently.
- Fallbacks must be tested, not assumed.
- Live external services must not be required to validate most patches.

In practice, this means patches are not safe just because the happy path works. A patch is only credible when it proves that the failure paths still degrade cleanly.

## 3. Minimum Validation Required for Any Patch
For almost any patch in this repository, the minimum safe validation baseline is:

1. Run `python -m py_compile` on every modified Python file.
2. Import every modified Python module directly.
3. Run the most relevant automated tests for the changed behavior.
4. Run `python -m unittest discover -s tests -v` if the change touches shared contracts, agents, overrides, formatter, dashboard, launchers, or documentation that references real commands/files.
5. Run `python main.py --dry-run`.
6. If the patch changes docs or launchers, verify that referenced files, paths, and commands actually exist in the repo.
7. If the patch changes operator-facing output, inspect the resulting brief, dashboard summary, launcher behavior, or email digest shape for obvious regressions.

Do not claim a patch is complete if `python main.py --dry-run` was skipped without a real reason.

## 4. Existing Test Coverage Overview
The repository currently uses `unittest`, not `pytest`, and already has meaningful targeted tests in `tests/`.

Covered today:

- `tests/test_planner.py`
  - empty input
  - one-article case
  - morning/afternoon digest creation
  - digest alternatives
  - duplication avoidance
- `tests/test_manual_overrides.py`
  - missing override file
  - invalid JSON
  - valid override resolution
  - invalid index fallback
- `tests/test_dashboard_overrides.py`
  - safe neutral override-file creation
- `tests/test_agents.py`
  - valid structured JSON handling
  - invalid JSON fallback
  - structured `improved_post` reparsing
  - digest empty input safety
  - timeout handling
- `tests/test_formatter.py`
  - grouped Instagram sections
  - missing optional data
  - empty MiniMax suppression
  - useful MiniMax retention
- `tests/test_dashboard_data.py`
  - snapshot save/load
  - missing snapshot fallback
  - stale snapshot labeling
  - selection summary resolution
- `tests/test_email_digest.py`
  - digest build with/without optional pieces
  - safe SMTP config failure
- `tests/test_launch_dashboard.py`
  - readiness detection
  - browser only after readiness
  - dashboard port fallback
  - explicit chosen-port usage
  - missing dashboard file
  - missing Streamlit
  - no-port failure path
  - operational target resolution
  - missing cards-folder path
- `tests/test_main.py`
  - CLI summary wording for the current digest model

Coverage is still partial. The most obvious weak or missing automated areas are:

- `scanner.py`
- `curator.py`
- `news_sources.py`
- `card_generator.py`
- full `dashboard_app.py` rendering behavior

These areas need stronger targeted validation when they change.

## 5. High-Risk Areas That Always Need Targeted Tests

### `curator.py`
High risk because it normalizes, filters, deduplicates, scores, and persists seen links. Small changes can silently distort editorial output or break selection quality.

### `planner.py`
High risk because many downstream modules trust the `plan` dict. Changing keys, digest semantics, or alternative selection logic will ripple into overrides, formatter, email, dashboard, and agents.

### `manual_overrides.py`
High risk because override semantics are simple but fragile. A silent drift in index handling changes operator intent.

### `formatter.py`
High risk because it is the final operator-facing artifact. Empty sections, bad labels, or missing links mislead the operator even if the underlying pipeline still ran.

### `agents.py`
High risk because it handles external model output, JSON parsing, fallback logic, and operator-readable post text. This is one of the easiest places to reintroduce silent regressions.

### `dashboard_data.py`
High risk because it normalizes shared state for the dashboard and mixes snapshot, fallback, overrides, and operator summaries.

### `dashboard_app.py`
High risk for UX honesty. Session-only state, persisted override state, copy actions, and freshness indicators must stay clear.

### `email_digest.py`
High risk because it must use the final resolved selection while remaining optional and non-fatal under SMTP/config failures.

## 6. Module-by-Module Testing Rules

### Scanner
Test:

- feed request timeout behavior
- feedparser fallback behavior
- per-feed failure tolerance
- API supplementation remaining non-fatal
- empty feed handling

Do not trust scanner changes without testing that one failing source does not break the scan pass.

### Curator
Test:

- incomplete article normalization
- low-quality/short-summary filtering
- YouTube Shorts filtering
- deduplication behavior
- seen-links persistence behavior
- empty input and small-input edge cases

Do not trust curator changes from code inspection alone. It contains dense heuristics and is under-tested today.

### Planner
Test:

- empty input
- one-article case
- morning digest composition
- afternoon digest composition
- alternative digests
- no unwanted duplication
- digest size boundaries
- override-safe behavior when alternatives are missing

Do not change plan keys or digest semantics casually.

### Manual Overrides
Test:

- missing file
- invalid JSON
- non-dict JSON
- valid override index behavior
- invalid override index fallback to primary
- neutral file creation if anything auto-creates overrides

Do not assume override safety because the file is small.

### Formatter
Test:

- brief generation with normal data
- brief generation with missing optional data
- grouped Instagram morning/afternoon sections
- operator-readable prompts and links
- suppression of empty/useless MiniMax sections
- retention of useful MiniMax sections

Any formatter change should include a sanity check of the generated Markdown, not just “file exists”.

### Agents
Test:

- valid JSON responses
- invalid JSON fallback
- structured `improved_post` fallback
- digest pack reconstruction
- timeout/failure path
- empty digest input
- operator-readable final `post`

Do not use live MiniMax calls in routine validation.

### Email Digest
Test:

- digest build with normal plan data
- digest build when optional pieces are missing
- SMTP disabled/incomplete configuration
- final resolved selection, not just primary plan entries
- mobile-friendly block structure where relevant

SMTP failure must remain non-fatal.

### Cards
Test:

- Pillow missing
- assets missing
- no-card fallback path
- digest cover compatibility if card behavior changes

Cards are optional; card failure must not break brief generation.

### Dashboard Data
Test:

- snapshot save/load
- missing snapshot fallback
- stale snapshot labeling
- resolved selection summaries
- override visibility
- safe empty defaults
- freshness/source labeling

This layer is the dashboard contract boundary. Treat it like an API.

### Dashboard App
Test:

- imports
- no crash with missing snapshot
- no crash with missing brief/cards/overrides
- session-only vs persisted state clarity
- operator summary accuracy
- copy/link actions after relevant changes

If no dedicated automated UI test is added, do at least a targeted smoke check and inspect the affected page manually.

### Launcher Flow
If launchers or `launch_dashboard.py` change, test:

- helper import and compile
- path resolution
- missing dashboard file
- missing Streamlit availability
- readiness-check behavior
- browser-after-readiness sequencing
- occupied-port fallback
- missing folder/file open targets where relevant
- readable failure paths

Do not trust batch file edits without validating the Python helper they depend on.

## 7. Fallbacks That Must Always Be Tested
These fallbacks are core to the current design and must be preserved:

- MiniMax API key missing
- invalid JSON from agents
- empty or partial agent outputs
- structured `qa.improved_post` fallback
- agent timeout/failure
- missing SMTP config
- email send failure
- missing card assets
- Pillow missing
- missing snapshot
- stale snapshot
- missing overrides file
- invalid override JSON
- invalid override index
- missing optional dependency such as Reddit client support
- optional API source failures
- dashboard fallback mode with partial data only

If a patch touches any area above, the fallback must be tested directly.

## 8. Operator-Facing Outputs That Need Sanity Checks
After relevant patches, sanity-check the actual artifacts the operator sees:

- generated brief Markdown
- Instagram Morning Digest and Afternoon Digest sections
- digest alternative visibility
- override resolution visibility
- MiniMax section usefulness
- image prompt and voice script labeling
- dashboard selection summary accuracy
- freshness/fallback notices in the dashboard
- launcher messages and final dashboard URL
- email digest readability

The repository can pass unit tests and still fail operationally if these outputs become misleading.

## 9. Testing Rules for Agent Layer Changes
When changing `agents.py`, always test:

- valid structured JSON handling
- invalid JSON fallback
- readable `post` output instead of raw JSON
- `instagram_pack` consistency
- digest pipeline behavior with empty input
- `qa.improved_post` reparsing
- timeout/failure metrics and safe return values

Avoid live external API dependence during tests. Use mocks and deterministic payloads.

If a change affects prompt/output schema, test both the producing path and every consumer that reads the result:

- formatter
- dashboard data
- email digest
- dashboard UI if operator-visible labels depend on it

## 10. Testing Rules for Instagram Logic Changes
When changing morning/afternoon digest logic, always test:

- digest composition
- story count boundaries
- category intent
- alternatives
- override selection
- formatter rendering
- dashboard visibility
- email digest alignment
- no accidental duplication inside the same digest

Do not validate Instagram only at the planner level. The contract flows through planner, overrides, formatter, agents, email, and dashboard.

## 11. Testing Rules for Dashboard Changes
When changing dashboard code, test:

- `dashboard_data.build_dashboard_context()`
- snapshot present vs snapshot missing
- stale/partial freshness labeling
- override visibility
- selection summary accuracy
- session-only draft edits vs persisted override state clarity
- link and copy actions when affected

The dashboard must never imply stronger persistence or freshness than the code actually provides.

## 12. Testing Rules for Documentation / Launcher Changes
When changing `README.md`, `PROJECT_CONTEXT.md`, `SAFE_MODIFICATION_GUIDE.md`, launchers, or startup helpers:

- verify every referenced file exists
- verify every referenced command is real
- verify every path is still correct
- verify launcher targets resolve to the real repo layout
- verify readiness logic if launcher behavior changed
- verify docs describe the current Morning Digest / Afternoon Digest model, not a legacy Instagram model

Documentation patches are not exempt from validation. In this repo, docs often describe real operator workflow and file locations.

## 13. Suggested Test Execution Order
Use this order after a non-trivial patch:

1. `python -m py_compile` on modified Python files
2. direct import checks for modified modules
3. the targeted `unittest` files for the changed behavior
4. `python -m unittest discover -s tests -v` if the change touches shared contracts or operator workflow
5. `python main.py --dry-run`
6. operator-facing sanity check of the affected artifact

For doc-only patches:

1. file existence checks
2. command relevance checks
3. optional full test run if the docs describe core workflow or launchers

## 14. Dangerous Anti-Patterns in Testing This Repo
Avoid these repository-specific mistakes:

- only testing happy paths
- skipping `python main.py --dry-run`
- trusting stale docs over code
- changing shared dict keys without tests
- not testing override fallback behavior
- not testing empty agent outputs
- relying on live API success as “validation”
- assuming dashboard fallback state is obvious without checking it
- treating session-only dashboard state as persisted behavior
- validating only one module when the change crosses planner/formatter/dashboard/email boundaries

## 15. Patch Completion Checklist
Before calling a patch done, verify all of the following:

- modified Python files compile
- modified modules import
- targeted tests for the changed behavior pass
- relevant fallbacks were tested
- `python main.py --dry-run` passes
- operator-facing output was sanity-checked if affected
- docs and launchers were validated against real files/commands if touched
- final report states what was actually tested and what was only statically inspected

If any of these is false, the patch is not fully validated.
