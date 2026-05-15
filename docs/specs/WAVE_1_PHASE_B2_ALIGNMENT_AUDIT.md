# Wave 1 Phase B-2 Alignment Audit

## Purpose

This document records the first alignment audit between:

- current Phase B-2 product-intelligence direction
- current Phase B-1 live tool-loop truth
- canonical product and runtime ownership specs
- A1 / A2 / A4 grading semantics

It exists to answer one narrow question:

`Does the current B-2 direction conflict with existing Wave 1 product truth, runtime truth, or grading truth?`

This is an audit note, not a replacement spec.

## Sources Checked

Primary sources reviewed for this audit:

- [docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md)
- [docs/specs/WAVE_1_PHASE_B2_P0_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_P0_EXECUTION_PLAN.md)
- [docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md)
- [docs/specs/WAVE_1_EVIDENCE_PATH_SELECTION_MATRIX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_EVIDENCE_PATH_SELECTION_MATRIX.md)
- [docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md)
- [docs/_spec_snapshots/legacy_v2_wave_pack_20260515/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md](../_spec_snapshots/legacy_v2_wave_pack_20260515/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md) as historical reference only
- [docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md)
- [docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md)
- [docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md)
- [docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md)
- [docs/specs/app_v2_ideal_architecture_final.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/app_v2_ideal_architecture_final.md)
- [docs/_spec_snapshots/legacy_v2_wave_pack_20260515/V2_GRADING_RUBRIC.md](../_spec_snapshots/legacy_v2_wave_pack_20260515/V2_GRADING_RUBRIC.md) as historical reference only

## Summary Verdict

Current B-2 direction is broadly aligned with current B-1 and canonical Wave 1 product truth.

No blocking architecture contradiction was found.

Current status:

- `aligned`: yes
- `blocking_conflict`: none found
- `spec_debt`: present
- `implementation_debt`: present
- `needs_new_product_decision`: none required for the current B-2 P0 direction

The next step should be contract sync and terminology cleanup, not a product-semantics redesign.

## Conflict Matrix

| Topic | Owner Truth | B-2 Status | Classification | Notes |
| --- | --- | --- | --- | --- |
| `estimable -> logged` | [L1_RUNTIME_OWNERSHIP_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md) `default-commit`; [L0_PRODUCT_CAPABILITY_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md) allows provisional understanding before all details settle | aligned | `aligned` | B-2's estimate-first logging direction matches low-friction default-commit product truth. |
| `unresolved -> draft` | [legacy V2 minimal implementation contracts](../_spec_snapshots/legacy_v2_wave_pack_20260515/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md), [L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md) | aligned | `aligned` | B-2 still preserves a true unresolved / draft lane. |
| follow-up is not a commit gate | [L1_RUNTIME_OWNERSHIP_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md), [L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md) | mostly aligned | `aligned_with_bridge_needed` | This aligns if B-2 `estimated/provisional` maps to an allowed uncertainty-backed commit posture such as `generic_with_explicit_uncertainty`. |
| query vs logging rigor | [legacy V2 minimal implementation contracts](../_spec_snapshots/legacy_v2_wave_pack_20260515/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md) `info_query -> no_mutation`; [WAVE_1_EVIDENCE_PATH_SELECTION_MATRIX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_EVIDENCE_PATH_SELECTION_MATRIX.md) | aligned | `aligned` | Same evidence rigor with different mutation behavior is compatible with current truth. |
| composition-unknown basket must block estimate path | [WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md), [WAVE_1_EVIDENCE_PATH_SELECTION_MATRIX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_EVIDENCE_PATH_SELECTION_MATRIX.md) | aligned | `aligned` | B-2 keeps `滷味` / `麻辣燙` as ask-first draft cases, which matches B1-004 boundary truth. |
| LLM judgment vs deterministic guardrails | [L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md), [app_v2_ideal_architecture_final.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/app_v2_ideal_architecture_final.md), [AGENTS.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/AGENTS.md) | aligned | `aligned` | Canonical truth already says deterministic layers validate or downgrade but must not silently replace semantic outputs. |
| retrieval should be typed or metadata-first before semantic expansion | [L4B_RETRIEVAL_POLICY_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md) | aligned | `aligned` | B-2's `retrieval intent + alias + metadata filter + later hybrid trigger` strongly matches canonical retrieval policy. |
| full ReAct retrieval should be deferred | [legacy V2 execution architecture](../_spec_snapshots/legacy_v2_wave_pack_20260515/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md), [WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md) | aligned | `aligned` | B-2 bounded two-pass retrieval is consistent with the repo's current maturity stance. |
| grading truth A1/A2/A4 | [legacy V2 grading rubric](../_spec_snapshots/legacy_v2_wave_pack_20260515/V2_GRADING_RUBRIC.md) | mostly aligned | `aligned_with_spec_debt` | B-2 supports A2 honesty and A4 state boundaries, but wording or vocabulary drift could still create rubric ambiguity if not synchronized. |

## Spec Debt

### 1. Exactness vocabulary mismatch

Current docs use different vocabularies for similar postures:

- B-2 draft:
  - `exact`
  - `estimated`
  - `provisional`
  - `unresolved`
- minimal contracts:
  - `exact`
  - `anchored_estimate`
  - `heuristic_estimate`
  - `insufficient_info`
- intake runtime contract:
  - `exact`
  - `near_exact`
  - `generic_with_explicit_uncertainty`

This is not yet a product-semantics contradiction, but it is a terminology bridge gap.

Recommended action:

- create one explicit alias or mapping table during `B2-001`
- do not let runtime and grading docs continue to drift silently

### 2. `provisional` wording currently risks sounding like a third external state

[WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md) currently says:

- `provisional`: must say `先記一筆粗估`

This is compatible with the user's intended product behavior only if it is interpreted as:

- already logged
- internal exactness posture is provisional

It becomes misleading if read as:

- a third persistence state
- something between draft and commit

Recommended action:

- rewrite this wording in `B2-001` so it clearly means `logged item with provisional posture`, not `third log state`

### 3. `meal_thread.provisional` and external `logged/draft` need explicit layer separation

[L0_PRODUCT_CAPABILITY_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md) lists `meal_thread` states including:

- `provisional`
- `committed`

B-2 now says:

- external outcome should remain `logged` vs `draft`
- `provisional` is an internal evidence or exactness posture

These can coexist, but only if the layer boundary is made explicit:

- internal thread state
- internal evidence posture
- external persisted outcome

Recommended action:

- add an explicit note during `B2-001` that these are different layers and must not be collapsed into one UI state model

## Implementation Debt

### 1. Retrieval intent object does not yet exist as a runtime contract surface

B-2 now depends on a structured retrieval-intent object, but this is still a draft concept and not yet enforced in runtime or tests.

### 2. Packet compression and recheck ownership are not yet fully formalized in runtime

B-2 correctly separates:

- deterministic hard recheck
- semantic recheck

but the runtime implementation seam is not yet built.

### 3. Large-DB or RAG adoption trigger is now defined in docs, but there is no operational audit yet that proves when corpus scale justifies upgrading beyond structured lookup

This is acceptable for P0. It is still a future implementation debt.

## A1 / A2 / A4 Alignment Notes

### A1 Functional Correctness

No current contradiction found.

B-2 keeps:

- ask-first for composition-unknown baskets
- commit path for estimable cases
- no-mutation distinction for query flows

### A2 Semantic / Product-Truth Correctness

B-2 is directionally strong here because it explicitly emphasizes:

- evidence honesty
- explicit uncertainty
- no fake exactness
- no snippet-as-truth

### A4 State Boundary Correctness

This is the most sensitive area.

B-2 remains aligned only if:

- unresolved stays draft
- follow-up does not silently turn into a hidden draft when estimability already exists
- `provisional` is not introduced as a third persisted state
- `clarify_before_estimate` remains reserved for true non-estimable cases

## Current Audit Conclusion

Current B-2 direction should proceed.

Recommended interpretation:

- no blocking semantic conflict
- no need to redesign B-2 direction
- do `B2-001` next as a contract and terminology sync slice

Do not jump to runtime implementation before the terminology bridge and wording cleanup are done.

## Recommended Next Slice

`B2-001 Phase B-2 contract freeze and terminology bridge`

Scope:

- align exactness vocabulary
- align `provisional` wording
- align internal vs external state terminology
- confirm `estimable -> logged` and `unresolved -> draft` across B-2 docs without changing canonical product meaning
