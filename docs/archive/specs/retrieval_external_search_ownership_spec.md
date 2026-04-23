# Retrieval and External Search Ownership Spec

## Deterministic ownership
- Run bounded local grounding before decision:
  - `resolve_exact_item(...)`
  - `resolve_ingredient_anchors(...)`
- Split evidence into:
  - `exact_lane`
  - `anchor_lane`
  - `template_lane`
- Apply identity gate, packaged-retail exclusion, and search loop caps.
- Build reasoning and observation facts for LLM consumption.

## Decision LLM ownership
- First route owner.
- Decides whether local evidence is enough, whether to escalate to external official search, and whether to continue into nutrition.

## Nutrition LLM ownership
- Secondary escalation owner.
- If first-round evidence is still insufficient, it may request one more tool round.
- Owns final nutrition posture and calorie reasoning.

## External search policy
- Two-stage escalation:
  1. local exact + local anchor
  2. external official search if evidence gap remains
- Search quality should not be treated as usable merely because results exist.
- `web_search_official` is fallback evidence, not default exact truth.
- `exact_item_db` remains higher authority than `web_search_official`.
- Search observation should expose:
  - `official_hit_count`
  - `identity_hit_count`
  - `coverage_status`
  - `why_not_enough_yet`

## Non-goals
- Deterministic code does not decide final exactness or kcal.
- Search is not fully free-form and is not hard-coded as DB-then-search only.
