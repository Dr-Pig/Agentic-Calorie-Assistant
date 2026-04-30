# UI Canonical Truth Surface Matrix

## Purpose

This document defines the allowed read-only mapping between future UI surfaces and existing canonical product truth.

It exists to prevent L9 UI / same-truth work from becoming a parallel source of truth while Wave 1 B2 semantic closure remains the current mainline.

## Non-Goals

- Do not define visual layout, typography, animation, component hierarchy, or brand style.
- Do not add runtime behavior, schemas, endpoints, database fields, renderer code, eval semantics, or mutation paths.
- Do not promote trace, sidecar, replay-pack, or benchmark fixture vocabulary into user-facing product truth.
- Do not let Ryo Lu-inspired product taste change contracts or workflow semantics; use that reference only for clarity, restraint, and information architecture.

## Upstream Docs

- `docs/specs/APP_V2_ENGINEERING_OPERATING_ENTRY.md`
- `docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`
- `docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md`
- `docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`
- `docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md`
- `docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md`
- `docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md`
- `docs/specs/V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`
- `docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md`
- `docs/quality/V2_WAVE_1_CAPABILITY_MICRO_SUITES.md`
- `docs/quality/V2_WAVE_1_MICRO_SUITE_CASES.md`

## Downstream Use

- Required before implementing L9 UI same-truth, UI renderers, smart-chip action wiring, proposal inbox UI, proactive UI, or cross-surface sync tests.
- Optional during B2 unless a B2 change exposes a new user-visible UI fact or action.
- Coding agents should read this only when touching UI-visible facts, UI actions, sidecar payloads, same-truth surfaces, or cross-surface acceptance criteria.

## Strategic Gate

```yaml
current_mainline: Wave 1 B2 semantic closure, evidence/synthesis alignment, final mapping boundary
is_detour: true
blocked_mainline: not_blocked
detour_reason: Read-only L9 surface inventory exposes same-truth dependencies without changing runtime truth or UI behavior.
detour_exit_gate: Every UI-visible datum/action maps to an existing canonical owner/read model, or is explicitly marked gap/deferred.
exit_gate_status: defined_by_this_matrix
return_slice_after_exit: B2 final mapping and evidence/synthesis closure
strategic_verdict: allowed_detour
```

## Capability Dependency Check

```yaml
capability_layer: L9 Same-Truth / UI / Memory / Proactive
upstream_dependencies:
  - layer: L0 Product Operating Rules
    contract_status: contract_backed
    risk_if_missing: UI could stop being chat-first and become a competing primary surface.
  - layer: L1-L3 InteractionEvent, AttachmentDecision, MealThread/Draft/Commit
    contract_status: contract_backed
    risk_if_missing: UI actions could bypass manager/guard/commit boundaries.
  - layer: L4-L7 Retrieval, Evidence, Synthesis, Final Mapping
    contract_status: draft_to_contract_backed_B2_mainline
    risk_if_missing: UI could canonize unresolved exactness, evidence, or food semantics.
  - layer: L8 Mutation/Ledger/Version
    contract_status: contract_backed_baseline
    risk_if_missing: UI could show calories, macros, overshoot, or logged state from a forked computation.
slice_mode:
  - diagnostic_only
  - producer_honesty_only
  - architecture_mapping
user_facing_behavior_changed: false
runtime_truth_changed: false
mutation_changed: false
safe_to_proceed_now: true
why_not_local_next_step_trap: No code behavior, schema, endpoint, renderer, or product semantics are added; the slice only identifies owners, gaps, and stop conditions.
```

## Best-Practice Evidence

```yaml
required: true
sources_checked:
  - official_or_primary_source: Microsoft Guidelines for Human-AI Interaction
    url: https://www.microsoft.com/en-us/research/articles/guidelines-for-human-ai-interaction-eighteen-best-practices-for-human-centered-ai-design/
  - official_or_primary_source: Apple Human Interface Guidelines - Generative AI
    url: https://developer.apple.com/design/human-interface-guidelines/generative-ai
  - official_or_primary_source: Google People + AI Guidebook - User Needs
    url: https://pair.withgoogle.com/guidebook-v2/chapters/user-needs/
  - official_or_primary_source: IBM Design for AI - Explainability
    url: https://www.ibm.com/design/ai/ethics/explainability/
  - official_or_primary_source: OpenAI Structured Outputs
    url: https://openai.com/index/introducing-structured-outputs-in-the-api/
  - official_or_primary_source: Vercel AI SDK UI
    url: https://ai-sdk.dev/docs/ai-sdk-ui/overview
adopted_guidance:
  - Keep users informed about AI capability, limitation, uncertainty, and recoverability.
  - Keep high-responsibility diet, body, and mutation decisions under user control.
  - Separate model/provider behavior from user experience and stable product contracts.
  - Prefer structured contracts and tool-result rendering over freeform UI truth.
rejected_guidance:
  - Do not adopt generative UI as permission for an LLM to define product truth, actions, or state transitions.
  - Do not use rich UI components as a substitute for canonical read models and guards.
conflict_with_repo_habits:
  - Existing diagnostic traces are useful evidence, but they are not user-facing product truth.
  - Current simple HTML surfaces may render canonical values, but visual correctness is not enough without owner alignment.
how_the_design_changed:
  - The first UI step is a truth-surface matrix, not component design.
  - Every future UI field/action must name its canonical owner before renderer work begins.
```

## LLM / Deterministic Boundary

```yaml
decision_surface: UI-visible facts, UI actions, sidecar render payloads, same-truth checks
truth_owner: hybrid
deterministic_role: validate | derive_from_canonical_read_model | reject | downgrade | mirror
llm_role: synthesize | classify | explain
do_not_override:
  - manager intent
  - food identity or evidence exactness
  - commit/draft state
  - ledger mutation truth
  - budget math
  - macro visibility
  - proposal legality
  - workflow routing
```

## Semantic Owners

```yaml
user_intent: manager_llm_with_contract_guards
food_semantics: intake_manager_and_evidence_synthesis
routing_or_workflow_effect: manager_decision_plus_transition_guards
mutation_legality: deterministic_domain_workflows_and_execution_guard
persistence_truth: owning_domain_models_and_read_models
ui_truth: none
ui_role: render_mirror_confirm_or_launch_existing_command
```

## Status Vocabulary

- `available`: canonical owner and read path already exist.
- `diagnostic_only`: trace or sidecar evidence exists, but it is not a user-facing product surface.
- `deferred`: product object exists or is planned, but UI display/action is not yet authorized for implementation.
- `gap`: no canonical owner/read path exists; stop before UI implementation.

## Surface Matrix

| User Job | UI Surface | Displayed Fact | Canonical Object | Truth Owner | Read Model / API | Sidecar / Trace Evidence | Allowed Action | Target Event / Command | Forbidden Inference | Upstream Dependency | Acceptance Gate | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| See today's calorie state | Today dashboard | budget, consumed, adjustment, remaining, meal count, meal summaries | `CurrentBudgetView`, `DayBudgetLedger` | `budget` domain | `/today/current-budget`, `/today` | sidecar budget summary, `phase_c_trace.same_truth_read_result` | refresh/read only | none | recomputing remaining or overshoot in renderer | L0B, L8 | MS9, MS11, MS12 | available |
| See whether macros may be shown | Today dashboard | consumed protein/carbs/fat only when visible, guard reason when hidden | `CurrentBudgetView` | `budget` plus macro visibility policy | `/today/current-budget` | sidecar `macro`, Phase C macro visibility status | refresh/read only | none | showing macros when `show_macro=false`; deriving macro trust from wording | L6-L8 | MS10, MS12 | available |
| Review active meal summaries | Today dashboard | active meal title, kcal, occurred time, resolution status | `CurrentBudgetView.meals`, `MealThread`, `MealVersion` | `intake` for meal truth, `budget` for today projection | `/today/current-budget`, `/today` | sidecar mutation summary, Phase C mutation outcome | open existing meal review only after route contract exists | `InteractionEvent(surface_mode=ui_anchored_action)` | treating summary rows as full meal semantic evidence | L1-L3, L8 | MS7, MS9, MS11 | available for summary; deferred for full review |
| Understand current body plan | Body plan dashboard | daily budget, recommended target, deficit, safety floor, TDEE, goal, profile status | `ActiveBodyPlanView`, `BodyPlan`, `BodyProfile` | `body` domain | `/body-plan/active`, `/body-plan` | sidecar active body plan view | refresh/read only | none | recalculating TDEE, target kcal, or safety floor in UI | L0A, L0B | onboarding/body-plan happy path gates | available |
| Record or review body observation | Weight surface | weight observation value, unit, observed date, source | `BodyObservation` | `body` domain | `/weight` | not required for intake same-truth | submit through existing body observation path | body observation command | turning observation into calibration proposal without proposal gate | L3.5 body workflow | body observation workflow tests | available |
| Confirm meal correction or commit from UI | Future meal review / smart chip | proposed target meal/thread and action affordance | `MealThread`, `MealVersion`, transition guard result | `intake` plus `runtime` guard | not yet authorized as standalone UI path | Phase A trace, Phase C trace | launch guarded action only | `InteractionEvent(surface_mode=ui_anchored_action)` routed through manager/guard | direct ledger mutation, direct commit, keyword-based target inference | L1-L3, L8 | MS7, MS9, MS11 | deferred |
| Inspect calibration or rescue proposal | Proposal inbox mirror | current open proposal, primary option, option summaries, status | `ProposalContainer`, `ProposalOption` | owning domain plus manager proposal policy | no general proposal inbox read model yet | calibration response `ui_hints` only where produced | accept/defer/reject only through proposal command path | proposal response command | letting UI host primary negotiation or invent options | L0, L2, L8 | proposal-specific acceptance gate | deferred |
| See proactive nudge context | Notification / proactive card | trigger status, trigger reason, linked context | `ProactiveTrigger` | proactive scheduler plus owning domain | no active Wave 1 proactive UI read model | scheduler trace when implemented | open chat or dashboard context only | proactive engagement event | auto-logging, auto-accepting, or inventing recommendation rationale | L9 proactive plus L4/L5 evidence | proactive scheduler gates | deferred |
| Debug same-truth closure | Internal diagnostics only | mutation outcome, same-truth read result, hard-fail conditions | trace artifacts, `phase_c_trace` | runtime diagnostics | request trace artifacts | `phase_c_trace.same_truth_closure_gate` | inspect only | none | exposing diagnostic labels as user-facing product status | Phase C baseline | MS12 | diagnostic_only |
| Display memory or history summary | Future history / memory surface | stable user preference or history summary | memory model, meal/body history read models | owning domain plus memory layer | no Wave 1 user-facing memory UI read model | not active | read only until memory contract exists | future memory command | summarizing raw history into canonical preference without memory contract | L4A, L9 memory | memory acceptance gates | deferred |

## Action Wiring Rules

| Action Class | Rule | Stop Condition |
|---|---|---|
| Read-only dashboard refresh | May read existing canonical read models and render supplied values. | Stop if renderer must compute missing truth. |
| UI-anchored correction / confirmation | Must re-enter `InteractionEvent`, attachment/transition guards, manager decision, and domain workflow. | Stop if direct mutation is proposed from UI. |
| Proposal accept / defer / reject | Must use proposal command path owned by the relevant domain and manager policy. | Stop if UI creates, ranks, or rewrites proposal options. |
| Smart chip / shortcut | May only launch an already-defined command with explicit target identity. | Stop if chip label requires new routing semantics. |
| Diagnostic trace inspection | Internal only; may support engineering review. | Stop if trace labels become product copy or user-visible truth. |

## Renderer Rules

- UI may render, filter, group, collapse, sort, and explain supplied canonical values.
- UI may show unavailable, hidden, pending, or deferred states when those states are supplied by canonical owners.
- UI must not compute calories, remaining budget, overshoot, macro visibility, evidence exactness, logged status, proposal legality, or workflow routing.
- UI must not parse assistant reply text as a truth source.
- UI must not promote benchmark fixture fields, runner vocabulary, or replay-pack labels into product architecture.

## Stop Conditions

- A UI card requires a field with no canonical owner.
- A UI action bypasses manager, guard, draft/commit, or ledger mutation boundaries.
- A renderer needs to infer food semantics, evidence quality, exactness, budget math, macro policy, proposal status, or commit state.
- Diagnostic sidecar/trace vocabulary is about to become user-facing product copy.
- Visual design, animation, layout, or taste decisions would change data contracts or workflow semantics.
- A future implementation touches API/schema/database/runtime/provider files before this matrix row is available or explicitly deferred.

## Test And Review Gates

- Static review must confirm every matrix row resolves to `available`, `diagnostic_only`, `deferred`, or `gap`.
- Governance review must confirm no runtime truth, user-facing behavior, mutation, schema, endpoint, or renderer implementation was introduced by this document.
- Future UI implementation must cross-check MS7, MS9, MS10, MS11, and MS12 before claiming same-truth readiness.
- Markdown encoding must pass `python scripts/check_markdown_encoding.py --policy-docs --require-bom` after edits.

## Current Verdict

The matrix is an allowed detour only as a read-only architecture mapping. After this document is created, default execution should return to Wave 1 B2 semantic closure unless a future UI-visible field/action exposes a concrete canonical-truth gap.
