# Findings & Decisions

## Requirements
- Inspect the real current agent flow and its consumers before editing.
- Add two new per-story agents in `agents.py`: `article_reader` and `platform_copywriter`.
- `article_reader` must read the real article URL and return strict JSON with either `status=ok` and article summary data or `status=cannot_access_article`.
- `platform_copywriter` must generate concise PT-PT per-platform outputs for one story at a time from the reader output.
- Add `run_story_platform_pipeline(article)` with safe fallback behavior.
- Preserve existing grouped digest flow unless safely untouched.
- Validate with py_compile, imports, focused tests, output-shape checks, and `python main.py --dry-run`.

## Research Findings
- `agents.py` currently exposes two active flows:
  - `run_full_pipeline(article)`: a five-stage per-article chain (`analyst -> copywriter -> image_director -> voice_director -> qa`)
  - `run_instagram_digest_pipeline(digest_articles, digest_type)`: a dedicated grouped-digest path
- The current per-article flow does not read article bodies. It builds the prompt only from title, source, summary, score, and link.
- Current per-article outputs are stored in `curated["agent_outputs"]` and normalized downstream as dictionaries with keys like:
  - `article`
  - `analysis`
  - `post`
  - `raw_post`
  - `instagram_pack`
  - `image_prompt`
  - `voice_script`
  - `qa`
  - `agent_metrics`
- `main.py` currently runs `run_full_pipeline()` only for the top 3 curated stories and stores the results in `curated["agent_outputs"]`.
- `dashboard_data.py` is the main per-story consumer:
  - `_normalize_output()` assumes the existing fields above
  - workspace builders use `analysis`, `instagram_pack`, and `voice_script` to create per-story Instagram/X/YouTube/email drafts
  - there is no current field for `article_summary`, platform-specific copy blocks, or reader/copywriter status
- `formatter.py` still renders the old per-article agent section as a generic MiniMax output block based on `post`, `instagram_pack`, `image_prompt`, `voice_script`, and `qa`.
- `email_digest.py` still uses `post`, `image_prompt`, `voice_script`, and digest packs for its rich email blocks. It does not currently know about a structured per-platform per-story payload.
- This means the safest implementation is additive:
  - keep existing fields for backward compatibility
  - add the new reader/copywriter structure alongside them
  - adapt dashboard/email/formatter only where the new fields improve compatibility without breaking old assumptions

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Keep new flow additive rather than replacing digest flows | User explicitly asked not to break or remove existing flows that may still be used elsewhere |
| Preserve legacy top-level fields while adding structured per-platform outputs | Dashboard, formatter, and email digest still depend on `post`, `analysis`, `instagram_pack`, `voice_script`, and `qa` |
| Make `main.py` process every selected story through the new flow | The requested product behavior is per-selected-story processing, not the previous top-3 sample run |
| Prefer the new structured per-platform payloads in `dashboard_data.py` while keeping legacy fallbacks | The dashboard should show the article-based outputs when available without breaking older snapshots |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Existing agent tests failed because the new pipeline fetches article content before calling the model | Rewrote the tests to stub `_fetch_article_payload()` explicitly and assert the new reader/copywriter contracts |
| The first draft stored `copywriter_output` as a reference to the whole result dict | Replaced that with a plain compatibility payload and only expose it when the copywriter actually returns valid structured JSON |

## Resources
- `C:\Users\berna\Desktop\Simula_Project\morning-brief\agents.py`
- `C:\Users\berna\Desktop\Simula_Project\morning-brief\dashboard_data.py`
- `C:\Users\berna\Desktop\Simula_Project\morning-brief\dashboard_app.py`
- `C:\Users\berna\Desktop\Simula_Project\morning-brief\formatter.py`
- `C:\Users\berna\Desktop\Simula_Project\morning-brief\email_digest.py`

## Visual/Browser Findings
- None. This task is local-code inspection only.
