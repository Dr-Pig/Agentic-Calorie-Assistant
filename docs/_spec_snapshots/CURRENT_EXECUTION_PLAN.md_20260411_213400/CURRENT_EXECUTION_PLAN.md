# Current Execution Plan

> [!WARNING]
> **Authority Limit**: This plan only details the execution of the *current and next stages*. It does NOT dictate the overall workflow order.
> For the canonical dependency sequence, always refer to:
> **[`WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)**

## Current Workflow Focus

- `2.5 Rescue`
- `Integrated surface validation`

## Current Active Slices

- `2.5a-rescue-deterministic-overlay`
- `2.1d-cannot-estimate-lane`

## Next Workflow Focus

- `2.7 Memory / Retrieval Deepening`
- `intake lane hardening`

## Next Queued Slices

- `2.7a-context-selector` *(numbering aligned to canonical ordering; slice detail still pending formal registry entry)*
- `2.1d-cannot-estimate-lane`
- `2.1e-web-search-fallback-lane`

## Last Re-plan At

- `2026-04-11`

## Reality Drift Notes

- canonical persistence and typed commit bridge exist earlier than the original build map assumed
- `app/usecases/text_meal.py` remains a thin-entrypoint target, but is still heavier than desired
- `app/schemas.py` is carrying both legacy and new typed contract shapes
- legacy meal-log persistence still exists as a transitional path and must not regain source-of-truth status
- the old execution grouping was too capability-centric and did not reflect the true workflow dependency order
- `2.3a-current-budget-read-model` is now complete enough to unblock a low-fi today surface
- the next safe concurrency step is read-surface work plus body-observation persistence, not more intake-core parallelism
- `2.3b-low-fi-today-ui` is now code-complete and moved into closeout-complete status with a checked-in handoff
- `2.4a-body-observation-persistence` is complete enough to unblock a low-fi weight surface
- low-fi Today and Weight surfaces now both exist and are ready for the first integrated manual check
- the first integrated manual check passed for `/today` and `/weight` empty-state surfaces
- `2.5a-rescue-deterministic-overlay` now exists as deterministic math plus canonical overlay write-through, but still requires an explicit `safety_floor_kcal` input because canonical user/body state does not yet expose a stable sex-derived floor
- canonical `safety_floor(user)` is now being formalized as `active BodyPlan.safety_floor_kcal`, so later rescue/calibration work should read that scalar instead of re-deriving user attributes at runtime
- `2.1b-exact-db-item-lane` is complete; branded exact paths now preserve planner brand context and suppress unnecessary search when local exact truth is already present
- `2.1c-clarify-required-lane` is complete; blocking clarify now hard-stops proceedability and has a direct no-canonical-commit regression
- next-workflow numbering for memory/retrieval had drifted to `2.6`; canonical ordering uses `2.7`, so active-plan labels are now corrected without changing the underlying execution intent

## Stale Assumptions Removed

- active work is no longer "just build canonical persistence"; typed contract alignment is already part of the current phase
- future implementation must not assume recommendation/calibration/rescue are ready to start in parallel
- new work should not be added to `text_meal.py` or `app/schemas.py` without a boundary review
- recommendation is no longer treated as an early low-context phase target; memory-aware recommendation is intentionally later

## Current Workstream

### Foundation Work For 2.1 / 2.2

Complete:

- canonical SQLAlchemy records exist
- canonical commit bridge exists
- schema reset/export tooling exists
- basic canonical repository tests exist

Still needed:

- expand canonical read/query helpers needed by correction flows and later read models
- keep proposal/body-observation/proactive skeletons aligned with `L2A`
- keep transitional meal-log mapping explicit and contained

### Typed Runtime Contract Alignment For Intake

Complete:

- `CommitRequestCandidate`
- `MealItemPayload`
- `StageTraceEvent`
- typed canonical write path from legacy persistence

Still needed:

- align `DecisionPassResult` vocabulary to final `L3T`
- align `NutritionResolutionResult` vocabulary to final `L3T`
- migrate `PassExecutionEnvelope` toward final status vocabulary

### Intake Vertical Slice Hardening

Now in progress:

- keep text intake path working while shifting more logic to `app/application`
- reduce direct persistence/trace ownership inside `text_meal.py`

Immediate next tasks:

1. add or expand read/query helpers needed by intake correction and the upcoming today/read-model layer
2. tighten intake pass result vocabulary to `L3T`
3. continue thinning `text_meal.py` by moving boundary-safe logic into application services
4. capture founder-fit benchmark seed cases from real corrected flows

## Active Task Artifacts

- sprint wrapper:
  - [`SPRINT-2026-04-CONTRACT-ASSIMILATION-INTAKE-CORRECTION.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/SPRINT-2026-04-CONTRACT-ASSIMILATION-INTAKE-CORRECTION.md)

- [`TASK-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/tasks/TASK-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION.md)
  - `slice_id`: `2.2b-historical-correction`

Completed task history has moved to [`docs/exec-plans/completed/tasks/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/completed/tasks).

## Active Handoff

- [`HANDOFF-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/active/HANDOFF-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION.md)
  - tied to `TASK-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION`

Completed handoff history has moved to [`docs/handoff/completed/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/completed).

## Working Rules

- do not write micro-tasks beyond the current workflow focus and the next workflow focus
- if `text_meal.py` or `app/schemas.py` absorbs another unrelated concern, stop and re-plan
- use behavior-first task wording; do not bind future work to a file unless the boundary is still clearly valid
- all execution decisions must conform to [`docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
