# Self-Use MVP Requirement Traceability Matrix

Status: DX0 audit artifact  
Date: 2026-05-07  
Claim scope: audit only, not a readiness claim

## Purpose

This document maps canonical self-use product truth against:

- the current local Accurate Intake shell scope
- current runtime and read-model evidence
- current tests and gates
- the highest-priority implementation and planning gaps

It exists to stop scope drift between:

1. whole-product canonical truth
2. the narrower local self-use foundation now being built
3. current runtime contracts and product pages

## Strategic Framing

```yaml
current_mainline: "Wave 1 B2 semantic closure plus Accurate Intake local self-use shell alignment"
is_detour: true
blocked_mainline: "Current shell and active plans are narrower than canonical self-use product truth, and several current-scope contracts are drifting"
detour_reason: "A DX0 traceability pass is required before more product-page or manager-surface work continues"
detour_exit_gate: "One audit artifact maps canonical product truth, active scope, runtime evidence, and top gaps"
exit_gate_status: "green_with_followup_work_remaining"
return_slice_after_exit: "DX1 macro contract recovery and tool-surface convergence"
strategic_verdict: "allowed_detour"
capability_layer: "L0 Product Operating Rules with L9 same-truth audit implications"
upstream_dependencies:
  - layer: "L0/L1 canonical product and runtime owner docs"
    contract_status: "contract_backed"
    risk_if_missing: "Would confuse product truth with local shell fixture truth"
slice_mode:
  - diagnostic_only
  - docs_and_governance
user_facing_behavior_changed: false
runtime_truth_changed: false
mutation_changed: false
safe_to_proceed_now: true
why_not_local_next_step_trap: "The repo already shows product-scope drift and contract drift; continuing implementation without a trace matrix would reinforce the wrong scope"
```

## Source Set

Primary canonical and planning sources:

- `docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md`
- `docs/quality/UX_JOURNEY_TO_SLICE_MAP.md`
- `docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`
- `docs/specs/UI_CANONICAL_TRUTH_SURFACE_MATRIX.md`
- `docs/specs/V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`
- `docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md`
- `docs/specs/WAVE_1_PHASE_B2_FOOD_KNOWLEDGE_METADATA_SPEC.md`
- `docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md`
- `docs/quality/ACCURATE_INTAKE_PL_CE_MVP_BUILD_ROADMAP.md`
- `docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md`

Primary runtime and test evidence sampled in this audit:

- `app/composition/current_budget_loader.py`
- `app/composition/payload_builders.py`
- `app/composition/accurate_intake_product_pages_renderer_source_map.py`
- `app/composition/non_fooddb_read_tool_executor.py`
- `app/composition/accurate_intake_manager_tool_surface_inventory.py`
- `app/composition/accurate_intake_responder_input_contract_fake_smoke.py`
- `app/runtime/application/execution_guard.py`
- `app/runtime/application/sidecar_service.py`
- `app/body/application/exercise_estimator.py`
- `tests/test_accurate_intake_product_pages_renderer_source_map.py`
- `tests/test_accurate_intake_pl_ce_product_pages_self_use_flow_gate.py`
- `tests/test_accurate_intake_responder_input_contract_fake_smoke.py`

## Normalized Verdict

The repo currently contains two different truths that have not been fully reconciled:

1. Canonical whole-product self-use truth:
   journeys `A-V` and capability families `F1-F8`
2. Active local build truth:
   a narrower local intake foundation limited to chat, today, body, bounded current-session/current-day context, and no proactive/rescue/recommendation/live-provider activation

That narrowed local shell is valid as a foundation slice, but it is not the same thing as the whole canonical self-use MVP app.

The main gap is therefore dual:

- whole-product capability closure is still incomplete by design
- even inside the narrowed current shell, several canonical contracts are still not aligned

The highest-risk current-scope drift is macro truth:

- macro fields are canonical in specs and read models
- Today product-page contracts do not yet mirror them
- responder honesty gates do not yet protect macro claims
- payload building still contains `macro_source: "llm_hint"` fallback behavior

## Capability Family Coverage

| Family | Canonical product scope | Active local shell status | Verdict | Owner track | Severity |
| --- | --- | --- | --- | --- | --- |
| F1 Plan Bootstrap & Fallback | Onboarding, no-plan fallback, body plan bootstrap | Present in shell and body routes, but still founder-gate pending | partial | Shared / PLCE | P0 |
| F2 Meal Thread Resolution | Single-turn intake, follow-up, clarify, correction | Core shell focus, but still not closure-proven across all A/B/C/D/K journeys | partial | Shared / PLCE | P0 |
| F3 Budget & Cross-Surface Sync | Today truth, overshoot, same-truth UI, macro visibility | Budget sync exists; macro and some same-truth fields are not fully wired to Today page | partial_with_drift | Shared / PLCE | P0 |
| F4 Rescue & Proposal Negotiation | Rescue flows F/F2/T | Explicitly deferred from current shell | deferred | Later-wave | P1 |
| F5 Body Observation & Calibration | G/H/I/U family | Weight and body-plan baseline exist; calibration and exercise remain partial or contract-only | partial_foundation_only | Shared / PLCE | P1 |
| F6 Recommendation & Preference Learning | L/M/Q/R/S | Explicitly deferred and offline-only | deferred | Later-wave | P1 |
| F7 Proactive Triggering | N/V | Explicitly deferred and no-send/offline-only | deferred | Later-wave | P1 |
| F8 Cross-Channel / Cross-Surface Experience | same-truth across chat/UI/surfaces | Chat/Today/Body shell exists, but only for a narrowed slice | partial_foundation_only | PLCE | P0 |

## Journey Traceability Matrix

Status vocabulary:

- `covered`: canonical truth, active scope, runtime path, and gate all align
- `partial`: some runtime and gate evidence exists, but closure is incomplete
- `deferred`: canonical journey exists but current shell explicitly does not activate it
- `drift`: current runtime or plan conflicts with canonical truth
- `missing`: canonical journey exists but current local shell has no active path

| ID | Product expectation | Canonical source family | Active scope and runtime evidence | Status | Severity | Owner | Recommended next slice |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | Onboarding complete flow | `L0_PRODUCT_CAPABILITY_SPEC`, `UX_JOURNEY_TO_SLICE_MAP`, `F1` | `/onboarding/bootstrap`, body page onboarding form, body-plan read model | partial | P0 | Shared / PLCE | Close founder gate for onboarding bootstrap and no-plan transitions |
| B | Single-turn intake plus budget sync | `UX_JOURNEY_TO_SLICE_MAP`, `F2`, `F3` | local chat shell, `/today/current-budget`, meal summaries, correction traces | partial | P0 | Shared / PLCE | Finish same-truth closure for chat and today |
| C | Pearl milk tea estimate with optional refinement | `UX_JOURNEY_TO_SLICE_MAP`, B2 follow-up semantics | pending follow-up and draft display are in current scope, but closure evidence is incomplete | partial | P0 | Shared / PLCE | Close estimate-with-follow-up runtime and human gate |
| D | Homemade meal blocking clarify | `UX_JOURNEY_TO_SLICE_MAP`, `F2` | clarify lane is canonical; current shell includes follow-up context and target candidates | partial | P0 | Shared / PLCE | Close blocking-clarify lifecycle evidence |
| E | Overshoot warning in UI and chat | `UX_JOURNEY_TO_SLICE_MAP`, `F3`, deep spec | remaining/consumed truth exists; overshoot UX closure not yet proven | partial | P0 | Shared / PLCE | Add same-truth overshoot gate across chat and Today |
| F | Rescue after overshoot | `UX_JOURNEY_TO_SLICE_MAP`, `F4` | explicitly out of scope for local shell | deferred | P1 | Later-wave | Do not activate before rescue owner plan |
| F2 | Planned large-meal rescue | `UX_JOURNEY_TO_SLICE_MAP`, `F4` | explicitly out of scope for local shell | deferred | P1 | Later-wave | Keep deferred until proposal/rescue activation plan exists |
| G | Weight update in chat, UI sync | `UX_JOURNEY_TO_SLICE_MAP`, `F5` | `body.record_observation` tool target exists; body page reads weight observations | partial | P0 | Shared / PLCE | Close chat-write to UI-read same-truth gate |
| H | Weight update in UI, chat can read | `UX_JOURNEY_TO_SLICE_MAP`, `F5`, `F8` | `/weight/observation` and `/weight/observations` exist in body page contract | partial | P0 | Shared / PLCE | Close UI-write to chat-read same-truth gate |
| I | Calibration proposal triggered by trend | `UX_JOURNEY_TO_SLICE_MAP`, `F5` | tool inventory and proposal contracts exist, but product-page shell does not surface a calibration inbox flow | partial | P1 | Shared / PLCE | Promote only after stored-proposal and UI surface plan align |
| J | No-onboarding degraded behavior | `UX_JOURNEY_TO_SLICE_MAP`, `F1`, current MVP goal | explicit no-plan honesty is current-wave truth, but still closure-pending | partial | P0 | Shared / PLCE | Verify no-plan degraded mode end to end |
| K | Item-level correction and removal | `UX_JOURNEY_TO_SLICE_MAP`, `F2`, `F3` | target-candidate context packs, remove-item commit path, supersede persistence, debug read model | partial | P0 | Shared / PLCE | Close target selection, ambiguity, and reload persistence gates |
| L | Food recommendation | `UX_JOURNEY_TO_SLICE_MAP`, `F6` | recommendation modules are offline-shadow only | deferred | P1 | Later-wave | Keep non-activated until recommendation activation plan |
| M | Preference memory | `UX_JOURNEY_TO_SLICE_MAP`, `F6`, memory specs | memory modules are offline-sidecar only | deferred | P2 | Later-wave | Keep non-activated until memory truth owner is active |
| N | Proactive nudges | `UX_JOURNEY_TO_SLICE_MAP`, `F7` | proactive deterministic gate and no-send evaluator only | deferred | P2 | Later-wave | Keep no-send only |
| O | Photo intake | `UX_JOURNEY_TO_SLICE_MAP`, `F2`, multimodal | canonical only; no active local shell path | deferred | P2 | Later-wave | Hold behind multimodal plan |
| P | Voice intake | `UX_JOURNEY_TO_SLICE_MAP`, `F2`, voice | canonical only; no active local shell path | deferred | P2 | Later-wave | Hold behind voice input plan |
| Q | Pre-meal planning | `UX_JOURNEY_TO_SLICE_MAP`, `F6` | no active local shell path | deferred | P2 | Later-wave | Keep deferred |
| R | Menu scan recommendation | `UX_JOURNEY_TO_SLICE_MAP`, `F6`, multimodal | no active local shell path | deferred | P2 | Later-wave | Keep deferred |
| S | Swap suggestion | `UX_JOURNEY_TO_SLICE_MAP`, `F6` | no active local shell path | deferred | P2 | Later-wave | Keep deferred |
| T | Event-day budget allocation | `UX_JOURNEY_TO_SLICE_MAP`, `F4`, `F6` | no active local shell path | deferred | P1 | Later-wave | Keep deferred |
| U | Exercise input adjusts effective budget | `UX_JOURNEY_TO_SLICE_MAP`, body owner map | deterministic estimator contract exists, but no active shell endpoint or Today integration path is declared | missing | P1 | Shared / PLCE | Decide whether U is in current self-use target; if yes, add route, ledger effect, and Today read-model gate |
| V | Weekly insight | `UX_JOURNEY_TO_SLICE_MAP`, `F7` | weekly read-model fields exist in body page, but proactive insight product flow is not active | deferred | P2 | Later-wave | Keep deferred until proactive activation plan |

## Cross-Cutting Requirement Matrix

| Requirement | Canonical truth | Runtime or test evidence | Verdict | Severity | Owner | Recommended next slice |
| --- | --- | --- | --- | --- | --- | --- |
| Manager-controlled ReAct loop and trace | Wave 1 bootstrap, deep spec, minimal contracts | active shell and diagnostics expose manager/runtime artifacts, but this audit did not re-grade full pass1/pass2 closure | partial | P1 | Shared | Keep using trace-first verification, but do not reopen Phase A as a detour |
| Context engineering stays bounded and non-authoritative | current shell docs, manager context policy, target-candidate diagnostics | bounded current-session/current-day context is explicit; proactive/rescue/recommendation context is intentionally omitted | partial | P1 | PLCE | Maintain bounded context and finish correction/clarify target-candidate closure |
| Responder allowed-facts honesty | deep spec and fake-smoke contract | current fake-smoke blocks invented logged status, remaining, exactness, target selection, readiness | partial_with_gap | P0 | Shared | Extend allowed-fact and forbidden-claim coverage to macro claims |
| Macro visibility and no invented macro truth | minimal contracts, deep spec, UI truth matrix | canonical read model exists, but payload fallback uses `llm_hint`; Today page contract omits macro mirror; guard reasons are narrower than spec | drift | P0 | Shared / PLCE | DX1 macro contract recovery |
| Today and Body same-truth UI surfaces | UI canonical truth matrix | product pages enforce budget/meal/body basics, but macro fields and some later-wave surfaces are absent | partial_with_drift | P0 | PLCE | Expand same-truth renderer contract only where canonical read models already exist |
| Tool-surface convergence | PLCE roadmap target coarse tool inventory | runtime still aliases coarse names to `read_day_budget` and `read_body_plan`; some direct-lane debt remains | drift | P0 | Shared / PLCE | MR2c-style coarse tool surface convergence |
| FoodDB evidence and macro metadata | B2 metadata spec plus current MVP goal | canonical metadata already supports macro candidates and exact-item macro fields, but Product Loop still waits on approved packet-ready evidence | partial_foundation_only | P1 | FDB / Shared | Shadow macro schema expansion before runtime promotion |
| Recommendation, rescue, proactive non-activation discipline | owner map and current MVP scope docs | offline-sidecar and no-send contracts are present and guarded | covered_for_current_scope | P1 | Later-wave | Preserve non-activation until later-wave owner plan |
| Exercise write path and Today effective-budget sync | journey U, owner map | estimator contract exists; shell route and page contract do not | missing | P1 | Shared / PLCE | Either explicitly defer in scope docs or implement end-to-end slice |
| Founder / human gate coverage | UX journey map | all listed journeys remain `pending` in the journey map | missing | P0 | Shared | Convert core current-scope journeys into an explicit founder gate sequence |

## Concrete Runtime Drift Notes

### 1. Macro fallback drift

Canonical specs already define macro truth, macro visibility, and hidden-state reasons.

Current runtime drift:

- `app/composition/payload_builders.py` falls back to `macro_source: "llm_hint"` with low confidence
- `app/composition/accurate_intake_responder_input_contract_fake_smoke.py` does not block invented macro claims
- `app/composition/accurate_intake_product_pages_renderer_source_map.py` does not require Today macro mirror fields
- `app/runtime/application/execution_guard.py` currently returns a narrower guard vocabulary than the canonical spec

This is the most important current-scope alignment gap.

### 2. Tool-surface drift

Canonical direction:

- current roadmap uses coarse public tool names

Current runtime drift:

- `app/composition/non_fooddb_read_tool_executor.py` still maps those names back to `read_day_budget` and `read_body_plan`
- `app/composition/accurate_intake_manager_tool_surface_inventory.py` still records direct-lane debt such as `estimate_body_observation_record_weight` and `estimate_calibration_budget_delta_direct_mutation`

This means the repo is still partly executing through compatibility vocabulary instead of the target surface.

### 3. Product pages are narrower than canonical read-model truth

Canonical Today truth already includes:

- daily budget summary
- meal summaries
- macro visibility state

Current Today page contract only requires:

- kcal summary fields
- meal summaries
- status

Macro fields are missing from the page contract even though the read model already computes them.

### 4. Exercise is specified but not activated

Canonical journey `U` expects:

- exercise intake
- deterministic estimate
- exercise event plus budget effect
- Today effective-budget reflection

Current repo state only proves:

- exercise estimate contract
- no mutation authority inside the estimator

No active local shell route or Today page contract was found for an exercise write flow.

## Top P0 Gaps

1. Macro contract recovery across payload, responder, read model, renderer, and guard reasons.
2. Tool-surface convergence from coarse public names to real runtime ownership without legacy alias dependence.
3. Core current-scope journey closure for `A/B/C/D/E/G/H/J/K`, with founder-gate evidence instead of only fixture evidence.
4. Product-page same-truth expansion to match already-canonical Today truth, especially macro visibility.
5. Explicit scope discipline: keep later-wave capabilities deferred, but stop letting the local shell masquerade as whole-product self-use closure.

## Proposed PR Train Update

```yaml
DX0:
  name: "Self-use MVP requirement traceability baseline"
  status: "this document"
  outcome:
    - "canonical whole-product truth separated from current shell truth"
    - "P0 current-scope drifts identified"

DX1:
  name: "Macro contract recovery"
  scope:
    - "remove or quarantine llm_hint macro fallback"
    - "extend responder honesty to macro claims"
    - "add Today macro mirror fields to renderer/source-map contract"
    - "align guard-reason vocabulary with canonical spec"

DX2:
  name: "Coarse tool surface convergence"
  scope:
    - "reduce legacy alias dependence"
    - "realign diagnostics, harnesses, and runtime to public coarse tool names"

DX3:
  name: "Core current-scope journey closure"
  scope:
    - "A/B/C/D/E/G/H/J/K founder-gate sequence"
    - "same-truth checks across chat, today, and body"

DX4:
  name: "Exercise scope decision"
  scope:
    - "either formally defer journey U from current shell target"
    - "or implement route plus ledger/read-model integration"

FDB-M1:
  name: "FoodDB shadow macro schema expansion"
  scope:
    - "keep runtime promotion off"
    - "align macro metadata, completeness counts, and packet exposure preparation"

Later-wave:
  name: "Rescue, recommendation, proactive, multimodal activation"
  scope:
    - "remain deferred until owner plans are explicit"
```

## Gate Gap Notes

- The journey map still marks all listed journeys as `pending`; this means canonical UX closure has not been converted into an active founder-gate ledger yet.
- Product-page tests are strong on no-frontend-truth rules for kcal and target calculation, but they do not yet enforce Today macro mirror fields.
- Responder input fake-smoke is already useful, but it does not yet protect macro honesty.
- Later-wave recommendation, rescue, and proactive modules are appropriately non-activated; this is not a bug unless scope claims blur.
- Current shell docs correctly avoid readiness claims, but naming such as "self-use MVP" can still be misread unless this narrower scope is stated every time.

