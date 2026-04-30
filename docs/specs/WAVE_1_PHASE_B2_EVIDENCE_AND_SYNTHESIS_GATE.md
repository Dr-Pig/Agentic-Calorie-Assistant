# Wave 1 Phase B-2 Evidence And Synthesis Gate

## Purpose

Phase B-2 is the evidence retrieval and nutrition synthesis quality gate for Wave 1. It is not a full nutrition engine and does not introduce production accuracy claims.

Passing Phase B-2 does not mean nutrition accuracy is production-ready. It only means the evidence path, same-item matching, synthesis boundary, guard behavior, and renderer wording are clean enough to proceed to Phase B-2 implementation.

This gate extends:

- `docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md`
- `docs/specs/WAVE_1_NUTRITION_WORKFLOW_AND_TOOL_CONTRACTS.md`
- `docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md`

It does not rewrite those canonical docs. If this gate conflicts with them, resolve the canonical product invariant first, then update this gate explicitly.

## Scope

Phase B-2 verifies contracts for:

- exact DB, generic DB, web search, selected extract, Taiwan semantic skill, and LLM-prior packets
- same-item matching and sibling/wrong-item rejection
- Manager Pass 2 evidence synthesis using compact packet refs
- selected extract policy
- exactness posture guard
- renderer exactness wording
- no-mutation queries that may use read tools but must not mutate

Runtime architecture note:

- `taiwan_skill` remains a synthetic-gate compatibility lane only
- target runtime architecture should attach Taiwan-specific semantics to generic food knowledge metadata
- clarify-only semantic records must not become independent runtime evidence packets

Food knowledge metadata, including generic anchors, exact item card seed metadata, meal templates, food mention/sense resolution, and portion cue semantics, is defined in `WAVE_1_PHASE_B2_FOOD_KNOWLEDGE_METADATA_SPEC.md`.

This gate owns packet-level invariants. The food metadata spec must not redefine packet truth levels, source quality labels, exactness guard behavior, product mutation semantics, or final mapping ownership.

Phase B-2 does not implement:

- autonomous nutrition subagents
- independent LLM evidence normalizers
- full macro engine
- all-web extract
- Grok or LLM renderer
- recommendation, rescue, memory, proactive, or UI redesign
- production nutrition accuracy certification

## Packet Contract

Every B-2 evidence packet must include:

```yaml
packet_id: string
truth_level: candidate | hint | rule_hint
source_type: exact_db | generic_db | web_search | web_extract | taiwan_skill | llm_prior
source_quality_label: internal_exact | internal_generic | official | brand_menu | trusted_database | third_party | semantic_hint | llm_prior | unknown
raw_ref: string
```

Packet contracts separate three concepts:

- `source_quality_label` describes source authority.
- `match_type` describes whether the candidate is the same item.
- `evidence_confidence` is Manager Pass 2's synthesis confidence after comparing packets.

Exact claims require both same-item match and enough evidence quality. Source authority alone is not enough. An official or brand source for the wrong item must be rejected or downgraded to anchor-only.

Current runtime slice clarification:

- official wrong-item `web_search` candidates are reject-only
- web `anchor-only` downgrade is deferred to a later richer web-evidence slice

Compatibility note:

- `source_type=taiwan_skill` remains allowed in the synthetic gate for readiness compatibility
- runtime implementation should not introduce a standalone Taiwan semantic packet source
- clarify-only generic semantic support must stay outside the `GenericDbCandidatePacket` lane

## Candidate Same-Item Dimensions

Candidate packets from exact DB, generic DB, web search, or web extract must include:

```yaml
matched_name: string
canonical_name: string
match_type: exact | alias_exact | generic | related | no_match
brand_match: same | different | unknown | not_applicable
size_or_serving_match: same | different | generic_serving | unknown | not_applicable
modifier_match: same | different | unknown | not_applicable
serving_basis: string
sibling_variant_risk:
  present: boolean
  reason: string | null
```

Rules:

- Generic DB packets may provide ranges or likely kcal, but must not claim `match_type=exact` or `source_quality_label=internal_exact`.
- Generic semantic-only clarify support must not be emitted as `GenericDbCandidatePacket`.
- SearchCandidatePacket may carry snippet, URL, score, query, and matched terms, but must not carry `final_kcal`, `final_truth`, or `primary_source`.
- TaiwanSkillPacket may carry semantic posture hints, DB/web policy hints, and contrast rules. It must not contain kcal, macro, or portion truth.
- LLM prior is last resort, must be weak, and cannot support exact claims.

### P0 Mismatch Oracle Freeze

For `B2-002`, the synthetic mismatch oracle must explicitly cover:

- `wrong_item`
- `sibling_variant`
- `wrong_size`
- `wrong_modifier`
- `insufficient_evidence`

The readiness gate should block fake-green exact claims whenever one of these mismatch families is present in the supporting packet set.

## Manager Pass 2 Contract

Manager Pass 2 may synthesize item result candidates from compact packets. It must cite packet refs, not raw prose labels such as "Tavily result".

Required evidence refs:

```yaml
evidence_used:
  - packet_id: string
    source_type: string
    source_quality_label: string
    usage: exact | anchor | fallback | semantic_hint | rejected
    reason: string

rejected_candidates:
  - packet_id: string
    risk_type: sibling_variant | wrong_item | wrong_brand | wrong_size | irrelevant | insufficient_evidence
    reason: string
```

Manager Pass 2 output must include:

```yaml
item_results:
  - interpreted_food_identity: string
    assumed_composition: string | null
    kcal_range: [number, number] | null
    likely_kcal: number | null
    uncertainty_level: low | moderate | high | unknown
    evidence_confidence: exact | strong | moderate | weak | insufficient
    exactness_posture: exact | estimated | provisional | unresolved
    evidence_used: list
    rejected_candidates: list
    uncertainty_reason: string
    suggested_followup_question: string | null
```

Pass 2 may produce synthesis candidates. It must not mutate the ledger.

## Selected Extract Policy

B-2 may define selected extract policy, but it forbids all-web extract. Extract is only allowed for a selected search packet when the source appears official or brand/menu, the query is an exact or brand item, and the snippet is insufficient for synthesis.

For the current official B-2 offline producer lane, selected extract remains a narrow `B2-006` exact-positive runtime-honesty path only. It is not a general web extraction framework and does not imply live Tavily activation or active runtime extract threading.

Trace fields:

```yaml
selected_search_packet_id: string | null
extract_reason: string | null
extract_allowed_by_policy: boolean
max_extract_urls: number
extract_count: number
```

`extract_count` must not exceed `max_extract_urls`. `selected_search_packet_id="*"` is forbidden.

Selected extract policy chooses what to inspect, not what to believe. A selected search packet does not become final nutrition truth by itself. When selected extract is used, the final exact item result must be backed by an accepted `web_extract` packet produced by the B2 local runtime synthesis path.

## Exactness Guard

The exactness guard binds evidence posture to ledger and renderer behavior:

- `exact` requires exact internal DB or official/brand same-item evidence.
- `estimated` allows generic DB, trusted database, or strong same-category candidate evidence.
- `provisional` allows stable commercial range when composition is incomplete but estimable.
- `unresolved` forbids ledger inclusion and must ask for missing composition.
- sibling variants, wrong-size variants, wrong-brand variants, and wrong-item official pages block exact claims.
- follow-up severity is a precision-upgrade tool, not a hidden commit gate.
- search snippet presence does not authorize final truth by itself; snippet-as-truth must be blocked explicitly by the readiness gate.

No-mutation query rule:

```yaml
interaction_type: nutrition_info_query
read_tools_allowed: true
mutation_allowed: false
```

## Renderer Exactness Wording

Renderer wording must mirror Manager Pass 2 exactness and RendererInput only:

- `exact`: may say "資料顯示".
- `estimated`: must say "估算".
- `provisional`: must say "先記一筆粗估".
- `unresolved`: must ask for the missing composition.

Renderer must not invent kcal, budget, logged status, evidence quality, or exactness wording outside `renderer.input.allowed_facts`, `renderer.input.item_results`, and `renderer.input.ledger_mutation_result`.

## Smoke Cases

The B-2 synthetic gate must include:

| Case | Expected gate behavior |
| --- | --- |
| `我吃了一顆茶葉蛋` | generic DB candidate |
| `我喝了一杯珍珠奶茶` | generic DB plus optional refinement |
| `我吃了一個便當` | generic DB provisional |
| `我吃了滷味` | block estimate until ingredients are listed |
| `我吃了豆干、海帶、貢丸的滷味` | item-level generic lookup for listed ingredients |
| `迷客夏珍珠紅茶拿鐵` | exact DB miss plus Tavily search candidate |
| `松屋特盛牛丼` | exact or official web candidate |
| `珍珠奶茶多少熱量？` | read tools allowed, no mutation |
| sibling negative | `迷客夏珍珠紅茶拿鐵` matched to `迷客夏珍珠鮮奶茶`; exact claim forbidden |
| official wrong-item negative | official or brand source exists but wrong item; reject-only in the current runtime slice, with anchor-only deferred |

## Anti-Fake-Pass Checks

The readiness verifier must fail when:

- Tavily snippet is used directly as final truth.
- Generic DB is marked exact.
- sibling variant is used as exact.
- `evidence_used` lacks `packet_id`.
- rejected sibling candidate is missing from `rejected_candidates` or silently promoted despite mismatch.
- Taiwan Skill contains kcal, macro, or portion truth.
- extract is called for every search result.
- renderer exactness wording exceeds RendererInput.

## Implementation Preconditions

Before Phase B-2 runtime implementation starts, the readiness artifact must also prove the following preconditions:

```yaml
trusted_database_policy:
  allowlist:
    - source_id
  approved: boolean

trusted_source_manifest:
  entries:
    - source_id: string
      source_quality_label: trusted_database
      approved: boolean
      scope: string
      evidence_authority: local_app_owned_store
      semantic_authority: none
      runtime_web_activation: false
```

`trusted_database` is not a generic label for good-looking third-party pages. A packet with `source_quality_label=trusted_database` must either resolve `source_id` to an approved manifest entry that is also present in the policy allowlist, or carry explicit artifact-level justification. Otherwise it must remain `third_party`.

```yaml
llm_prior_trace:
  llm_prior_used: boolean
  why_no_better_evidence_available: string
  exact_claim_allowed: false
  evidence_confidence: weak | insufficient
```

LLM prior is last resort only. It cannot support exact claims, strong evidence confidence, or ledger exactness.

```yaml
minimal_db_seed_manifest:
  store_backing: local_app_owned_test_aligned_store
  semantic_authority: none
  provenance_note: seeds exercise local lookup / packetizer paths, not semantic ownership
  seeds:
    - food_name: string
      seed_type: generic | exact
      used_by_smoke_case: string
      fixture_only: boolean
      allowed_fields:
        - kcal_range
        - likely_kcal
        - macro_candidate
  exact_seed_policy: empty_for_real_runtime_in_this_slice
```

The default generic seed set is `茶葉蛋`, `珍珠奶茶`, `便當`, `豆干`, `海帶`, and `貢丸`. Generic seeds may include `kcal_range`, `likely_kcal`, and optional `macro_candidate`; they must not contain brand exact truth. Real exact DB seeds remain empty in this slice. Synthetic exact-positive packets are allowed only when marked `fixture_only=true`.

The B-2 deterministic producer may use a synthetic manager structured fixture as semantic input, but local evidence provenance must remain separate: `trusted_source_manifest` and `minimal_db_seed_manifest` describe app-owned local lookup / packetizer evidence stores, not a fake Manager, not live DB readiness, and not runtime web activation.

```yaml
runtime_trace_parity:
  status: checked | not_applicable
  required_core_fields_match: true
  extra_fields_allowed: true
  renamed_core_fields_allowed: false
  missing_core_fields_allowed: false
```

Runtime traces may add implementation metadata, but they must preserve canonical packet, Manager Pass 2, mutation, and renderer field names. Synthetic-only artifacts may use `status=not_applicable` until runtime traces exist.

Official B-2 producer artifacts may also include a report-only provenance diagnostic such as `producer_trace` to distinguish runtime-backed cases from deferred compatibility cases. This field is for report and readiness honesty only. It must not become nutrition-domain truth, renderer truth, exactness policy, or Phase C mapping input.

When the official producer uses listed-item runtime fanout, it may also emit a report-only `listed_item_fanout` trace with one resolution entry per listed item. This trace is for per-item runtime honesty and readiness diagnostics only. It must not decide estimate vs unresolved, evidence confidence, renderer wording, or Phase C mapping.

When the official producer uses selected extract for the exact-positive web lane, `extract_policy` remains a report/readiness diagnostic only, and `web_extract` packets remain exact-support candidates rather than final truth objects.

## Readiness Artifact

The B-2 verifier reads a synthetic artifact only. It does not start real DB, Tavily, extract, provider, renderer, or ledger runtime.

Minimum readiness output:

```yaml
ready_for_phase_b2_implementation: boolean
blockers: list
warnings: list
smoke_cases:
case_checks:
recommended_next_steps_ordered:
```

If blockers remain, the next step is:

```text
fix_phase_b2_gate_blockers -> rerun_phase_b2_evidence_synthesis_readiness_gate
```

Only when this gate is clean should implementation start for the minimal B-2 evidence/synthesis slice.
