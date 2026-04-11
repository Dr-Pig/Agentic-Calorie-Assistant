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
