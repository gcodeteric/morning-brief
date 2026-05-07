# Task Plan: Two-Agent Per-Story Workflow

## Goal
Add a two-agent per-story flow in `agents.py` where `article_reader` reads the real article first and `platform_copywriter` then generates concise PT-PT platform outputs, while preserving existing digest flows and keeping dashboard/formatter/email compatibility safe.

## Current Phase
Phase 5

## Phases

### Phase 1: Requirements & Discovery
- [x] Inspect current `agents.py` flow and output contracts
- [x] Inspect dashboard/formatter/email consumers
- [x] Document findings in `findings.md`
- **Status:** complete

### Phase 2: Contract Design
- [x] Define `article_reader` and `platform_copywriter` contracts from real code constraints
- [x] Decide minimal compatibility approach for dashboard/formatter/email
- [x] Document decisions with rationale
- **Status:** complete

### Phase 3: Implementation
- [x] Add new prompts and helper functions in `agents.py`
- [x] Add `run_story_platform_pipeline(article)` and safe fallback behavior
- [x] Adjust consumers only if required
- **Status:** complete

### Phase 4: Testing & Verification
- [x] Add/update tests for reader, copywriter, pipeline success, and fallback paths
- [x] Run py_compile/imports/relevant tests
- [x] Run `python main.py --dry-run`
- **Status:** complete

### Phase 5: Delivery
- [x] Review diffs and validation evidence
- [x] Summarize remaining limitations honestly
- [ ] Deliver final report
- **Status:** in_progress

## Key Questions
1. What is the current per-story agent contract and how much of it is consumed directly by dashboard data shaping?
2. How can the new per-story structure be added without breaking existing grouped digest flows and tests?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use code-first inspection before changing prompts/contracts | The user explicitly asked to preserve real current behavior and avoid invented architecture |
| Keep legacy `post` / `instagram_pack` / `voice_script` fields while adding structured per-platform outputs | `dashboard_data.py`, `formatter.py`, and `email_digest.py` still consume the legacy keys |
| Run the new per-story flow for every selected story in `main.py` | The requested behavior is explicitly “for EACH selected news item” rather than the previous top-3 sample |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Existing `tests/test_agents.py` assumed the old five-stage pipeline and live-fetched `example.com` during the new flow | 1 | Rewrote the tests to stub article fetch and assert the new two-agent JSON contract directly |
| `copywriter_output` became self-referential during the first implementation draft | 1 | Added `_copywriter_output_payload()` and only populate `copywriter_output` when the copywriter returns valid structured JSON |

## Notes
- Keep scope centered on `agents.py` and only touch consumers if compatibility truly requires it.
- Preserve graceful degradation when article access fails or optional agent outputs are unavailable.
