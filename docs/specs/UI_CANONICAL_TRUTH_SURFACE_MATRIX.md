# UI Canonical Truth Surface Matrix

## Purpose

This document defines the allowed read-only mapping between CurrentShell and future UI surfaces and existing canonical product truth.

It exists to prevent L9 UI / same-truth work from becoming a parallel source of truth while CurrentShell self-use MVP local desktop dogfood remains the current mainline.

## Advanced Product Surface Policy

Current product direction is chat-primary with aligned UI mirrors:

- Chat is the primary interaction surface for intake, rescue, recommendation, proactive, memory confirmation, and calibration negotiation.
- UI/dashboard surfaces should mirror relevant state, status, history, proposals, controls, and review context, but they do not own product truth.
- Buttons, chips, cards, or dashboard controls are allowed only as explicit structured events into Manager / guard / domain workflow.
- UI must not parse assistant text, button labels, card position, or fixture labels as authorization for mutation.
- Do not introduce a generic "inbox" as a primary product concept. Capability-specific proposal mirrors, history views, dashboards, and control surfaces must be specified by canonical owner before implementation.

## Non-Goals

- Do not define visual layout, typography, animation, component hierarchy, or brand style.
- Do not add runtime behavior, schemas, endpoints, database fields, renderer code, eval semantics, or mutation paths.
- Do not promote trace, sidecar, replay-pack, or benchmark fixture vocabulary into user-facing product truth.
- Do not let Ryo Lu-inspired product taste change contracts or workflow semantics; use that reference only for clarity, restraint, and information architecture.

## Upstream Docs

- `docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md`
- `docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md`
- `docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml`
- `docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml`
- `docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md`
- `docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md`
- `docs/specs/L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md`
- `docs/specs/CAPABILITY_TO_MODULE_OWNERSHIP_MAP.md`

## Downstream Use

- Required before implementing L9 UI same-truth, UI renderers, smart-chip action wiring, proposal inbox UI, proactive UI, or cross-surface sync tests.
- Optional unless a CurrentShell/AppShell change exposes a new user-visible UI fact or action.
- Coding agents should read this only when touching UI-visible facts, UI actions, sidecar payloads, same-truth surfaces, or cross-surface acceptance criteria.

## Strategic Gate

```yaml
current_mainline: CurrentShell self-use MVP local desktop dogfood
is_detour: true
blocked_mainline: not_blocked
detour_reason: Read-only L9 surface inventory exposes same-truth dependencies without changing runtime truth or UI behavior.
detour_exit_gate: Every UI-visible datum/action maps to an existing canonical owner/read model, or is explicitly marked gap/deferred.
exit_gate_status: defined_by_this_matrix
return_slice_after_exit: CurrentShell self-use MVP local desktop dogfood
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
    contract_status: contract_backed_for_current_shell_baseline
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
| Inspect calibration or rescue proposal | Proposal inbox mirror | current open proposal, primary option, option summaries, status | `ProposalContainer`, `ProposalOption` | owning domain plus manager proposal policy | calibration public contract: `/calibration/proposals/open` via root-mounted `public_router`; rescue: no general proposal inbox read model yet | calibration response `ui_hints` only where produced | accept/defer/reject only through proposal command path | calibration public contract: `/calibration/proposal/stored-action` via root-mounted `public_router`; rescue: future proposal response command | letting UI host primary negotiation, invent options, or call internal direct-payload calibration actions | L0, L2, L8 | proposal-specific acceptance gate | contract_ready for calibration mirror; public route activation active; rescue deferred |
| See proactive nudge context | Notification / proactive card | trigger status, trigger reason, linked context | `ProactiveTrigger` | proactive scheduler plus owning domain | no active CurrentShell proactive UI read model | scheduler trace when implemented | open chat or dashboard context only | proactive engagement event | auto-logging, auto-accepting, or inventing recommendation rationale | L9 proactive plus L4/L5 evidence | proactive scheduler gates | deferred |
| Debug same-truth closure | Internal diagnostics only | mutation outcome, same-truth read result, hard-fail conditions | trace artifacts, `phase_c_trace` | runtime diagnostics | request trace artifacts | `phase_c_trace.same_truth_closure_gate` | inspect only | none | exposing diagnostic labels as user-facing product status | Phase C baseline | MS12 | diagnostic_only |
| Display memory or history summary | Future history / memory surface | stable user preference or history summary | memory model, meal/body history read models | owning domain plus memory layer | no active CurrentShell user-facing memory UI read model | not active | read only until memory contract exists | future memory command | summarizing raw history into canonical preference without memory contract | L4A, L9 memory | memory acceptance gates | deferred |

## BodyBudget CurrentShell Integration Readiness Matrix

This matrix freezes the BodyBudget read-model names that CurrentShell AppShell/WebCell surfaces and later Context Engineering may reference.

It does not authorize frontend math, CE packet changes, ManagerContextPacket changes, automatic calibration, recommendation, rescue, proactive behavior, or new mutation paths. If CurrentShell needs a BodyBudget field not listed here, stop and add or extend a backend read model first.

The machine-readable readiness artifact mirrors this matrix through `current_shell_contract.integration_readiness_matrix`; the artifact is a contract check, not a frontend fallback or alternate truth store.

| Stable Read Model Name | Backend Route / Read Function | Truth Owner | CurrentShell Allowed Use | Stable Field Contract | Forbidden CurrentShell Behavior | Readiness Gate |
|---|---|---|---|---|---|---|
| `current_budget_view` | `/today/current-budget`; `app.composition.current_budget_read_model.build_current_budget_view` | `budget` domain for budget math; `intake` domain for active meal truth | Render today's budget, consumed, remaining, meal count, meal summaries, and macro visibility exactly as supplied. | `budget_kcal`, `consumed_kcal`, `adjustment_kcal`, `remaining_kcal`, `active_meal_count`, `meals[]`, `show_macro`, `macro_guard_reason`, `last_recomputed_at` | Do not recompute consumed, remaining, meal inclusion, overshoot, adjustment sign, or macro visibility. | `tests/test_budget_ledger_truth_boundary.py`; `tests/test_product_loop_mvp_read_model.py`; `/today/current-budget` smoke |
| `body_budget_deficit_summary` | `/today/deficit-summary`; `app.composition.body_budget_deficit_summary.build_body_budget_deficit_summary` | `body` owns plan/weight truth; `budget` owns ledger math; composition assembles read-only deficit observation | Render the deficit observation loop: active target, consumed, remaining, estimated daily deficit, latest weight, and weight-history count. `deficit_summary` is shorthand only; CurrentShell contract references must use `body_budget_deficit_summary`. | `source_kind`, `read_only`, `truth_owner`, `target_available`, `target_source`, `active_daily_target_kcal`, `recommended_target_kcal`, `consumed_kcal`, `adjustment_kcal`, `remaining_kcal`, `estimated_daily_deficit_kcal`, `latest_weight_kg`, `latest_weight_observed_at`, `latest_weight_observation_id`, `weight_history_count`, `current_budget`, `active_body_plan` | Do not calculate TDEE, target kcal, remaining kcal, estimated deficit, latest weight, trend, or target-source legality in CurrentShell. | `tests/test_body_budget_deficit_summary.py`; `tests/test_body_budget_sync_diagnostic.py`; `/today/deficit-summary` smoke |
| `body_budget_weekly_progress` | `/today/weekly-progress`; `app.composition.body_budget_weekly_progress.build_body_budget_weekly_progress` | `body` owns weight observations; `budget` owns daily budget math; composition assembles read-only weekly progress | Render a seven-day deficit/progress surface from backend day rows and aggregate fields. | `source_kind`, `read_only`, `window_start_date`, `window_end_date`, `window_days`, `days[]`, `logged_day_count`, `target_available_day_count`, `total_consumed_kcal`, `total_remaining_kcal`, `estimated_weekly_deficit_kcal`, `weight_observation_count`, `first_weight_kg`, `latest_weight_kg`, `weight_delta_kg`, `weight_delta_policy` | Do not compute weekly deficit, weight delta, or logged-day coverage in CurrentShell; do not infer trend, calibration eligibility, rescue, recommendation, or proactive behavior from this read model. | `tests/test_body_budget_weekly_progress.py`; `/today/weekly-progress` smoke |
| `body_budget_effective_budget_view` | `/today/effective-budget`; `app.composition.body_budget_effective_budget.build_body_budget_effective_budget_view` | `budget` owns ledger math; composition exposes adjustment-layer read model and sign-policy trace | Render backend-supplied effective budget posture, adjustment layer totals, current runtime sign policy, canonical formula status, and calibration adjustment entry capability flag. | `source_kind`, `read_only`, `truth_owner`, `ledger_present`, `base_budget_kcal`, `consumed_kcal`, `runtime_adjustment_total_kcal`, `runtime_effective_budget_kcal`, `remaining_kcal`, `remaining_formula`, `adjustment_layers.manual_adjustment_total_kcal`, `adjustment_layers.calibration_adjustment_total_kcal`, `adjustment_layers.rescue_overlay_total_kcal`, `adjustment_layers.signed_effective_budget_delta_kcal`, `adjustment_layers.runtime_adjustment_total_from_entries_kcal`, `entry_breakdown`, `sign_policy`, `calibration_adjustment_ledger_entry_enabled` | Do not calculate effective budget, adjustment layer totals, or sign policy in CurrentShell; do not create calibration adjustment entries outside accepted stored proposal actions with explicit backend effect payload; do not reinterpret signed layers outside the backend budget math helper. | `tests/test_body_budget_effective_budget_read_model.py`; `tests/test_budget_effective_budget_math.py`; `/today/effective-budget` smoke |
| `active_body_plan_view` | `/body-plan/active`; `app.body.application.active_body_plan_read_model.build_active_body_plan_view` | `body` domain | Render active plan, recommended target, manual target posture, deficit, safety floor, TDEE, profile status, and baseline profile fields. | `body_plan_id`, `plan_status`, `goal_type`, `current_weight_kg`, `target_weight_kg`, `daily_budget_kcal`, `recommended_target_kcal`, `daily_deficit_kcal`, `safety_floor_kcal`, `estimated_tdee`, `target_pace_kg_per_week`, `plan_source`, `profile_status`, `last_updated_at` | Do not run BMR/TDEE formulas, infer manual override legality, mutate target, or treat profile current weight as latest observation. | `tests/test_active_body_plan_read_model.py`; `tests/test_weight_route_body_plan_boundary.py`; `/body-plan/active` smoke |
| `calibration_proposal_inbox` | Public route `/calibration/proposals/open`; root app mounts `public_router` from `app.composition.calibration_routes.public_router`; full internal router remains `app.composition.calibration_routes.router`; read function `app.composition.calibration_proposal_inbox.load_open_calibration_proposal_inbox` returns `ProposalContainer` | calibration proposal artifacts over `ProposalContainer` / `ProposalOption`; route projection owns CurrentShell-safe payload shape | Render open calibration proposals as an inbox mirror and launch existing stored proposal actions through `public_router`. | Route projection fields: `proposal_container_id`, `proposal_type`, `proposal_status`, `top_option_id`, `local_date`, `proposal_family`, `created_at`, `accepted_at`, `options[].proposal_option_id`, `options[].option_type`, `options[].option_label`, `options[].option_summary`, `options[].rank_order`, `options[].is_primary`, `options[].effect_payload`. Read function domain fields: `ProposalContainer.user_id`, `ProposalContainer.metadata`, and `ProposalContainer.options`; metadata-derived fields are not direct read-function fields. | Do not expose full diagnostic metadata, policy packets, or trace envelopes; do not create, rank, rewrite, accept, defer, or reject proposals outside `/calibration/proposal/stored-action`; do not mount the full internal calibration router into the root app; `/calibration/proposal/action` and manual model-input `/calibration/proposal/preview` stay internal diagnostic contracts. | `tests/test_calibration_proposal_inbox.py`; `tests/test_calibration_routes.py`; `tests/test_calibration_activation_cap.py`; root public route smoke active |
| `calibration_proposal_history` | Public route `/calibration/proposals/history`; root app mounts `public_router` from `app.composition.calibration_routes.public_router`; full internal router remains `app.composition.calibration_routes.router`; read function `app.composition.calibration_proposal_inbox.load_calibration_proposal_history` returns `ProposalContainer` | calibration proposal artifacts over `ProposalContainer` / `ProposalOption`; route projection owns CurrentShell-safe audit payload shape | Render accepted, rejected, dismissed, expired, and open calibration proposals as a read-only audit mirror while preserving backend ordering. | Route projection fields: `proposal_container_id`, `proposal_type`, `proposal_status`, `top_option_id`, `local_date`, `proposal_family`, `created_at`, `accepted_at`, `expired_at`, `expiry_reason`, `primary_option_type`, `primary_option_label`, `primary_option_summary`. Read function domain fields remain `ProposalContainer.user_id`, `ProposalContainer.metadata`, and `ProposalContainer.options`; metadata-derived fields are not direct read-function fields and the route does not expose `options[]` or `effect_payload`. | Do not accept, defer, reject, dismiss, or expire proposals from history; do not expose `options[]`, `effect_payload`, full diagnostic metadata, policy packets, or trace envelopes; do not infer calibration eligibility, plan changes, budget effects, rescue, recommendation, or proactive behavior from history. | `tests/test_calibration_proposal_inbox.py`; `tests/test_bodybudget_current_shell_integration_matrix.py`; `tests/test_calibration_activation_cap.py`; root public route smoke active |

### CurrentShell Consumption Rules

- CurrentShell may refer to BodyBudget data only by the stable read-model names in this matrix.
- CurrentShell may render, group, collapse, or label supplied values, but it must not calculate BodyBudget truth.
- CurrentShell sorting or filtering is presentation-only for non-proposal collections where order is not semantically meaningful. `calibration_proposal_inbox` must preserve backend-provided proposal order, option `rank_order`, `is_primary`, and `proposal_status`.
- If a UI or WebCell needs a missing field, the next slice is a backend read-model extension, not a frontend fallback calculation.
- Context Engineering may summarize these read models only through a separate CE contract slice. This matrix does not add fields to `ManagerContextPacket`.
- `calibration_proposal_inbox` is a mirror only. Primary negotiation remains chat-first, and stored actions remain the only mutation path for accepted/deferred/rejected calibration proposals; `/calibration/proposal/stored-action` must not create unknown users while resolving invalid action requests.
- `calibration_proposal_history` is read-only audit. History route projection must not expose `options[]`, `effect_payload`, full metadata, policy packets, or trace envelopes, and must not be used as a mutation source.
- `/estimate` may bridge chat-primary calibration preview only when `EstimateRequest.calibration_preview_requested=true`; it returns backend `proposal_response` with `proposal_cards` and `quick_actions` for render/mirror surfaces. `persist_calibration_proposal=true` is ignored unless the explicit preview flag is present. Raw chat text, chip label text, or reply wording must not authorize preview persistence.
- `/estimate` may bridge chat-primary calibration accept/defer/reject only when `EstimateRequest` includes both `calibration_proposal_container_id` and `calibration_action`; optional `calibration_action_accepted_at` may be supplied as backend commit input for the stored-action effective-date rule; `/calibration/proposal/stored-action` `accepted_at` must include date and time, and `/estimate` `calibration_action_accepted_at` must include date and time; neither accepts date-only values; raw chat text, chip label text, or reply wording must not authorize calibration mutation. CurrentShell must not calculate the effective date; it must render backend `effective_from`.

## Action Wiring Rules

| Action Class | Rule | Stop Condition |
|---|---|---|
| Read-only dashboard refresh | May read existing canonical read models and render supplied values. | Stop if renderer must compute missing truth. |
| UI-anchored correction / confirmation | Must re-enter `InteractionEvent`, attachment/transition guards, manager decision, and domain workflow. | Stop if direct mutation is proposed from UI. |
| Proposal accept / defer / reject | Must use proposal command path owned by the relevant domain and manager policy. | Stop if UI creates, ranks, or rewrites proposal options. |
| Chat-primary calibration proposal preview | May call `/estimate` only with explicit `calibration_preview_requested=true`; may persist an open proposal only with explicit `persist_calibration_proposal=true` and backend preview eligibility. | Stop if preview or proposal persistence is inferred from raw text such as "should we adjust", button copy, assistant wording, or proposal card position. |
| Chat-primary calibration proposal action | May call `/estimate` only with explicit `calibration_proposal_container_id` and `calibration_action`, optionally with `calibration_action_accepted_at`, or call `/calibration/proposal/stored-action` directly. Effective date remains backend-owned through returned `effective_from`. | Stop if action is inferred from raw text such as "yes", button copy, assistant wording, or proposal card position, or if CurrentShell calculates the effective date. |
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

The matrix is an allowed detour only as a read-only architecture mapping. Default execution should return to CurrentShell self-use MVP local desktop dogfood unless a future UI-visible field/action exposes a concrete canonical-truth gap.
