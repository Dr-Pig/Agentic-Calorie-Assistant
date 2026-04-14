# Task Artifact

- `task_id`: `TASK-2026-04-12-027-RESCUE-PROPOSAL-ARTIFACT-FOUNDATION`
- `slice_id`: `2.5b-rescue-proposal-artifact-foundation`
- `status`: `COMPLETED`
- `owner`: `planner`
- `started_at`: `2026-04-12`
- `execution_surface`: `worker-worthy`
- `selection_reason`: `This slice is a bounded production implementation in rescue application modules; the write scope is clear, but the artifact-shaping work is noisy enough to justify isolating it from planner context.`

## Source Of Truth Refs

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md)
- [docs/specs/L3M_GUARDRAIL_MATH_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3M_GUARDRAIL_MATH_SPEC.md)
- [docs/governance/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/BUILD_FILE_PLACEMENT_RULES.md)
- [docs/governance/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/LAYER_DEPENDENCY_RULES.md)

## Goal

Turn deterministic rescue trigger / assessment truth into a structured proposal artifact without adding user-facing response wording, route/UI behavior, recommendation wiring, or accept-side commit semantics.

## Planned Touch Files

- `app/application/rescue_proposal.py`
- `app/application/rescue_overlay.py` only if a narrow adapter or shared deterministic helper extraction is required
- `app/domain/canonical_models.py` only if a narrow typed artifact is truly needed
- `tests/test_rescue_proposal.py`
- `tests/test_rescue_overlay.py` only if a narrow cross-module regression is required
- `docs/exec-plans/active/tasks/TASK-2026-04-12-027-RESCUE-PROPOSAL-ARTIFACT-FOUNDATION.md`

## Forbidden Files

- `app/routes.py`
- `app/usecases/text_meal.py`
- `app/schemas.py`
- recommendation / proactive / retrieval logic
- rescue response wording or UI surfaces
- proposal accept / canonical writeback behavior beyond already-existing overlay skeletons
- calibration proposal logic
- freeze-growth files unless a real re-plan trigger is hit and explicitly recorded

## New Files Expected

- `app/application/rescue_proposal.py`
- `tests/test_rescue_proposal.py`

## Completion Criteria

- deterministic-first rescue proposal artifact exists
- artifact includes at least:
  - `rescue_needed`
  - `recovery_viability`
  - `rescue_horizon`
  - `allowed_rescue_families[]`
  - `blocked_rescue_families[]`
  - `recommended_rescue_family`
  - explicit `no_rescue` or `rescue_stop_and_escalate` posture when appropriate
- option payloads never violate `BodyPlan.safety_floor_kcal`
- no user-facing response generation is added
- no recommendation/proactive side effects are added
- no accept-side commit semantics are expanded

## Tests To Run

- `python -m pytest tests/test_rescue_proposal.py -q`
- `python -m pytest tests/test_rescue_overlay.py -q`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Expected Re-plan Impact

Will determine whether rescue is ready to stop at the first product-semantics human gate before option shaping / response work, or whether proposal artifact boundaries are still unstable and need one more bounded rescue correction.

## Completion Record

- `completed_at`: `2026-04-12`
- `actual_touch_files[]`:
  - `app/application/rescue_proposal.py`
  - `tests/test_rescue_proposal.py`
  - `docs/exec-plans/active/tasks/TASK-2026-04-12-027-RESCUE-PROPOSAL-ARTIFACT-FOUNDATION.md`
- `tests_run[]`:
  - `python -m pytest tests/test_rescue_proposal.py -q`
  - `python -m pytest tests/test_rescue_overlay.py -q`
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`
- `reality_drift_notes`:
  - `none`
- `source_of_truth_updated`:
  - `no`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`:
  - `docs/exec-plans/completed/handoff/HANDOFF-2026-04-12-027-RESCUE-PROPOSAL-ARTIFACT-FOUNDATION.md`
