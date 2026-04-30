# Wave 1 Evidence Path Selection Matrix

## Purpose

This document defines the selection boundary between:

- `lookup_generic_food`
- exact DB
- web search candidate discovery
- web extract
- Taiwan semantic case-law metadata
- `llm_prior`
- clarify boundary final

It exists to prevent accidental collapse of all nutrition evidence paths into one runtime habit.

This matrix does not change the Wave 1 Phase B-1 runtime contract by itself. It clarifies how evidence path selection should be interpreted across B-1 and B-2.

Evidence path decisions may be implemented through food knowledge metadata and mention/sense resolution defined in `WAVE_1_PHASE_B2_FOOD_KNOWLEDGE_METADATA_SPEC.md`. This matrix owns route policy; the food metadata spec owns how surface food terms map to generic anchors, exact item cards, meal templates, or listed-basket itemization metadata.

## Core Policy

Mutation intent changes evidence threshold.

The same food may use a different evidence path depending on whether the interaction is:

- logged food with possible ledger impact
- no-mutation query-only answer
- exact brand/store-specific identity resolution
- composition-unknown boundary clarification

`lookup_generic_food` is not web search.

Tavily search is web candidate discovery, not generic food lookup.

Broader Tavily extract is deferred and should remain behind `WebExtractPort`.

A narrow exact-brand exact-DB-miss live diagnostic canary may use `WebExtractPort` for selected extract trace verification only. That canary does not activate general web extraction or user-facing exact-result mapping.

`llm_prior` is an allowed traceable hint or fallback path. It is not silent ledger truth.

## P0 Contract Freeze Alignment

For `B2-001`, interpret the Wave 1 product contract as:

- estimable cases may become `logged`
- unresolved composition cases must remain `draft`
- `provisional` is an internal estimation posture, not a permission to hide uncertainty
- packet usage classes must stay explicit and trace-visible
- follow-up severity is a precision-upgrade tool, not a hidden commit gate
- retrieval intent stays a typed raw-state object; it is not evidence verdict, synthesis, or mutation decision

## Evidence Path Matrix

### Logged common single food

Example:

- `我吃了一顆茶葉蛋`

Policy:

- B-1 core smoke uses `lookup_generic_food` to validate the generic evidence tool-loop path.
- This does not mean `llm_prior` is permanently forbidden for the product.
- `llm_prior` may later serve as traced fallback or sanity check, but not as silent commit truth in this slice.
- For logged food with mutation intent, evidence threshold is higher than for a query-only answer.

### Query-only common food

Example:

- `茶葉蛋大概幾卡？`

Policy:

- no mutation
- `llm_prior` may answer an approximate range
- generic lookup is optional
- response must not claim logged status

### Logged high-variance common item

Examples:

- `我喝了一杯珍珠奶茶`
- `我吃了一個便當`
- `我吃了一碗牛肉麵`

Policy:

- generic lookup preferred
- return range and uncertainty posture
- targeted follow-up may be appropriate
- no web path unless brand/store is specified

### Composition-unknown self-selected basket

Example:

- `我吃了滷味`

Policy:

- clarify-style boundary final
- no estimate
- no mutation
- no generic lookup
- no web search

Accepted boundary semantics:

- composition unknown
- ask for missing item composition or listed ingredients
- no nutrition synthesis
- no fake-final delegation

### Listed-ingredient basket

Example:

- `我吃了豆干、海帶、貢丸的滷味`

Policy:

- item-level `lookup_generic_food`
- no web path needed in the normal case
- `llm_prior` may be auxiliary later, but the primary path is generic item-level evidence

### Brand/store-specific item

Examples:

- `迷客夏珍珠紅茶拿鐵`
- `松屋特盛牛丼`

Policy:

- exact DB first
- web search candidate second if exact DB misses
- broader Tavily extract remains deferred behind `WebExtractPort`
- a narrow exact-brand exact-DB-miss diagnostic canary may use selected extract through `WebExtractPort`, but it remains trace-only and not user-facing activation
- `llm_prior` only as fallback, never as exact truth

Brand/store-specific does not imply immediate extract.

### No-mutation nutrition query

Examples:

- `珍珠奶茶大概多少熱量？`
- `茶葉蛋大概幾卡？`

Policy:

- generic lookup or `llm_prior` may be used
- no mutation
- if the query is brand/store-specific, move toward the exact/web path

## B-1 Interpretation Notes

`B1-001` remains `lookup_generic_food` in Phase B-1 because it tests the generic evidence tool-loop path.

It does not mean the product architecture permanently forbids `llm_prior` for common-food estimation.

`B1-004` remains a composition-unknown boundary case:

- clarify boundary final
- no estimate
- no mutation
- no generic lookup
- no web search

## Case Strictness & Evidence Posture

Phase B-1 cases are not all equally strict about route shape.

### Hard invariants

- `B1-004` composition-unknown self-selected basket
  - must not estimate
  - must not call `lookup_generic_food`
  - must not use web search
  - must not log or mutate
  - accepted shape is clarify-style final only
- `B1-005` listed-ingredient basket
  - must not collapse listed ingredients into a basket-level fake lookup
  - item-level lookup is the intended evidence path
- `B1-006` no-mutation nutrition query
  - hard invariant is `no mutation`
  - response must not claim logged status
  - route may remain flexible
- unsupported alias
  - `search`, `extract`, `web_search`, and `food_lookup` must not be accepted as canonical tool names

### Golden path smoke

- `B1-001` may remain a generic-evidence tool-loop smoke
- expected route for this smoke is `lookup_generic_food`
- this is a smoke contract, not a product-wide claim that `llm_prior` is always invalid

### Flexible outcome eval

- `B1-001`, `B1-002`, and `B1-003` should not all be treated as hard route validators
- multiple evidence postures may be valid depending on product policy, including:
  - generic lookup
  - `llm_prior` rough estimate
  - clarify-first
- these cases should be judged by outcome safety, uncertainty posture, source posture, and mutation policy, not only by exact route

### Decision-shape validator policy

- v1 decision-shape validators may enforce only hard invariants
- they must not enforce preferred routes for flexible cases
- they must not auto-repair model decisions
- they must not add tools, normalize aliases, or manufacture fake green

## LLM Prior Trace Policy

- `llm_prior` is not a tool
- it is a model-internal evidence posture or synthesis posture
- it may be valid for a no-mutation answer, rough estimate, or DB-miss fallback
- if it is later used for ledger-adjacent output, it must be explicitly traced as `source_type=llm_prior`, `prior_used=true`, and a rough estimate posture

## B-2 Interpretation Notes

This matrix aligns with the B-2 packet contract:

- `source_type: exact_db | generic_db | web_search | web_extract | taiwan_skill | llm_prior`
- `source_quality_label` remains distinct from exactness posture

Interpretation note:

- `taiwan_skill` remains a synthetic-gate compatibility label only
- target runtime architecture should attach Taiwan semantics to generic food knowledge metadata
- clarify-only semantic support must stay outside the `GenericDbCandidatePacket` lane

`llm_prior` is allowed only as weak traced evidence and cannot justify exact claims, strong evidence confidence, or silent ledger truth.
