# Capability-to-Module Ownership Map

## Purpose

This thin map translates product capability families into module ownership and placement rules. It is a file-placement and dependency-direction guard, not a product journey, UX layout, runtime activation plan, or API contract.

Coding agents should read this when adding a new `app/*` package, choosing where a later-wave capability belongs, or changing import guards for `memory`, `recommendation`, `rescue`, proactive behavior, proposal inboxes, smart chips, or UI same-truth work.

## Non-Goals

- Do not use this file to define user-facing behavior, visual hierarchy, prompts, provider selection, DB schema, or mutation legality.
- Do not add empty symmetry files just because a capability has an owner row.
- Do not route around canonical specs. This map points to owners; the owner specs define product semantics.

## Upstream and Downstream

Upstream truth:

- `docs/specs/app_v2_ideal_architecture_final.md`
- `docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`
- `docs/specs/UX_TO_SYSTEM_CAPABILITY_GAP_MATRIX.md`
- `docs/specs/UI_CANONICAL_TRUTH_SURFACE_MATRIX.md`

Downstream enforcement:

- `config/active_code_policy.jsonc`
- `tests/test_domain_first_guardrails.py`
- `tests/test_architecture.py`
- `tests/test_v2_architecture_regression.py`
- `scripts/check_layer_integrity.py`
- `scripts/check_runtime_boundaries.py`
- `.importlinter`

## Ownership Matrix

| Capability family | Owner module | Allowed layer now | Forbidden placement | Activation cap now | Current examples |
|---|---|---|---|---|---|
| Intake manager loop, meal draft, commit boundary | `app/intake` with `app/runtime` contracts | Wave 1 active runtime | `app/routes.py`, root `app/schemas.py`, provider adapters | Active Wave 1 only | `intake_turn_orchestrator`, `intake_execution_orchestrator` |
| Nutrition evidence, synthesis, final mapping | `app/nutrition` | Wave 1 B2 active mainline | `app/runtime` semantic ownership, provider adapters | Active B2 mainline | local synthesis and evidence path work |
| Budget ledger and today sync | `app/budget` | Wave 1 active runtime | UI renderer, root facades, unrelated domains | Active Wave 1 only | today budget read path |
| Body plan, observation, calibration baseline | `app/body` | Wave 1 active runtime plus later calibration gates | ledger shortcuts, recommendation, rescue | Active baseline plus calibration proposal seam only | body plan routes and onboarding service |
| Retrieval and food knowledge metadata | `app/knowledge` or `app/nutrition` by source role | Spec or B2 mainline only | provider transport semantics, eval fixture shape | Contract-backed B2 work only | knowledge skeleton, B2 metadata specs |
| Proactive deterministic brakes | `app/runtime/application` plus `app/runtime/contracts` | Deterministic offline scaffold | scheduler, LINE push, LLM call, UI route | Offline diagnostic only | proactive deterministic gate |
| Durable memory and derived profile summaries | `app/memory` | Read-only offline sidecar | runtime entrypoints, shared, providers, durable write service | Offline sidecar scaffold | preference, golden-order, suppression summaries |
| Recommendation candidate quality | `app/recommendation` | Prepared-candidate offline sidecar | live search, Google Places, ranking LLM, proactive push | Offline sidecar scaffold | candidate quality gate |
| Rescue proposal read model | `app/rescue` | Read model scaffold | ledger mutation, accept overlay, DB migration, root facades | Offline sidecar scaffold | proposal read projection |
| Pending meal intent | `app/runtime/contracts` until semantics close | Contract only | intake handoff, recommendation acceptance, MealThread creation | Contract only | pending meal intent Pydantic contract |
| UI same-truth surfaces | UI/read-model owner per canonical matrix | Spec/read-model only | truth recomputation, mutation path, root schema growth | Spec only | UI canonical truth surface matrix |

## B2-Safe Parallel Readiness

This table records the current activation cap for parallel capability work while Wave 1 B2 semantic closure is the mainline. It is an implementation sequencing guard, not permission to activate product behavior.

| Slice | Capability | Current status | Owner | Allowed now | Blocked until activation plan |
|---|---|---|---|---|---|
| S0 | Spec/readiness alignment | `safe_now` | docs/governance | targeted spec alignment and ownership maps | large rewrites or new product semantics |
| S1 | Body target math | `safe_now` | `app/body` | deterministic formula tests and validators | LLM target calculation or persistence expansion |
| S2 | Onboarding bootstrap | `safe_now_with_existing_path` | `app/body`, `app/budget` | explicit onboarding completion -> BodyPlan -> DayBudgetLedger | silent bootstrap from observations, Manager integration, fixture rewrites |
| S3 | Budget same-truth read models | `safe_now_read_model` | `app/budget` | no-plan, overshoot, macro, and meal-summary consistency | read model food recomputation or ledger writes |
| S4 | BodyObservation ownership | `safe_now_existing_model` | `app/body` | body-owned write/read service and compatibility re-export | migration or automatic BodyPlan mutation |
| S5 | Exercise estimator | `contract_only` | `app/body` | MET/user-asserted estimate contract and deterministic tests | `ExerciseEvent` persistence, ledger bonus write |
| S6 | Calibration activation cap | `offline_only` | `app/body` | preview/model/gate tests and root-router non-activation guard | action route mounting, BodyPlan/ledger mutation activation |
| S7 | Recommendation quality gate | `offline_only` | `app/recommendation` | prepared-candidate quality gate | live search, Google Places, ranking LLM, B2 evidence object dependency |
| S8 | Memory derived summaries | `derived_summary_only` | `app/memory` | read-only preference/golden-order/suppression summaries | durable memory write, promotion service, LLM extraction |
| S9 | Proactive deterministic gate | `deterministic_brake_only` | `app/runtime` | quiet hours, cooldown, caps, suppression, evidence/quality thresholds | scheduler, push, LLM, route activation |
| S10 | Rescue read model | `read_model_only` | `app/rescue` | inbox/history projection and no raw trace leakage | accept/dismiss mutation, ledger overlay |
| S11 | Pending meal intent | `contract_only` | `app/runtime/contracts` | short-term context contract and status/expiry tests | service flow, intake handoff, recommendation acceptance |
| S12 | Architecture guard pack | `safe_now` | tests/scripts | root facade, import direction, non-activation, empty-file guards | weakening B2 architecture to fit sidecars |

## Guardrail

If a capability needs a field, state transition, mutation, live provider, scheduler, UI renderer, or manager-visible tool that is not already owned by its canonical module, stop and promote the decision through the relevant spec before adding code.

## Non-Blocking Architecture Debt

For the B2-safe parallel sidecar checkpoint, `lint-imports --config .importlinter` is diagnostic only. The expected current posture is that the sidecar and archive contracts stay kept, while broad runtime/shared and business-domain independence contracts may remain broken until a separate architecture refactor slice is approved.
