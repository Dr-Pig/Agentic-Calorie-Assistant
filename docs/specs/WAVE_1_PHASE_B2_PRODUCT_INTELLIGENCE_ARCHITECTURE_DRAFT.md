# Wave 1 Phase B-2 Product Intelligence Architecture Draft

## Purpose

This draft captures the current agreed product-intelligence direction for Wave 1 Phase B-2.

It is an additive architecture-planning document. It does not silently replace:

- `docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md`
- `docs/specs/WAVE_1_EVIDENCE_PATH_SELECTION_MATRIX.md`
- `docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md`
- `docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md`

If this draft conflicts with canonical product status semantics or runtime ownership, resolve the product invariant first and then realign the gate docs explicitly.

## Section 1 - Architecture Direction

Phase B-2 should not be implemented as:

- `DB-first`
- pure freeform model prior estimation
- full autonomous multi-hop ReAct retrieval

Phase B-2 should be implemented as:

- `LLM-first composition inference`
- `selective search or selected external evidence when justified`
- `small anchor store`
- `packetized evidence`
- `estimate-first logging when estimable`
- `correction-first follow-up loop`

The goal is not to beat a strong model prior by brute-force database size. The goal is to make estimation behavior structured, traceable, correctable, and productizable.

## Section 2 - Core Status Rule

External user-visible status remains binary:

- `logged`
- `draft`

Internal exactness or evidence posture may still distinguish:

- `exact`
- `estimated`
- `provisional`
- `unresolved`

Hard alignment rule:

- `estimable -> logged`
- `unresolved -> draft`

`provisional` is an internal posture. It is not a third user-facing or persistence state.

Follow-up does not block logging.

## Section 3 - Estimability Rule

Estimability is not a deterministic food-name rule.

Estimability is an LLM judgment about whether the system can infer the core composition well enough to estimate honestly.

If composition is inferable:

- estimate first
- log first
- then decide whether follow-up is worthwhile

If composition is not inferable:

- ask first
- do not log

This means the product should not hard-code that a dish class is always estimable or always non-estimable without going through the composition-inference judgment.

## Section 4 - Core Inference Contract

Before synthesis or mutation mapping, the LLM should produce a structured estimation judgment object.

Minimum fields:

```yaml
composition_inferable: boolean
estimation_blocker_reason: string | null
inferred_base_dish: string | null
inferred_core_components:
  - string
assumed_preparation_style: string | null
unknown_modifiers:
  - string
major_uncertainty_drivers:
  - string
exactness_posture: exact | estimated | provisional | unresolved
provisionality_severity: low | medium | high
likely_kcal: number | null
kcal_range: [number, number] | null
followup_needed: boolean
followup_priority: none | soft | strong
followup_targets:
  - string
followup_reason: string | null
```

The product should depend on this structured object, not on freeform nutrition prose.

## Section 5 - Logged vs Draft Decision Rule

Decision rule:

- if `composition_inferable = false`, the result stays `draft`
- if `exactness_posture = unresolved`, the result stays `draft`
- if `composition_inferable = true` and `exactness_posture in {exact, estimated, provisional}`, the result becomes `logged`

`followup_needed = true` does not block logging.

Key policy sentence:

`logged vs draft is determined by estimability, not by exactness`

## Section 6 - Follow-up Severity Policy

Follow-up is a precision-upgrade mechanism, not a commit gate.

Severity levels:

- `none`
- `soft`
- `strong`

The system should consider:

- absolute range width
- relative uncertainty
- whether the missing factor is a major calorie driver
- whether asking is actually useful and answerable

Examples:

- `茶葉蛋` -> `none`
- `珍珠奶茶` -> `strong`
- `松屋牛丼` -> `strong`
- `雞腿便當` -> `soft`
- `麻辣臭豆腐` -> `strong`

## Section 7 - Case-Law Semantics

Current agreed product examples:

### `今天喝了一杯珍珠奶茶`

- logged
- estimable
- strong follow-up
- ask sugar level and cup size

### `我吃了一個茶葉蛋`

- logged
- estimable
- no follow-up

### `我吃了滷味`

- draft
- not estimable from the bare phrase
- ask what ingredients were selected

### `我吃了雞腿便當`

- logged
- estimable
- soft follow-up
- `炸` vs `滷` matters more than side-dish uncertainty

### `我吃了麻辣燙`

- draft
- same composition-unknown basket rule as `滷味`

### `我吃了麻辣臭豆腐`

- logged
- estimable
- strong follow-up
- ask about noodles, add-ons, portion, and broth consumption

### `我吃了松屋牛丼`

- logged
- estimable
- strong follow-up
- bowl size is a major uncertainty driver

### `我吃了鹽酥雞`

- if the utterance implies a mixed stall basket, treat it like a composition-unknown basket and keep it `draft`
- if the utterance clearly specifies a single item such as `一份鹽酥雞` or `五十元鹽酥雞`, it may become estimable and loggable

## Section 8 - Small Anchor Store Scope

The small anchor store is an inference-support layer, not an inference-replacement layer.

Each anchor should capture:

- a stable estimable dish anchor
- major calorie-driving modifier schema
- common composition hints

Minimum anchor shape:

```yaml
anchor_id: string
canonical_name: string
aliases:
  - string
dish_type: string
baseline_kcal_range: [number, number]
baseline_likely_kcal: number
major_modifiers:
  - name: string
    values:
      - string
composition_hints:
  - string
```

P0 should stay test-aligned and intentionally small.

Start with:

- high-frequency single items
- high-frequency customizable drinks
- high-frequency generic meals
- stable-base but variable dishes
- listed-ingredient item anchors

Do not start with a giant brand/menu corpus.

## Section 9 - Source Priority By Case Type

Source priority should be case-type-sensitive, not globally fixed.

### Stable generic single item

Order:

1. small anchor store
2. trusted generic DB
3. model prior

### Generic inferable customizable drink

Order:

1. small anchor store plus modifier schema
2. model prior composition inference
3. trusted generic DB
4. selected search when brand identity exists

### Brand or menu item

Order:

1. official brand or menu source
2. selected search candidate
3. small anchor store
4. model prior fallback

### Generic known-structure meal

Order:

1. small anchor store plus composition hints
2. model prior composition inference
3. trusted generic DB
4. optional selected search

### Stable-base but variable dish

Order:

1. small anchor store plus composition hints
2. model prior composition inference
3. trusted generic DB
4. selected search when store identity exists

### Composition-unknown basket

Do not enter estimate-source ranking.

The correct path is:

- ask first
- remain draft

### Listed-ingredient basket

Order:

1. item-level anchors
2. item-level generic DB
3. model prior as decomposition support

### Query-only nutrition answer

Use the same estimation rigor as the matching logging case.

Difference:

- `mutation = false`

## Section 10 - Search Result To Packet Compression

Search results are not nutrition truth.

They must be compressed into typed evidence packets before synthesis.

Packet usage classes:

- `exact`
- `anchor`
- `semantic_hint`
- `rejected`

Snippet policy:

- snippets may help source discovery or ranking
- snippets may act as hints
- snippets must not directly become final kcal truth or exact evidence

Packet layer should preserve:

- packet identity
- source quality
- match or mismatch posture
- serving basis
- extracted kcal if available
- rejection reasons for bad candidates

## Section 11 - Ownership Split: LLM Judgment vs Deterministic Guardrails

Deterministic packet policy should not try to decide everything.

Deterministic guardrails should own:

- schema validation
- source metadata normalization
- snippet-as-truth blocking
- exactness hard vetoes
- extract budget limits
- packet completeness checks
- mismatch labeling

LLM judgment should own:

- composition inferability
- base dish inference
- major uncertainty drivers
- whether a candidate can still serve as anchor
- final range and likely estimate
- follow-up targets

This is a hybrid ownership model:

- semantic judgment stays with the LLM
- hard safety and compression stay deterministic

## Section 12 - Retrieval Loop Shape

Phase B-2 should use a bounded two-pass retrieval pipeline, not a full open-ended ReAct loop.

### Pass 1

LLM outputs:

- composition inferability
- inferred base dish
- unknown modifiers
- major uncertainty drivers
- selected evidence path
- whether search is needed
- whether selected extraction is worth doing

### Retrieval Step

Data tools may perform:

- anchor lookup
- generic DB lookup
- selected search
- optional selected extraction

### Guardrail Step

Deterministic packet policy:

- normalizes packets
- applies hard vetoes
- enforces extract budget
- blocks snippet-only truth claims

### Pass 2

LLM uses the packet set to produce:

- exactness posture
- likely kcal
- kcal range
- follow-up targets
- uncertainty reason

### Final Mapping

Deterministic mapping applies the already-approved status rule:

- `unresolved -> draft`
- otherwise `logged`

## Section 13 - DB Retrieval Shape

DB retrieval should not start as raw keyword-only search.

For a small anchor store, the recommended P0 shape is:

1. normalize the utterance into a structured retrieval intent
2. attempt canonical or alias match
3. apply metadata filters for brand, dish type, size, or modifier slots when available
4. fall back to semantic or hybrid candidate expansion only when the deterministic candidate set is weak or ambiguous
5. keep candidate traces instead of silently collapsing to one answer

Recommended retrieval intent fields:

```yaml
base_dish: string | null
aliases:
  - string
brand_hint: string | null
size_hint: string | null
modifier_hints:
  - string
listed_items:
  - string
retrieval_goal: exact_lookup | anchor_lookup | brand_lookup | semantic_hint
```

P0 guidance:

- if the corpus is still small and test-aligned, do not overbuild a vector stack first
- start with alias normalization plus structured filters
- add semantic or hybrid retrieval only when ambiguity or corpus growth justifies it

This follows the same best-practice direction as modern retrieval systems:

- query rewriting improves retrieval quality
- metadata or attribute filters narrow the candidate set
- hybrid retrieval is helpful once simple exact or alias lookup stops being enough

## Section 14 - Retrieval Recheck Policy

Every candidate that survives retrieval should pass a recheck layer before synthesis uses it.

Recheck has two parts:

### Deterministic recheck

Hard checks such as:

- wrong brand
- wrong size
- missing serving basis
- snippet-only evidence
- clear sibling exactness veto

### Semantic recheck

LLM-assisted checks such as:

- still usable as anchor?
- still supports the inferred composition?
- should this be downgraded to semantic hint?
- does the mismatch force unresolved status?

Query construction should be guided by the structured retrieval intent, not by bare keyword templates.

## Section 15 - Wrong-Item And Sibling-Variant Rejection

Mismatch families should be explicit:

- `wrong_item`
- `sibling_variant`
- `wrong_size`
- `wrong_modifier`
- `insufficient_evidence`

Exact claims require all of:

- same item
- same brand when relevant
- same size or serving when relevant
- same major modifier when relevant
- clear serving basis
- clear calorie basis

Some mismatches may downgrade to `anchor`.

Others must remain `rejected` or force `unresolved`.

Rejected candidates should stay trace-visible for evaluation, debugging, and correction learning.

## Section 16 - Query And Logging Parity

The quality standard for estimation should remain the same for query and logging.

The difference is mutation, not lower estimation rigor for queries.

Examples:

- `珍珠奶茶多少熱量？`
- `我喝了一杯珍珠奶茶`

Both may share the same estimation contract.

Difference:

- query does not mutate
- logging may mutate

## Section 17 - Minimal P0 Build Order

Recommended build order:

1. finalize contract alignment
   - inference contract
   - logged vs draft rule
   - follow-up severity rule
2. add synthetic contract tests
   - estimability
   - mismatch downgrade
   - packet usage
3. build the small anchor store in test-aligned minimal scope
4. implement structured retrieval intent construction
5. implement packet compression and deterministic hard recheck
6. implement Pass 2 synthesis over packet refs
7. add correction-path hooks and follow-up trace support
8. only then consider live external search or larger corpus work

P0 should prioritize contract correctness over data volume.

## Section 18 - What Not To Build Yet

Do not start with:

- giant nutrition DB ingestion
- full brand-menu corpus
- full autonomous multi-hop search agent
- production accuracy claims
- UI-level third status beyond logged vs draft
- deterministic food-name taxonomy as the main estimability engine

## Section 19 - Best-Practice Reference Shape

The architecture direction in this draft is consistent with the current best-practice pattern:

- use strong LLM judgment for ambiguous composition and uncertainty reasoning
- use query rewriting and structured retrieval intent instead of raw search text
- use metadata or attribute filters to narrow candidate sets
- keep deterministic layers for hard guardrails and compression, not full semantic judgment
- keep retrieval loops bounded before introducing heavier multi-hop agentic search

Any implementation slice that changes retrieval, packetization, DB lookup, or follow-up policy should re-check current official best-practice guidance before coding.

## Section 20 - Large-DB RAG Adoption Trigger

Large-DB RAG or hybrid retrieval is intentionally deferred out of Phase B-2 P0.

Do not start RAG merely because a larger corpus sounds more future-proof.

Introduce metadata-aware hybrid or semantic retrieval only after all of the following are already stable:

- retrieval intent object
- packet compression
- deterministic hard recheck
- wrong-item and sibling-variant downgrade rules
- final logged vs draft mapping

RAG or hybrid retrieval becomes justified when one or more are true:

- alias plus metadata-filtered lookup shows material recall gaps in evals
- the anchor corpus grows large enough that manual alias and filter maintenance becomes the bottleneck
- brand or menu corpora become semi-structured document sets rather than manageable rows
- lexical candidate generation alone is no longer good enough for recall
- retrieval recall, not synthesis or packet policy, is the proven limiting factor

When the trigger is reached, the preferred next step is:

- query-rewritten retrieval intent
- metadata or attribute filters
- hybrid lexical plus semantic candidate generation
- packet-first synthesis

Do not jump from small structured lookup directly to blind vector similarity.
