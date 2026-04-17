# Workflow Slice Registry

## Purpose

This document is the canonical supporting registry that decomposes the workflow ordering truth into implementation slices.

It is subordinate to:

- [`docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)

It does not redefine workflow order. It translates the canonical order into dispatchable work units that can be assigned to one or more agents or engineers.

## Registry Rules

- Every slice must belong to one parent workflow from the ordering spec.
- A slice may only depend on slices that are earlier or same-wave compatible in the canonical workflow order.
- `allowed_touch_areas` and `forbidden_touch_areas` are mandatory because this registry is intended to reduce file bloat and cross-slice collisions.
- A slice may be marked parallelizable only when its write scope and state dependency boundaries are explicitly non-conflicting.

## Minimum Slice Schema

Each slice entry must define at least:

- `slice_id`
- `parent_workflow_id`
- `title`
- `goal`
- `depends_on_slices[]`
- `required_truth_docs[]`
- `allowed_touch_areas[]`
- `forbidden_touch_areas[]`
- `state_dependencies`
- `ui_surface_dependency`
- `acceptance_criteria[]`
- `required_tests[]`
- `benchmark_seed_required`
- `handoff_required`
- `parallelizable_with[]`
- `delegation_mode`
- `default_worker_posture`

`delegation_mode` must use one of:

- `single_threaded_decision_work`
- `parallelizable_implementation`
- `parallelizable_verification`

`default_worker_posture` should make the default execution bias explicit:

- keep semantic/product truth on the main thread
- prefer workers for bounded non-semantic follow-through

## Initial Slice Set

### 2.1 Single-turn Intake

#### Slice `2.1a-simple-provisional-estimate`

- `parent_workflow_id`: `2.1-single-turn-intake`
- `title`: `Simple provisional estimate lane`
- `goal`: handle the cheapest low-context intake path when the system can answer without exact DB matching or web search
- `depends_on_slices[]`: `[]`
- `required_truth_docs[]`:
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L3M_GUARDRAIL_MATH_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/usecases/text_meal*`
  - `app/application/*`
  - `app/agent/task_meal_link_llm.py`
  - `app/agent/decision_llm.py`
  - `app/agent/nutrition_resolution_llm.py`
- `forbidden_touch_areas[]`:
  - recommendation runtime
  - calibration runtime
  - rescue runtime
  - proactive logic
- `state_dependencies`: canonical meal write path, ledger update, stage trace
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - single text meal can commit through canonical persistence
  - no external search required
  - trace is emitted per pass
- `required_tests[]`:
  - intake happy path
  - commit candidate creation
  - ledger update smoke test
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

#### Slice `2.1b-exact-db-item-lane`

- `parent_workflow_id`: `2.1-single-turn-intake`
- `title`: `Exact DB item lane`
- `goal`: resolve exact or near-exact known food items through local database-backed evidence
- `depends_on_slices[]`:
  - `2.1a-simple-provisional-estimate`
- `required_truth_docs[]`:
  - `docs/specs/nutrition_output_contract.md`
  - `docs/specs/retrieval_external_search_ownership_spec.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/agent/exact_item_index.py`
  - `app/usecases/evidence/*`
  - `app/application/evidence_assembly.py`
  - intake pass modules
- `forbidden_touch_areas[]`:
  - web fallback behavior
  - memory/retrieval deepening layers
  - recommendation logic
- `state_dependencies`: local evidence retrieval, typed nutrition resolution, canonical write
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - exact item path can produce stronger evidence-backed result
  - no web lookup is required when local exact match succeeds
- `required_tests[]`:
  - exact item resolution
  - exact-vs-provisional selection
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

#### Slice `2.1c-clarify-required-lane`

- `parent_workflow_id`: `2.1-single-turn-intake`
- `title`: `Clarify-required single-turn lane`
- `goal`: detect when intake cannot safely proceed without a blocking follow-up
- `depends_on_slices[]`:
  - `2.1a-simple-provisional-estimate`
- `required_truth_docs[]`:
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/agent/decision_llm.py`
  - `app/agent/final_response_llm.py`
  - `app/application/followup_policy.py`
  - intake boundary helpers
- `forbidden_touch_areas[]`:
  - recommendation logic
  - body observation
  - rescue/calibration logic
- `state_dependencies`: draft/no-commit behavior, follow-up response handling
- `ui_surface_dependency`: chat reply only
- `acceptance_criteria[]`:
  - blocking clarify path does not commit meal truth
  - outward question is consistent with unresolved info
- `required_tests[]`:
  - clarify-blocking no-commit path
  - follow-up question shape validation
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

#### Slice `2.1d-cannot-estimate-lane`

- `parent_workflow_id`: `2.1-single-turn-intake`
- `title`: `Cannot-estimate refusal lane`
- `goal`: explicitly abstain from commit when the system cannot produce a safe estimate
- `depends_on_slices[]`:
  - `2.1c-clarify-required-lane`
- `required_truth_docs[]`:
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md`
- `allowed_touch_areas[]`:
  - intake pass modules
  - response shaping helpers
- `forbidden_touch_areas[]`:
  - canonical write bridge semantics
  - non-intake workflow code
- `state_dependencies`: abstain/no-commit behavior
- `ui_surface_dependency`: chat reply only
- `acceptance_criteria[]`:
  - no canonical meal write occurs
  - abstain path stays explicit and typed
- `required_tests[]`:
  - cannot-estimate no-commit
  - abstain payload validation
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.1e-web-search-fallback-lane`

- `parent_workflow_id`: `2.1-single-turn-intake`
- `title`: `Web-search fallback lane`
- `goal`: add controlled external lookup only after local/exact paths are insufficient
- `depends_on_slices[]`:
  - `2.1b-exact-db-item-lane`
  - `2.1c-clarify-required-lane`
- `required_truth_docs[]`:
  - `docs/specs/retrieval_external_search_ownership_spec.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/usecases/evidence/retrieval.py`
  - `app/search/*`
  - evidence assembly modules
  - intake pass modules
- `forbidden_touch_areas[]`:
  - recommendation runtime
  - calibration/rescue logic
  - memory selector logic
- `state_dependencies`: search ownership rules, evidence ranking, no implicit semantic override
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - web path only activates when local path is insufficient
  - search-derived evidence remains lower authority than exact/local truth
- `required_tests[]`:
  - fallback activation
  - ownership enforcement
  - no-search-when-not-needed
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

### 2.2 Multi-turn Intake + Correction

#### Slice `2.2a-active-meal-continuation`

- `parent_workflow_id`: `2.2-multi-turn-intake-correction`
- `title`: `Active meal continuation`
- `goal`: support adding information to an in-progress meal thread without breaking lineage
- `depends_on_slices[]`:
  - `2.1a-simple-provisional-estimate`
- `required_truth_docs[]`:
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/state_transition.py`
  - `app/infrastructure/meal_log_persistence.py`
  - canonical meal bridge
  - intake entrypoint helpers
- `forbidden_touch_areas[]`:
  - today UI
  - recommendation
  - rescue/calibration
- `state_dependencies`: active thread detection, version chain maintenance
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - continuation attaches to the correct active meal thread
  - canonical version lineage stays valid
- `required_tests[]`:
  - active thread continuation
  - no accidental new thread
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

#### Slice `2.2b-historical-correction`

- `parent_workflow_id`: `2.2-multi-turn-intake-correction`
- `title`: `Historical correction`
- `goal`: support editing a previous committed meal through new version creation instead of in-place overwrite
- `scope_note`: correction here assumes the target meal/thread is already explicit or directly resolvable from active context, today context, or another bounded correction reference; fuzzy cross-week historical recall belongs to later memory / retrieval work
- `depends_on_slices[]`:
  - `2.2a-active-meal-continuation`
- `required_truth_docs[]`:
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L3M_GUARDRAIL_MATH_SPEC.md`
- `allowed_touch_areas[]`:
  - canonical persistence
  - canonical commit bridge
  - intake correction helpers
- `forbidden_touch_areas[]`:
  - UI surfaces beyond correction display
  - recommendation/rescue/calibration logic
- `state_dependencies`: version supersession, ledger recompute
- `ui_surface_dependency`: correction feedback only
- `acceptance_criteria[]`:
  - historical correction creates a new version
  - ledger recompute reflects correction
- `required_tests[]`:
  - historical correction lineage
  - recompute after correction
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

#### Slice `2.2c-cross-midnight-attribution`

- `parent_workflow_id`: `2.2-multi-turn-intake-correction`
- `title`: `Cross-midnight attribution`
- `goal`: ensure late-night intake and correction flows land on the correct local date
- `depends_on_slices[]`:
  - `2.2a-active-meal-continuation`
- `required_truth_docs[]`:
  - `docs/specs/L3M_GUARDRAIL_MATH_SPEC.md`
  - `docs/specs/L2_DATA_STATE_SPEC.md`
- `allowed_touch_areas[]`:
  - time label helpers
  - canonical persistence local-date resolution
  - intake entrypoint wiring
- `forbidden_touch_areas[]`:
  - recommendation/rescue/calibration
  - UI beyond date rendering
- `state_dependencies`: local date attribution, ledger date selection
- `ui_surface_dependency`: today page readiness later
- `acceptance_criteria[]`:
  - cross-midnight inputs attribute to the correct ledger date
  - corrections do not silently drift to the wrong day
- `required_tests[]`:
  - cross-midnight intake
  - cross-midnight correction
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.2d-followup-closure-validation-foundation`

- `parent_workflow_id`: `2.2-multi-turn-intake-correction`
- `title`: `Follow-up closure validation foundation`
- `goal`: validate backend two-turn closure for both `ask_followup_only` and `estimate_with_followup` lanes without widening into UI, read-side, or memory/retrieval work
- `depends_on_slices[]`:
  - `2.2a-active-meal-continuation`
  - `2.2c-cross-midnight-attribution`
- `required_truth_docs[]`:
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md`
- `allowed_touch_areas[]`:
  - `docs/quality/benchmarks/intake/multi_turn/*`
  - `docs/quality/benchmark_test_set_v1.txt`
  - `docs/quality/benchmark_test_set_v2.txt`
  - `tests/fixtures/benchmark_test_set_v1.json`
  - `tests/test_followup_closure_validation.py`
  - targeted intake validation helpers
- `forbidden_touch_areas[]`:
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
  - today UI/read-model surfaces
  - rescue/calibration/recommendation/proactive logic
  - memory/retrieval deepening
- `state_dependencies`: pending follow-up state, unresolved info state, same-intake closure target, continuation/supersession safety
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - `ask_followup_only -> completion` closes on the same intake boundary
  - `estimate_with_followup -> refinement` closes on the same intake boundary
  - first-turn unresolved state remains open until the follow-up reply arrives
  - second turn does not silently fork into a duplicate meal thread
  - validation passes without durable memory or retrieval deepening assumptions
- `required_tests[]`:
  - targeted two-turn ask-followup closure regression
  - targeted two-turn estimate-with-followup refinement regression
  - pending follow-up state continuity assertions
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.2f-founder-fit-multi-turn-replay-pack`

- `parent_workflow_id`: `2.2-multi-turn-intake-correction`
- `title`: `Founder-fit multi-turn replay pack`
- `goal`: author and review an initial founder-fit replay pack that expands beyond `2.2d`'s two closure proofs into representative multi-turn cases that are ready for human review and later eval growth
- `depends_on_slices[]`:
  - `2.2d-followup-closure-validation-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md`
  - `docs/quality/planner_case_matrix.md`
- `allowed_touch_areas[]`:
  - `docs/quality/benchmarks/intake/multi_turn/*`
  - `docs/quality/FOLLOWUP_CLOSURE_SEED_INVENTORY.md`
  - `docs/quality/FOUNDER_FIT_MULTI_TURN_REPLAY_PACK_V1.md`
  - benchmark seed docs under `docs/quality/*`
- `forbidden_touch_areas[]`:
  - production runtime code
  - today UI/read-model surfaces
  - rescue/calibration/recommendation/proactive logic
  - memory/retrieval deepening
- `state_dependencies`: session-local follow-up continuity, same-intake attachment, follow-up closure boundary, new-meal-switch boundary
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - replay pack contains a reviewable initial set of representative founder-fit multi-turn cases
  - pack covers both `ask_followup_only` and `estimate_with_followup` closure lanes
  - pack includes boundary controls for attachment vs new-meal-switch
  - every replay case names its benchmark seed or authored origin
  - pack is small enough for human review and later expansion
- `required_tests[]`:
  - none; this slice is review-pack authoring and selection
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.2g-generic-drink-exact-lane-soft-avoid`

- `parent_workflow_id`: `2.2-multi-turn-intake-correction`
- `title`: `Generic drink exact-lane soft avoid`
- `goal`: keep generic tea-shop drink classes such as generic bubble tea out of automatic `exact_item` finalization unless the user supplied strong exact identity cues
- `depends_on_slices[]`:
  - `2.2f-founder-fit-multi-turn-replay-pack`
- `required_truth_docs[]`:
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `docs/quality/FOUNDER_FIT_MULTI_TURN_REPLAY_PACK_V1.md`
- `allowed_touch_areas[]`:
  - `app/application/context_assembly.py`
  - `app/usecases/text_meal_nutrition_support.py`
  - `app/usecases/text_meal_response_support.py`
  - targeted tests for pass/runtime posture guards
- `forbidden_touch_areas[]`:
  - retrieval architecture rewrites
  - memory/recommendation/calibration/rescue logic
  - broad exact-item ontology refactors
- `state_dependencies`: generic-drink evidence interpretation, pass-level repair gating, no deterministic post-pass posture override
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - generic `珍珠奶茶` no longer defaults to exact-item finalization without explicit brand or packaged identity cues from the user
  - branded or strong exact-cued drinks can still remain exact
  - deterministic layers no longer rewrite completed LLM posture fields after pass completion
- `required_tests[]`:
  - targeted generic drink exact-lane regression
  - targeted post-pass override regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.2h-turn2-hybrid-replay-eval-foundation`

- `parent_workflow_id`: `2.2-multi-turn-intake-correction`
- `title`: `Turn-2 hybrid replay evaluation foundation`
- `goal`: establish the cost-controlled standard workflow for second-turn intake evaluation by replaying saved turn-1 context and only live-calling turn 2
- `depends_on_slices[]`:
  - `2.2g-generic-drink-exact-lane-soft-avoid`
- `required_truth_docs[]`:
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md`
- `allowed_touch_areas[]`:
  - eval runner / fixture / benchmark docs under `docs/quality/*`
  - targeted replay harness code
  - targeted tests for replay closure behavior
- `forbidden_touch_areas[]`:
  - today UI/read-model surfaces
  - rescue/calibration/recommendation/proactive logic
  - durable memory / retrieval deepening
- `state_dependencies`: saved turn-1 trace contract, saved llm traces, pending follow-up state, same-intake closure target
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - one `ask_followup_only -> completion` replay path works
  - one `estimate_with_followup -> refinement` replay path works
  - second turn attaches to the same intake without duplicate meal creation
  - replay evaluation does not require full 2-turn live reruns by default
- `required_tests[]`:
  - targeted turn-2 hybrid replay regression
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.2i-turn2-attachment-and-refinement-replay-pack`

- `parent_workflow_id`: `2.2-multi-turn-intake-correction`
- `title`: `Turn-2 attachment and refinement replay pack`
- `goal`: expand the file-backed turn-2 replay pack so planner attachment, same-intake recognition, completion, and refinement behavior can be tested across multiple founder-fit follow-up families without rerunning full live turn-1 flows each time
- `depends_on_slices[]`:
  - `2.2h-turn2-hybrid-replay-eval-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `docs/quality/FOUNDER_FIT_MULTI_TURN_REPLAY_PACK_V1.md`
  - `docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md`
- `allowed_touch_areas[]`:
  - `docs/quality/benchmarks/intake/multi_turn/*`
  - `scripts/run_turn2_hybrid_replay.py`
  - `tests/test_turn2_hybrid_replay_foundation.py`
- `forbidden_touch_areas[]`:
  - intake runtime logic
  - today/read-model runtime logic
  - rescue/calibration/recommendation/proactive logic
  - durable memory / retrieval deepening
- `state_dependencies`: saved turn-1 trace contract, turn-1 persistence outcome, same-intake attachment, refinement-vs-new-meal discrimination
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - replay pack expands beyond the original two official cases
  - pack includes both `ask_followup_only -> completion` and `estimate_with_followup -> refinement` families
  - pack includes founder-fit cases that explicitly stress same-intake attachment and no-duplicate-meal behavior
  - every case names its accepted Golden seed or founder-authored origin
- `required_tests[]`:
  - turn-2 replay pack shape validation
  - turn-2 replay summary contract regression
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.2j-turn2-boundary-to-persistence-continuity`

- `parent_workflow_id`: `2.2-multi-turn-intake-correction`
- `title`: `Turn-2 boundary-to-persistence continuity`
- `goal`: ensure same-intake turn-2 follow-ups attach to the unresolved parent meal whenever boundary/context already classify the turn as `continue_active_meal`, even if planner intent remains `food_estimation`
- `depends_on_slices[]`:
  - `2.2i-turn2-attachment-and-refinement-replay-pack`
- `required_truth_docs[]`:
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/infrastructure/meal_log_persistence.py`
  - `app/application/text_meal_commit_service.py`
  - `tests/test_canonical_persistence.py`
  - `tests/test_followup_closure_validation.py`
- `forbidden_touch_areas[]`:
  - prompt templates
  - replay pack taxonomy expansion
  - today/read-model surfaces
  - rescue/calibration/recommendation/proactive logic
- `state_dependencies`: unresolved meal lineage, parent log continuity, canonical commit target continuity, boundary-first same-intake recognition
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - `continue_active_meal` turns attach to the unresolved parent even when planner intent stays `food_estimation`
  - turn-2 completion/refinement no longer opens a new meal when same-intake boundary is already resolved
  - still-unresolved follow-up remains attached to the same parent meal instead of fragmenting lineage
- `required_tests[]`:
  - boundary-to-persistence continuity regression
  - still-unresolved same-parent regression
  - targeted turn-2 replay rerun for previously detached cases
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.2k-turn2-closure-complete-pack-tightening`

- `parent_workflow_id`: `2.2-multi-turn-intake-correction`
- `title`: `Turn-2 closure-complete pack tightening`
- `goal`: tighten the 9-case positive-path replay pack so turn-2 replies are explicitly closure-complete, fixture-safe, and suitable for workflow-level replay evidence without relying on ambiguous shorthand`
- `depends_on_slices[]`:
  - `2.2j-turn2-boundary-to-persistence-continuity`
- `required_truth_docs[]`:
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `docs/quality/FOUNDER_FIT_MULTI_TURN_REPLAY_PACK_V1.md`
- `allowed_touch_areas[]`:
  - `docs/quality/benchmarks/intake/multi_turn/*`
  - `tests/test_turn2_hybrid_replay_foundation.py`
  - `scripts/check_audit_fixture_safety.py`
- `forbidden_touch_areas[]`:
  - intake runtime logic
  - prompt templates
  - today/read-model surfaces
  - rescue/calibration/recommendation/proactive logic
- `state_dependencies`: closure-complete turn-2 phrasing, fixture safety, positive-path replay oracle stability
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - each of the 9 official turn-2 inputs is explicit enough to read as an answer to the previous follow-up, not a new meal
  - known fixture-risk cases are rewritten into clear UTF-8 positive-path inputs
  - replay pack remains schema-valid and registry-safe
  - live rerun of the 9-case pack produces a clearer separation between continuity bugs and true closure-threshold misses
- `required_tests[]`:
  - turn-2 replay pack shape validation
  - audit fixture safety check
  - full 9-case live rerun evidence
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

### 2.3 Today UI / Read Models

#### Slice `2.3a-current-budget-read-model`

- `parent_workflow_id`: `2.3-today-ui-read-models`
- `title`: `Current budget read model`
- `goal`: surface remaining kcal and committed meal truth from canonical ledger/state
- `depends_on_slices[]`:
  - `2.2b-historical-correction`
  - `2.2c-cross-midnight-attribution`
- `required_truth_docs[]`:
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
- `allowed_touch_areas[]`:
  - canonical read/query helpers
  - application read-model assembly
  - route/view serializers
- `forbidden_touch_areas[]`:
  - recommendation logic
  - rescue/calibration/proactive
- `state_dependencies`: canonical meal data, ledger recompute
- `ui_surface_dependency`: today UI
- `acceptance_criteria[]`:
  - read model reflects canonical truth for current day
  - correction paths are visible through read side
- `required_tests[]`:
  - today read model happy path
  - correction visibility
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `2.4a-body-observation-persistence`

#### Slice `2.3b-low-fi-today-ui`

- `parent_workflow_id`: `2.3-today-ui-read-models`
- `title`: `Low-fi today UI`
- `goal`: render the canonical today/read-model state in a coarse but truthful UI
- `depends_on_slices[]`:
  - `2.3a-current-budget-read-model`
- `required_truth_docs[]`:
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
- `allowed_touch_areas[]`:
  - route handlers
  - UI templates/components for today surface
  - read-model adapters
- `forbidden_touch_areas[]`:
  - recommendation/proactive surfaces
  - body observation semantics
- `state_dependencies`: today read model
- `ui_surface_dependency`: today UI itself
- `acceptance_criteria[]`:
  - UI does not invent state beyond read-model truth
  - UI remains low-fi and additive
- `required_tests[]`:
  - rendering smoke test
  - today state visibility test
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `2.4b-weight-ui`

#### Slice `2.3c-read-side-confidence-follow-through`

- `parent_workflow_id`: `2.3-today-ui-read-models`
- `title`: `Read-side confidence follow-through`
- `goal`: revalidate current-budget and today-facing read-side truth after first-turn Golden live audit and turn-2 replay evidence confirm the current multi-turn intake behavior`
- `depends_on_slices[]`:
  - `2.2h-turn2-hybrid-replay-eval-foundation`
  - `2.3a-current-budget-read-model`
  - `2.3b-low-fi-today-ui`
- `required_truth_docs[]`:
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/read_models/*`
  - `app/web/*today*`
  - targeted read-side and route-level regressions
  - eval/replay summaries under `.logs/turn2_hybrid_replay/*`
- `forbidden_touch_areas[]`:
  - intake decision or nutrition pass logic
  - rescue/calibration/recommendation/proactive logic
  - memory / retrieval deepening
- `state_dependencies`: canonical meal truth, unresolved-to-committed turn-2 closure, same-intake attachment, current-budget/today read assembly
- `ui_surface_dependency`: `today UI only as a read-side consumer; no broader UI redesign`
- `acceptance_criteria[]`:
  - current-budget reflects confirmed turn-2 closure truth without duplicate or missing meal state
  - today-facing read side remains correction-safe after the newly verified multi-turn paths
  - read-side regressions explicitly cover both `ask_followup_only -> completion` and `estimate_with_followup -> refinement`
- `required_tests[]`:
  - targeted current-budget regression after turn-2 completion
  - targeted today/read-side regression after estimate refinement
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

### 2.4 Weight / Body Observation

#### Slice `2.4a-body-observation-persistence`

- `parent_workflow_id`: `2.4-weight-body-observation`
- `title`: `Body observation persistence`
- `goal`: persist weight/body observations so that later calibration has a stable second data source
- `depends_on_slices[]`:
  - `2.1a-simple-provisional-estimate`
- `required_truth_docs[]`:
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md`
- `allowed_touch_areas[]`:
  - canonical persistence
  - body observation write helpers
  - route serializers
- `forbidden_touch_areas[]`:
  - calibration proposal logic
  - recommendation
- `state_dependencies`: body observation canonical write path
- `ui_surface_dependency`: weight UI later
- `acceptance_criteria[]`:
  - body observations can be written and read
  - local-date and observed-at fields remain explicit
- `required_tests[]`:
  - body observation write/read
  - observed-at normalization
- `benchmark_seed_required`: `false`
- `handoff_required`: `false`
- `parallelizable_with[]`: `2.3a-current-budget-read-model`

#### Slice `2.4b-weight-ui`

- `parent_workflow_id`: `2.4-weight-body-observation`
- `title`: `Weight UI`
- `goal`: show the current body-observation state in a low-fi surface without implying full calibration readiness
- `depends_on_slices[]`:
  - `2.4a-body-observation-persistence`
- `required_truth_docs[]`:
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
- `allowed_touch_areas[]`:
  - body observation routes/views
  - low-fi UI surface for weight data
- `forbidden_touch_areas[]`:
  - calibration proposals
  - recommendation/proactive
- `state_dependencies`: body observation read path
- `ui_surface_dependency`: weight UI itself
- `acceptance_criteria[]`:
  - weight entries are visible and truthful
  - UI does not promise calibration outcomes yet
- `required_tests[]`:
  - weight UI smoke test
  - body observation visibility test
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `2.3b-low-fi-today-ui`

### 2.5 Rescue

#### Slice `2.5a-rescue-deterministic-overlay`

- `parent_workflow_id`: `2.5-rescue`
- `title`: `Deterministic rescue overlay`
- `goal`: introduce short-horizon rescue math and overlay persistence without depending on memory-aware recommendation
- `dependency_note`: this slice may read canonical ledger truth via stable read-side helpers, but it must not depend on Today UI route or presentation behavior
- `depends_on_slices[]`:
  - `2.3a-current-budget-read-model`
- `required_truth_docs[]`:
  - `docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L3M_GUARDRAIL_MATH_SPEC.md`
- `allowed_touch_areas[]`:
  - ledger arithmetic helpers
  - rescue overlay write path
  - rescue runtime skeletons
- `forbidden_touch_areas[]`:
  - recommendation
  - memory selectors
  - proactive
- `state_dependencies`: day budget ledger, rescue overlay persistence
- `ui_surface_dependency`: rescue display later
- `acceptance_criteria[]`:
  - rescue overlay respects safety floor and compression cap
  - overlay writes through canonical ledger
- `required_tests[]`:
  - rescue math
  - safety floor enforcement
  - overlay ledger recompute
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

#### Slice `2.5b-rescue-proposal-artifact-foundation`

- `parent_workflow_id`: `2.5-rescue`
- `title`: `Rescue proposal artifact foundation`
- `goal`: convert deterministic rescue trigger / assessment truth into a structured non-user-facing proposal artifact without generating response copy, UI, or accept-side commit behavior
- `depends_on_slices[]`:
  - `2.5a-rescue-deterministic-overlay`
- `required_truth_docs[]`:
  - `docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L3M_GUARDRAIL_MATH_SPEC.md`
  - `docs/specs/L2_DATA_STATE_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/rescue_*`
  - `app/domain/canonical_models.py` only if a narrow typed artifact is required
  - `tests/test_rescue_*`
- `forbidden_touch_areas[]`:
  - `app/routes.py`
  - `app/usecases/text_meal.py`
  - `app/schemas.py`
  - recommendation / proactive / retrieval logic
  - rescue response wording or UI surfaces
  - accept-side proposal commit semantics
- `state_dependencies`: current budget truth, rescue overlay math, active `BodyPlan.safety_floor_kcal`, rescue family legality, escalation posture
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - deterministic-first rescue proposal artifact exists
  - proposal artifact expresses `rescue_needed`, `recovery_viability`, `rescue_horizon`, allowed and blocked rescue families, and explicit `no_rescue` or `rescue_stop_and_escalate` posture where appropriate
  - no option violates `BodyPlan.safety_floor_kcal`
  - slice stops before user-facing response shaping, route/UI work, recommendation wiring, or accept-side writeback
- `required_tests[]`:
  - rescue proposal artifact happy path
  - viability-to-posture regression
  - stop-and-escalate legality regression
  - safety-floor enforcement regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

#### Slice `2.5c-rescue-option-shaping`

- `parent_workflow_id`: `2.5-rescue`
- `title`: `Rescue option shaping`
- `goal`: refine deterministic rescue proposal artifacts into ranked, dispatch-safe rescue options with explicit family semantics, activation timing, and guardrail-backed effect payloads, while still stopping before any user-facing response wording or accept-side commit behavior
- `depends_on_slices[]`:
  - `2.5b-rescue-proposal-artifact-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/rescue_proposal.py`
  - `app/application/rescue_overlay.py` only if narrow option-effect alignment is required
  - `tests/test_rescue_proposal.py`
  - `tests/test_rescue_overlay.py` only if option-effect payloads change
- `forbidden_touch_areas[]`:
  - `app/routes.py`
  - `app/usecases/text_meal.py`
  - `app/schemas.py`
  - rescue response wording or UI surfaces
  - recommendation / proactive / retrieval logic
  - accept-side overlay commit semantics
- `state_dependencies`: rescue trigger truth, recovery viability, rescue horizon, safety-floor legality, activation timing policy, typed rescue option contract
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - ranked rescue options exist for the legal rescue families without requiring response text
  - `same_day_soft_cap`, `short_horizon_spread`, `next_meal_protection`, `logging_first_rescue`, and `rescue_stop_and_escalate` each have explicit shaping semantics where legal
  - option payloads encode activation timing such as `immediate_next_meal`, `today_lunch`, or `tomorrow_0000` consistently with the `11:00` rule and the `next_meal_protection` exception
  - `non_viable` rescue always fronts `rescue_stop_and_escalate`
  - slice stops before response presentation, channel copy, quick actions, or accept-side writeback
- `required_tests[]`:
  - rescue option ranking regression
  - activation-timing / `11:00` boundary regression
  - non-viable escalation precedence regression
  - legal-family shaping regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

#### Slice `2.5d-rescue-response-surface`

- `parent_workflow_id`: `2.5-rescue`
- `title`: `Rescue response surface`
- `goal`: surface rescue as a single chat-first recovery plan with adjustable intensity, while keeping intake separate and UI mirror-only
- `depends_on_slices[]`:
  - `2.5c-rescue-option-shaping`
- `required_truth_docs[]`:
  - `docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `AGENTS.md`
- `allowed_touch_areas[]`:
  - `app/application/rescue_response.py`
  - `app/application/rescue_chat_surface.py`
  - `app/application/rescue_overlay.py` only for narrow accept-side payload application
  - `app/application/rescue_runtime.py` only if surface inputs need narrow read compatibility
  - `app/application/open_proposals_read_model.py`
  - `app/infrastructure/open_proposals_read_model.py` only if top-option retrieval needs narrow shaping
  - `app/web/rescue_routes.py`
  - `tests/test_rescue_response.py`
  - `tests/test_rescue_chat_surface.py`
  - `tests/test_rescue_routes.py`
- `forbidden_touch_areas[]`:
  - `app/usecases/text_meal.py`
  - `app/schemas.py`
  - intake response surfaces
  - backup-option UI
- `state_dependencies`: open rescue proposal read-side, top-option retrieval, target recovery kcal, effective budget basis, chat-first product posture
- `ui_surface_dependency`: mirror-only
- `acceptance_criteria[]`:
  - rescue surfaces as one recommended recovery plan, not a backup-option menu
  - chat and intake remain separated
  - proactive rescue and explicit reactive rescue use the same single-plan response contract
  - plan intensity can be shortened or extended within the configured guardrails
  - accept marks the rescue proposal accepted and applies the persisted rescue overlay payload to ledger writeback
  - defer keeps the proposal pending, sets a 12-hour reminder boundary, and keeps UI mirror-only state readable
  - reject/defer reasons only create a thin bridge artifact for later personalization work; they do not imply `2.7` memory/retrieval deepening is implemented
  - rescue exposes a dedicated web/chat route without mixing rescue into intake routes
  - UI remains mirror-only and does not become the primary interaction surface
- `required_tests[]`:
  - surface gate regression
  - single-plan response rendering regression
  - shorten / extend guardrail regression
  - defer reminder regression
  - thin reason-bridge regression
  - reject / explain action regression
  - accept-side overlay writeback regression
  - rescue route integration regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

### 2.6 Calibration Core

#### Slice `2.6a-recommended-target-kcal-foundation`

- `parent_workflow_id`: `2.6-calibration-core`
- `title`: `Recommended target kcal foundation`
- `goal`: define and compute a deterministic personalized daily target that stays above the canonical hard floor without overloading rescue guardrail semantics
- `depends_on_slices[]`:
  - `2.5a-rescue-deterministic-overlay`
- `required_truth_docs[]`:
  - `docs/references/SAFETY_FLOOR_AND_TARGET_DECISION_NOTE.md`
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/L2A_DATA_DICTIONARY_SPEC.md`
  - `docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/target_calculation.py`
  - `app/domain/canonical_models.py`
  - `tests/test_target_calculation.py`
- `forbidden_touch_areas[]`:
  - `app/routes.py`
  - `app/usecases/text_meal.py`
  - `app/schemas.py`
  - recommendation response surfaces
  - proactive logic
  - rescue response surfaces
- `state_dependencies`: active `BodyPlan` hard floor, deterministic target inputs, later calibration consumption
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - deterministic target calculation uses personal inputs and weekly loss target
  - personalized target remains explicitly separate from `BodyPlan.safety_floor_kcal`
  - computed target never drops below the canonical hard floor
- `required_tests[]`:
  - target-calculation deterministic regression
  - hard-floor clamp regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

#### Slice `2.6b-calibration-posture-foundation`

- `parent_workflow_id`: `2.6-calibration-core`
- `title`: `Calibration posture and operating-estimate foundation`
- `goal`: produce the first deterministic calibration-core output layer that distinguishes `insufficient_data`, `logging_quality_first`, `monitor_only`, and `calibration_candidate` without entering proposal or UI work
- `depends_on_slices[]`:
  - `2.6a-recommended-target-kcal-foundation`
  - `2.4a-body-observation-persistence`
- `required_truth_docs[]`:
  - `docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md`
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/L2A_DATA_DICTIONARY_SPEC.md`
  - `docs/specs/L3M_GUARDRAIL_MATH_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/calibration_model.py`
  - `app/application/target_calculation.py` only if baseline-target integration needs narrow alignment
  - `app/domain/canonical_models.py` only if a narrow typed output is required
  - `tests/test_calibration_model.py`
- `forbidden_touch_areas[]`:
  - `app/routes.py`
  - `app/usecases/text_meal.py`
  - `app/schemas.py`
  - calibration proposal runtime
  - recommendation response surfaces
  - proactive logic
  - memory / retrieval selector logic
- `state_dependencies`: active `BodyPlan` operating baseline, body observation history, intake coverage summary, mismatch attribution heuristics
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - deterministic calibration model outputs posture class without proposal generation
  - v1 thresholds honor the `14-day / 5-observation / 80% intake coverage` defaults
  - `operating_expenditure_estimate` remains separate from `intake_estimation_bias_posture`
  - slice does not mutate canonical ledger, recommendation, or rescue behavior
- `required_tests[]`:
  - posture classification regression
  - insufficient-data gate
  - logging-quality-first gate
  - candidate-vs-monitor deterministic regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

#### Slice `2.6c-calibration-proposal-gate-foundation`

- `parent_workflow_id`: `2.6-calibration-core`
- `title`: `Calibration proposal gate foundation`
- `goal`: add the deterministic proposal-eligibility gate that consumes calibration posture outputs and decides whether proposal flow may start, without generating options, UI responses, or accept-side writeback
- `depends_on_slices[]`:
  - `2.6b-calibration-posture-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md`
  - `docs/specs/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/L3M_GUARDRAIL_MATH_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/calibration_proposal_gate.py`
  - `app/application/calibration_model.py` only if a narrow adapter is required
  - `app/domain/canonical_models.py` only if a narrow typed gate result is required
  - `tests/test_calibration_proposal_gate.py`
- `forbidden_touch_areas[]`:
  - `app/routes.py`
  - `app/usecases/text_meal.py`
  - `app/schemas.py`
  - proposal option generation / ranking / response logic
  - proposal accept / BodyPlan writeback
  - recommendation response surfaces
  - proactive logic
  - memory / retrieval selector logic
- `state_dependencies`: calibration posture output, confidence gate, blocked option families, active budget/body-plan summary
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - deterministic gate outputs proposal eligibility and allowed / blocked option families
  - `logging_quality_first`, `monitor_only`, and low-confidence cases do not enter proposal flow
  - slice stops before option generation, response shaping, and commit side effects
- `required_tests[]`:
  - proposal-eligibility gate regression
  - blocked-option-family regression
  - no-proposal-on-low-quality-data regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`

### 2.7 Memory / Retrieval Deepening

#### Slice `2.7a-semantic-routing-eval-foundation`

- `parent_workflow_id`: `2.7-memory-retrieval-deepening`
- `title`: `Semantic routing eval foundation`
- `goal`: turn open-world chat semantic judgment into a file-backed, state-pack-based evaluation problem before any production semantic-router implementation or durable memory deepening begins
- `depends_on_slices[]`:
  - `2.5d-rescue-response-surface`
  - `2.2k-turn2-closure-complete-pack-tightening`
- `required_truth_docs[]`:
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `docs/quality/L5A_EVAL_SPEC.md`
  - `docs/quality/BENCHMARK_CASE_SCHEMA.md`
  - `AGENTS.md`
- `allowed_touch_areas[]`:
  - `docs/quality/*semantic*routing*`
  - `docs/quality/benchmarks/semantic_routing/*`
  - `docs/quality/AUDIT_RUNNER_REGISTRY.json`
  - `docs/quality/AUDIT_FIXTURE_REGISTRY.json`
  - `scripts/run_semantic_routing_eval.py`
  - targeted audit/harness helpers only if needed for the new runner
  - `tests/test_semantic_routing_eval_foundation.py`
- `forbidden_touch_areas[]`:
  - production intake/rescue/calibration routing logic
  - `app/usecases/text_meal.py`
  - `app/routes.py`
  - `app/schemas.py`
  - durable memory write paths
  - retrieval selector / reranker implementation
  - style-personalization runtime
- `state_dependencies`: open rescue proposal summary, pending intake follow-up summary, latest linked identifiers, thin reject/defer reason bridge, minimal recent message summaries
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - an official semantic-routing taxonomy exists for founder-fit chat utterances
  - a file-backed founder-fit benchmark pack exists with both rescue-bound and intake-followup-bound cases
  - the eval foundation uses a minimal state pack rather than full transcript replay
  - the runner emits predicted semantic family, workflow family, target attachment, workflow effect, and full trace artifacts
  - ambiguous cases remain visible in the benchmark pack instead of being hidden behind deterministic routing overrides
  - the checked-in docs explicitly note that the repo does not yet define a canonical `conversation_style_profile` / `sour.md` equivalent, and that style adaptation is a later `2.7` extension
- `required_tests[]`:
  - semantic-routing benchmark pack shape validation
  - semantic-routing runner summary/oracle contract regression
  - audit fixture safety check for the semantic-routing pack
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.7b-semantic-routing-evidence-hardening`

- `parent_workflow_id`: `2.7-memory-retrieval-deepening`
- `title`: `Semantic routing evidence hardening`
- `goal`: use the initial semantic-routing eval evidence to harden taxonomy, benchmark coverage, and drift-triage visibility without implementing a production semantic router or activating style-personalization runtime`
- `depends_on_slices[]`:
  - `2.7a-semantic-routing-eval-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L4A_MEMORY_MODEL_SPEC.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `docs/quality/SEMANTIC_ROUTING_EVAL_FOUNDATION.md`
  - `docs/quality/L5A_EVAL_SPEC.md`
  - `AGENTS.md`
- `allowed_touch_areas[]`:
  - `docs/specs/L4A_MEMORY_MODEL_SPEC.md`
  - `docs/quality/*semantic*routing*`
  - `docs/quality/benchmarks/semantic_routing/*`
  - `scripts/run_semantic_routing_eval.py`
  - `tests/test_semantic_routing_eval_foundation.py`
  - semantic-routing audit fixture/runner registry entries only if needed
- `forbidden_touch_areas[]`:
  - production intake/rescue/calibration routing logic
  - `app/usecases/text_meal.py`
  - `app/routes.py`
  - `app/schemas.py`
  - durable memory write paths
  - retrieval selector / reranker implementation
  - style-personalization runtime
- `state_dependencies`: semantic-routing state pack, thin reject/defer reason bridge, founder-fit rescue and intake-followup active-state summaries, drift-cluster triage metadata
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - `sour.md` / style-profile concept is recorded in repo truth only as a dormant extension note
  - founder-fit semantic-routing pack expands with high-value boundary and ambiguity cases without widening into unrelated domains
  - eval output emits drift triage by failure cluster, mismatch type, ambiguity posture, and state-pack sufficiency
  - live failures are reviewable by cluster and provisional hypothesis instead of remaining a black box
  - no deterministic semantic override table is introduced
- `required_tests[]`:
  - expanded semantic-routing benchmark pack shape validation
  - semantic-routing triage contract regression
  - mock semantic-routing regression with ambiguity case coverage
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.7c-official-text-surface-mojibake-guard-hardening`

- `parent_workflow_id`: `2.7-memory-retrieval-deepening`
- `title`: `Official text-surface mojibake guard hardening`
- `goal`: harden the repository's official benchmark, eval, script, and user-facing text surfaces against UTF-8-readable but semantically corrupted mojibake without opening production routing or style-personalization runtime`
- `depends_on_slices[]`:
  - `2.7b-semantic-routing-evidence-hardening`
- `required_truth_docs[]`:
  - `docs/quality/HARNESS_EXECUTION_POLICY.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `AGENTS.md`
- `allowed_touch_areas[]`:
  - `scripts/*mojibake*`
  - `scripts/audit_io_guard.py`
  - `scripts/check_audit_fixture_safety.py`
  - `docs/quality/*GUARD*.json`
  - `.githooks/pre-commit`
  - `.github/workflows/ci.yml`
  - targeted guard tests
  - minimal execution-truth sync
- `forbidden_touch_areas[]`:
  - production intake/rescue/calibration routing logic
  - retrieval selector / reranker implementation
  - style-personalization runtime
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: official audit fixture registry, official audit runner registry, benchmark text fields, user-facing string surfaces, UTF-8 family enforcement
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - official benchmark fixtures, eval runners, and targeted tests are covered by a shared official text-surface guard
  - fixture safety blocks semantic corruption in high-risk text fields such as `title`, `utterance`, `pending_question`, and `note`
  - pre-commit and CI enforce the new official text-surface guard
  - the existing user-facing mojibake guard continues to pass on clean rescue surfaces
  - no production routing or semantic-judgment logic is changed
- `required_tests[]`:
  - official text-surface guard regression
  - audit fixture semantic-field corruption regression
  - existing user-facing mojibake guard regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`

#### Slice `2.7d-semantic-routing-prompt-state-pack-hardening`

- `parent_workflow_id`: `2.7-memory-retrieval-deepening`
- `title`: `Semantic routing prompt/state-pack hardening`
- `goal`: use the 2.7b drift clusters on top of the now-guarded official text surfaces to tighten semantic-routing prompts, target vocabulary, and state-pack sufficiency without implementing a production semantic router or introducing deterministic semantic overrides`
- `depends_on_slices[]`:
  - `2.7b-semantic-routing-evidence-hardening`
  - `2.7c-official-text-surface-mojibake-guard-hardening`
- `required_truth_docs[]`:
  - `docs/quality/SEMANTIC_ROUTING_EVAL_FOUNDATION.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `docs/specs/L4A_MEMORY_MODEL_SPEC.md`
  - `docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md`
  - `AGENTS.md`
- `allowed_touch_areas[]`:
  - `docs/quality/*semantic*routing*`
  - `docs/quality/benchmarks/semantic_routing/*`
  - `scripts/run_semantic_routing_eval.py`
  - targeted semantic-routing eval fixtures/tests
  - semantic-routing prompt/state-pack builder code only if required by the eval contract
  - minimal execution-truth sync
- `forbidden_touch_areas[]`:
  - production intake/rescue/calibration routing logic
  - deterministic semantic override tables
  - retrieval selector / reranker implementation
  - style-personalization runtime
  - durable memory write paths
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: guarded official semantic-routing benchmark pack, drift-cluster triage artifacts, rescue action family evidence, intake follow-up continuation evidence, thin reject/defer reason bridge
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - semantic-routing live failures are reduced by prompt/state-pack and target-vocabulary improvements rather than deterministic override logic
  - rescue action family drift is reviewable as prompt/state-pack behavior rather than a black-box aggregate failure
  - intake follow-up continuation drift is reviewable as prompt/state-pack behavior rather than a black-box aggregate failure
  - ambiguity buckets remain explicit instead of being collapsed into keyword heuristics
  - response-side distinctions are not promoted into primary routing labels unless they change workflow effect or object attachment
  - suite-governance follow-through yields agent-allowed official capability/service packs plus executable workflow runners without introducing new product semantics
  - orchestration can discover and run the current executable workflow smoke lane by `suite_id` / `workflow_family` metadata instead of ad hoc script memory
  - no production semantic router is introduced
- `required_tests[]`:
  - semantic-routing benchmark pack regression
  - semantic-routing mock runner regression
  - semantic-routing live eval plus drift-triage artifact generation
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `parallelizable_implementation`
- `default_worker_posture`: `keep semantic/product truth local, but prefer workers for bounded registry, runner, fixture, executable-pack, regression, and docs follow-through`

#### Slice `2.7e-workflow-routing-pass-foundation`

- `parent_workflow_id`: `2.7-memory-retrieval-deepening`
- `title`: `Workflow routing pass foundation`
- `goal`: implement the global `workflow_routing_pass` as a thin pre-pass that routes utterances to the correct workflow family before any domain-specific pass runs, replacing the current implicit assumption that all input is intake
- `depends_on_slices[]`:
  - `2.7d-semantic-routing-prompt-state-pack-hardening`
- `required_truth_docs[]`:
  - `docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md`
  - `docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `docs/quality/SEMANTIC_ROUTING_EVAL_FOUNDATION.md`
  - `AGENTS.md`
- `allowed_touch_areas[]`:
  - `app/application/workflow_routing_pass.py`
  - `app/application/pass_runner.py`
  - `app/usecases/text_meal.py` only for thin wiring to new routing pass
  - `tests/test_workflow_routing_pass.py`
- `forbidden_touch_areas[]`:
  - intake pass internals
  - rescue pass internals
  - calibration pass internals
  - recommendation pass internals
  - deterministic semantic override tables
  - `app/routes.py`
  - `app/schemas.py`
- `state_dependencies`: open rescue proposal summary, pending intake followup summary, active body plan summary, recent message summary
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - `workflow_routing_pass` outputs `target_workflow_family`, `disposition`, `routing_confidence`, `ambiguity_posture`
  - intake, rescue, calibration, recommendation, body_observation, general_chat are all legal `target_workflow_family` values
  - routing pass uses `fast_router_model`, not `strict_reasoner_model`
  - routing pass does not do intake boundary splitting or nutrition resolution
  - existing intake flow still works when routing pass outputs `target_workflow_family: intake`
  - general_chat utterances route correctly without entering intake flow
- `required_tests[]`:
  - routing pass output schema regression
  - intake routing regression
  - rescue routing regression
  - general_chat routing regression
  - ambiguous utterance routing regression
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `single_threaded_decision_work`
- `default_worker_posture`: `keep semantic/product truth local`

#### Slice `2.7f-general-chat-workflow`

- `parent_workflow_id`: `2.7-memory-retrieval-deepening`
- `title`: `General chat workflow`
- `goal`: implement the general_chat workflow as a 1-pass response that reads CurrentBudgetView and ActiveBodyPlanView to answer product-related questions without entering any domain-specific flow
- `depends_on_slices[]`:
  - `2.7e-workflow-routing-pass-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L3_5_PROMPT_CONTRACT_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/general_chat_pass.py`
  - `app/application/pass_runner.py`
  - `tests/test_general_chat_workflow.py`
- `forbidden_touch_areas[]`:
  - intake pass internals
  - rescue pass internals
  - calibration pass internals
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: `CurrentBudgetView`, `ActiveBodyPlanView`
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - general_chat uses `response_writer_model`, 1 pass
  - can answer budget-related questions using `CurrentBudgetView`
  - can answer goal-related questions using `ActiveBodyPlanView`
  - does not commit any canonical state
  - does not trigger intake, rescue, or calibration flow
- `required_tests[]`:
  - general_chat budget query regression
  - general_chat goal query regression
  - no-state-mutation regression
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `parallelizable_implementation`
- `default_worker_posture`: `workers handle implementation; keep product truth local`

#### Slice `2.7g-memory-statistical-pattern-foundation`

- `parent_workflow_id`: `2.7-memory-retrieval-deepening`
- `title`: `Memory statistical pattern foundation (L2a)`
- `goal`: implement the deterministic L2a statistical pattern aggregation that produces PreferenceProfileSummary from MealItem history, triggered by nightly consolidation
- `depends_on_slices[]`:
  - `2.7e-workflow-routing-pass-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L4A_MEMORY_MODEL_SPEC.md`
  - `docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md`
  - `docs/specs/L2_DATA_STATE_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/memory_consolidation.py`
  - `app/infrastructure/preference_profile_persistence.py`
  - `tests/test_memory_consolidation.py`
- `forbidden_touch_areas[]`:
  - LLM semantic extraction (L2b)
  - recommendation runtime
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: committed MealItem history, nightly consolidation trigger
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - `PreferenceProfileSummary` is pre-materialized after consolidation
  - `item_kind_distribution`, `staple_type_distribution`, `drink_preference_strength` are correctly computed
  - `time_of_day_patterns` correctly aggregates by hour bucket
  - consolidation triggers when 24h elapsed and new MealItems exist
  - `freshness_posture` is set to `stale` after 48h without consolidation
- `required_tests[]`:
  - statistical aggregation regression
  - consolidation trigger condition regression
  - freshness posture regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `parallelizable_implementation`
- `default_worker_posture`: `workers handle implementation`

#### Slice `2.7h-memory-semantic-pattern-extraction`

- `parent_workflow_id`: `2.7-memory-retrieval-deepening`
- `title`: `Memory semantic pattern extraction (L2b)`
- `goal`: implement the LLM-based semantic pattern extraction that produces contextual, temporal, and trend-based preference patterns from raw MealItem time series
- `depends_on_slices[]`:
  - `2.7g-memory-statistical-pattern-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L4A_MEMORY_MODEL_SPEC.md`
  - `docs/specs/L3_5_PROMPT_CONTRACT_SPEC.md`
  - `docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/memory_semantic_extraction.py`
  - `app/infrastructure/semantic_pattern_persistence.py`
  - `tests/test_memory_semantic_extraction.py`
- `forbidden_touch_areas[]`:
  - L2a statistical pattern code
  - confirmed memory write path
  - recommendation runtime
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: 21 committed MealItems, 7-day trigger gap, raw MealItem fields including occurred_at, item_name, consumption_note
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - extraction triggers when 21 new MealItems accumulated AND 7 days since last extraction
  - LLM outputs structured semantic pattern items with pattern_type, description, confidence, content_hash
  - patterns with confidence < 0.5 are not written to L2b
  - same content_hash increments reinforcement_count instead of creating duplicate
  - extraction does not trigger confirmed memory upgrade (that is a separate slice)
- `required_tests[]`:
  - extraction trigger condition regression
  - semantic pattern schema regression
  - low-confidence filter regression
  - content_hash dedup regression
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `single_threaded_decision_work`
- `default_worker_posture`: `keep LLM pass design local`

#### Slice `2.7i-confirmed-memory-upgrade-path`

- `parent_workflow_id`: `2.7-memory-retrieval-deepening`
- `title`: `Confirmed memory upgrade path`
- `goal`: implement the two paths for confirmed memory creation: direct user declaration and LLM-judged upgrade from L2b semantic patterns
- `depends_on_slices[]`:
  - `2.7h-memory-semantic-pattern-extraction`
- `required_truth_docs[]`:
  - `docs/specs/L4A_MEMORY_MODEL_SPEC.md`
  - `docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/confirmed_memory_service.py`
  - `app/infrastructure/confirmed_memory_persistence.py`
  - `app/application/workflow_routing_pass.py` only for declaration detection
  - `tests/test_confirmed_memory.py`
- `forbidden_touch_areas[]`:
  - recommendation runtime
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: L2b semantic patterns, utterance_override state, user declaration detection
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - user declaration (「記住我不喝含糖飲料」) directly writes to confirmed memory without reinforcement_count gate
  - L2b pattern with reinforcement_count ≥ 5 and confidence ≥ 0.8 triggers LLM upgrade judgment
  - confirmed memory is not auto-expired unless overridden by new declaration or behavior
  - negative preference memory is written as first-class object, not as a tag on positive preference
- `required_tests[]`:
  - direct declaration write regression
  - L2b upgrade threshold regression
  - negative preference first-class regression
  - no-auto-expiry regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `single_threaded_decision_work`
- `default_worker_posture`: `keep memory write path design local`

### 2.8 Recommendation

#### Slice `2.8a-recommendation-context-and-candidate-foundation`

- `parent_workflow_id`: `2.8-recommendation`
- `title`: `Recommendation context and candidate foundation`
- `goal`: implement the first two nodes of the recommendation 3-node graph: context shaping and candidate retrieval/filtering, using historical MealItem and golden orders as v1 candidate sources
- `depends_on_slices[]`:
  - `2.7i-confirmed-memory-upgrade-path`
  - `2.6b-calibration-posture-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L4A_MEMORY_MODEL_SPEC.md`
  - `docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/recommendation_context.py`
  - `app/application/recommendation_candidate_retrieval.py`
  - `app/infrastructure/preference_profile_persistence.py`
  - `tests/test_recommendation_context.py`
  - `tests/test_recommendation_candidate_retrieval.py`
- `forbidden_touch_areas[]`:
  - recommendation response pass
  - proactive nudge logic
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: `CurrentBudgetView`, `ActiveBodyPlanView`, `PreferenceProfileSummary`, committed MealItem history, golden orders
- `ui_surface_dependency`: none
- `acceptance_criteria[]`:
  - context pass extracts hard constraints (remaining kcal) and soft preferences from PreferenceProfileSummary
  - candidate retrieval uses historical MealItem matches first, golden orders second
  - candidates are filtered by remaining kcal hard constraint
  - cold-start (empty PreferenceProfileSummary) falls back to safe defaults without error
  - location context is optional and gracefully absent
- `required_tests[]`:
  - context hard constraint extraction regression
  - candidate retrieval priority regression
  - cold-start fallback regression
  - kcal filter regression
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `parallelizable_implementation`
- `default_worker_posture`: `workers handle implementation`

#### Slice `2.8b-recommendation-ranking-and-response`

- `parent_workflow_id`: `2.8-recommendation`
- `title`: `Recommendation ranking and response`
- `goal`: implement the third node of the recommendation 3-node graph: ranking candidates by soft preferences and producing a chat response with quick actions
- `depends_on_slices[]`:
  - `2.8a-recommendation-context-and-candidate-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L3_5_PROMPT_CONTRACT_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/recommendation_ranking.py`
  - `app/application/recommendation_response.py`
  - `app/web/recommendation_routes.py`
  - `tests/test_recommendation_ranking.py`
  - `tests/test_recommendation_response.py`
- `forbidden_touch_areas[]`:
  - intake flow
  - rescue flow
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: candidate set from 2.8a, `PreferenceProfileSummary`, budget posture
- `ui_surface_dependency`: chat response only (v1 reactive)
- `acceptance_criteria[]`:
  - ranking applies hard constraints first, soft preferences second
  - chat response shows 1 top pick + 1-2 backup picks
  - `幫我記這個` quick action correctly routes to intake flow via hint_packet
  - recommendation does not create canonical state
  - rescue-active state correctly filters candidates exceeding rescue overlay budget
- `required_tests[]`:
  - ranking hard-constraint-first regression
  - chat response density regression
  - intake handoff via hint_packet regression
  - no-state-mutation regression
  - rescue-aware filtering regression
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `parallelizable_implementation`
- `default_worker_posture`: `workers handle implementation`

#### Slice `2.8c-calibration-proposal-response-surface`

- `parent_workflow_id`: `2.8-recommendation`
- `title`: `Calibration proposal response surface`
- `goal`: implement the calibration proposal response pass that presents a single primary proposal to the user in chat, with accept/defer/reject quick actions and UI mirror
- `depends_on_slices[]`:
  - `2.6c-calibration-proposal-gate-foundation`
  - `2.7e-workflow-routing-pass-foundation`
- `required_truth_docs[]`:
  - `docs/specs/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L3_5_PROMPT_CONTRACT_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/calibration_proposal_response.py`
  - `app/application/calibration_commit_bridge.py`
  - `app/web/calibration_routes.py`
  - `tests/test_calibration_proposal_response.py`
- `forbidden_touch_areas[]`:
  - calibration model internals
  - recommendation runtime
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: calibration proposal gate output, `ActiveBodyPlanView`, `CurrentBudgetView`
- `ui_surface_dependency`: chat primary, UI mirror
- `acceptance_criteria[]`:
  - calibration proposal surfaces as single primary recommendation in chat
  - accept correctly writes new BodyPlan version and refreshes CurrentBudgetView
  - 11:00 rule correctly determines effective_from
  - `logging_quality_first` proposal correctly surfaces without plan change
  - `plan_reset` only surfaces when recovery_viability is non_viable
- `required_tests[]`:
  - single-primary-proposal regression
  - accept-side BodyPlan write regression
  - 11:00 effective_from regression
  - logging_quality_first no-plan-change regression
  - plan_reset gate regression
- `benchmark_seed_required`: `true`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `single_threaded_decision_work`
- `default_worker_posture`: `keep calibration commit semantics local`

### 2.9 Proactive Nudges

#### Slice `2.9a-proactive-scheduler-foundation`

- `parent_workflow_id`: `2.9-proactive-nudges`
- `title`: `Proactive scheduler foundation`
- `goal`: implement the ProactiveScheduler with budget_alert_check and meal_reminder_check, UserProactivePreference, quiet hours, and max_daily_proactive_count enforcement
- `depends_on_slices[]`:
  - `2.8b-recommendation-ranking-and-response`
  - `2.8c-calibration-proposal-response-surface`
- `required_truth_docs[]`:
  - `docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md`
  - `docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L2_DATA_STATE_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/proactive_scheduler.py`
  - `app/infrastructure/user_proactive_preference_persistence.py`
  - `app/web/proactive_routes.py`
  - `tests/test_proactive_scheduler.py`
- `forbidden_touch_areas[]`:
  - recommendation runtime
  - calibration runtime
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: `CurrentBudgetView`, `UserProactivePreference`, `ProactiveStatusView`, cooldown state
- `ui_surface_dependency`: none (triggers chat messages)
- `acceptance_criteria[]`:
  - budget_alert fires when remaining_kcal < 0 or overshoot > 15%
  - emergency budget_alert (overshoot > 30%) bypasses quiet hours and max_daily_proactive_count
  - meal_reminder fires every 30 min during 07:00-22:00 when no meals logged in meal window
  - quiet hours correctly suppress non-emergency triggers
  - max_daily_proactive_count resets at 00:00 local time
  - UserProactivePreference can be updated via chat or UI
- `required_tests[]`:
  - budget_alert threshold regression
  - emergency bypass regression
  - quiet hours suppression regression
  - max_daily_count reset regression
  - UserProactivePreference update regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `parallelizable_implementation`
- `default_worker_posture`: `workers handle implementation`

#### Slice `2.9b-proactive-rescue-nudge`

- `parent_workflow_id`: `2.9-proactive-nudges`
- `title`: `Proactive rescue nudge`
- `goal`: implement the proactive rescue trigger that asks the user if they want to see a rescue plan when overshoot is detected, as a separate chat message from intake
- `depends_on_slices[]`:
  - `2.9a-proactive-scheduler-foundation`
  - `2.5d-rescue-response-surface`
- `required_truth_docs[]`:
  - `docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md`
  - `docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/proactive_scheduler.py`
  - `app/application/rescue_runtime.py`
  - `tests/test_proactive_rescue_nudge.py`
- `forbidden_touch_areas[]`:
  - intake response surfaces
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: `CurrentBudgetView`, overshoot detection, cooldown state
- `ui_surface_dependency`: none (separate chat message)
- `acceptance_criteria[]`:
  - proactive rescue fires as separate chat message, never embedded in intake reply
  - system asks 「要不要看看救援方案？」before sending full rescue proposal
  - user saying yes triggers rescue flow
  - user saying no marks trigger as dismissed with cooldown
  - preventive rescue (「星期六要吃大餐，現在先少吃」) correctly routes to rescue flow via workflow_routing_pass
- `required_tests[]`:
  - separate-message regression
  - ask-before-proposal regression
  - yes-triggers-rescue regression
  - no-dismisses-with-cooldown regression
  - preventive rescue routing regression
- `benchmark_seed_required`: `true`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `parallelizable_implementation`
- `default_worker_posture`: `workers handle implementation`

#### Slice `2.9c-proactive-recommendation-nudge`

- `parent_workflow_id`: `2.9-proactive-nudges`
- `title`: `Proactive recommendation nudge`
- `goal`: implement the proactive recommendation trigger that surfaces meal suggestions at meal times when the user has remaining budget and no recent meal logged
- `depends_on_slices[]`:
  - `2.9a-proactive-scheduler-foundation`
  - `2.8b-recommendation-ranking-and-response`
- `required_truth_docs[]`:
  - `docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md`
  - `docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/proactive_scheduler.py`
  - `app/application/recommendation_context.py`
  - `tests/test_proactive_recommendation_nudge.py`
- `forbidden_touch_areas[]`:
  - intake flow
  - rescue flow
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: `CurrentBudgetView`, `ProactiveStatusView`, meal timing patterns, suppression state
- `ui_surface_dependency`: none (chat message)
- `acceptance_criteria[]`:
  - proactive recommendation fires only during meal windows (07:00-22:00)
  - suppression / cooldown correctly prevents repeated nudges
  - nudge respects max_daily_proactive_count
  - nudge does not fire when rescue is active and budget is already constrained
- `required_tests[]`:
  - meal-window timing regression
  - suppression regression
  - rescue-active no-nudge regression
  - max_daily_count regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `parallelizable_implementation`
- `default_worker_posture`: `workers handle implementation`

#### Slice `2.9d-proactive-calibration-nudge`

- `parent_workflow_id`: `2.9-proactive-nudges`
- `title`: `Proactive calibration nudge`
- `goal`: implement the proactive calibration trigger that notifies the user when calibration conditions are met (14-day window + 5 observations) and surfaces the calibration proposal
- `depends_on_slices[]`:
  - `2.9a-proactive-scheduler-foundation`
  - `2.8c-calibration-proposal-response-surface`
- `required_truth_docs[]`:
  - `docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md`
  - `docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/application/proactive_scheduler.py`
  - `app/application/calibration_model.py`
  - `tests/test_proactive_calibration_nudge.py`
- `forbidden_touch_areas[]`:
  - recommendation runtime
  - rescue runtime
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: `BodyObservation` history, intake coverage summary, calibration posture output
- `ui_surface_dependency`: none (chat message)
- `acceptance_criteria[]`:
  - calibration nudge fires only when 14-day window elapsed AND 5+ observations exist
  - nudge fires at most once per day (nightly check)
  - nudge correctly surfaces calibration proposal via chat
  - `logging_quality_first` posture surfaces as nudge to improve logging, not as plan change
- `required_tests[]`:
  - 14-day + 5-observation gate regression
  - once-per-day regression
  - logging_quality_first nudge regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `false`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `parallelizable_implementation`
- `default_worker_posture`: `workers handle implementation`

### 0. Onboarding

#### Slice `0.a-onboarding-ui-and-body-plan-bootstrap`

- `parent_workflow_id`: `0-onboarding`
- `title`: `Onboarding UI and BodyPlan bootstrap`
- `goal`: implement the onboarding flow where the user fills a UI form with basic info, the system deterministically computes the initial BodyPlan, and chat can update it if the user changes their mind
- `depends_on_slices[]`:
  - `2.4a-body-observation-persistence`
- `required_truth_docs[]`:
  - `docs/specs/L0A_ONBOARDING_FLOW_SPEC.md`
  - `docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md`
  - `docs/specs/L2_DATA_STATE_SPEC.md`
  - `docs/specs/L2A_DATA_DICTIONARY_SPEC.md`
  - `docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md`
- `allowed_touch_areas[]`:
  - `app/web/onboarding_routes.py`
  - `app/web/body_plan_routes.py`
  - `app/web/today_routes.py`
  - `app/application/onboarding_service.py`
  - `app/application/active_body_plan_read_model.py`
  - `app/application/current_budget_answer.py`
  - `app/infrastructure/body_plan_persistence.py`
  - `app/infrastructure/active_body_plan_read_model.py`
  - `app/infrastructure/canonical_persistence.py`
  - `app/application/canonical_commit_bridge.py`
  - `app/models.py`
  - `app/database.py`
  - `app/domain/canonical_models.py`
  - `app/domain/__init__.py`
  - `alembic/versions/*body_profile_bootstrap_foundation.py`
  - `tests/test_onboarding.py`
  - `tests/test_active_body_plan_read_model.py`
  - `tests/test_current_budget_answer.py`
  - `tests/test_routes_body_plan_ui.py`
  - `tests/test_routes_today_ui.py`
  - `tests/test_canonical_persistence.py`
- `forbidden_touch_areas[]`:
  - calibration proposal runtime
  - recommendation runtime
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- `state_dependencies`: BodyPlan write path, DayBudgetLedger initialization, safety_floor_kcal from sex field
- `ui_surface_dependency`: onboarding UI form
- `acceptance_criteria[]`:
  - UI form collects sex, current_weight_kg, height_cm, age_years, goal_type
  - system deterministically computes recommended_target_kcal using Mifflin-St Jeor
  - safety_floor_kcal is set from sex (1200 female, 1500 male, 1500 prefer_not_to_say)
  - raw_target_kcal is clamped to safety_floor_kcal
  - BodyPlan is created with plan_source: onboarding_bootstrap
  - DayBudgetLedger is created for current day after BodyPlan is accepted
  - `/body-plan` can show the active target after bootstrap
  - `/today/current-budget` reflects the same target after bootstrap
  - committed intake meals update `DayBudgetLedger` using active body-plan fallback when explicit budget is absent
  - skipping onboarding allows intake logging but hides budget display
  - gain_weight goal_type skips rescue trigger
- `required_tests[]`:
  - Mifflin-St Jeor calculation regression
  - safety_floor_kcal clamp regression
  - DayBudgetLedger initialization regression
  - skip-onboarding fallback regression
  - gain_weight rescue-skip regression
- `benchmark_seed_required`: `false`
- `handoff_required`: `true`
- `parallelizable_with[]`: `[]`
- `delegation_mode`: `parallelizable_implementation`
- `default_worker_posture`: `workers handle implementation`
