# Current Execution Plan

> [!WARNING]
> **Authority Limit**: This plan only details the execution of the *current and next stages*. It does NOT dictate the overall workflow order.
> For the canonical dependency sequence, always refer to:
> **[`WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)**

## Current Workflow Focus

- `2.3 Today UI / Read Models`
- `today-surface follow-through closed; planner re-evaluation required before next bounded slice`

## Current Critical-Path Segment

- `2.3 Today UI / Read Models`
- `2.2 Multi-turn Intake + Correction` is now stable enough to hand off into the next canonical segment
- `2.4 Weight / Body Observation` remains required before `2.6 Calibration`, but it does not block the current `2.2-2.5` mainline segment

## Current Active Slices

- `none`

## Next Workflow Focus

- `planner formalization required before the next bounded slice`

## Next Queued Slices

- `none`

## Legal-Next Set And Best-Next Selection

Current legal-next set:

- `none`

Selected best-next slice:

- `none`

Selection reason:

- all currently formalized bounded slices in the active wave are complete
- the next bounded implementation step requires new planner formalization, not immediate dispatch
- continuing without a formalized next slice would widen scope beyond the current execution plan

## Last Re-plan At

- `2026-04-12`

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
- `TASK-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION` has been re-scoped to respect protected legacy files, layer dependency rules, and freeze-growth discipline before further implementation continues
- historical correction hardening is now complete and validated under the new harness gates, so active execution can shift back to read-side follow-through
- `2.3a-current-budget-read-model` now needs a correction-aware follow-through pass, not a rerun of the original foundation slice
- `2.3a-current-budget-read-model` follow-through closed via regression coverage, so active work now shifts to the Today surface layer that consumes that read model
- `2.3b-low-fi-today-ui` now needs a date-aware follow-through after the `2.2` continuation and cross-midnight truth were revalidated
- `2.1e-web-search-fallback-lane` is now the next bounded intake slice after exact-db, clarify-required, and cannot-estimate all closed
- `2.1e-web-search-fallback-lane` hit a valid re-plan trigger because the exact-vs-search authority seam still lives in freeze-growth `app/application/evidence_assembly.py`
- `TASK-2026-04-12-017-EVIDENCE-TIER-POLICY-EXTRACTION` and `TASK-2026-04-12-018-SEARCH-AUTHORITY-TIER-SEPARATION` are complete; `2.1e` can resume under the narrowed authority policy
- `TASK-2026-04-12-019-RESCUE-SAFETY-FLOOR-SOURCE-ALIGNMENT` closed the rescue safety-floor source drift; `1200 / 1500` now remain hard lower bounds while personalized daily target math is split into a separate queued task
- `2.6a-recommended-target-kcal-foundation` is now complete as a deterministic baseline and has explicit truth coverage for its formula family
- after `2.6a`, the next worthwhile slice is calibration-core formalization, not direct `2.7a-context-selector` implementation
- `2.7a-context-selector` remains planning-only until it has a formal registry entry and bounded write scope
- the first bounded calibration-core slice is now formalized as `2.6b-calibration-posture-foundation`
- `2.6b` intentionally stops before proposal policy, canonical writeback, and UI work
- `2.6b-calibration-posture-foundation` is now complete and archived with a completed handoff
- the next calibration-core slice is `2.6c-calibration-proposal-gate-foundation`, which still stops before option generation and accept-side writeback
- `2.6c-calibration-proposal-gate-foundation` is now complete, but calibration follow-through is intentionally paused
- active execution is returning to the product main flow because multi-turn intake is still not founder-fit complete
- `2.2a-active-meal-continuation` closed via regression proof; remaining `2.2` risk now sits in cross-midnight local-date attribution
- `2.2c-cross-midnight-attribution` is now complete; the next execution risk sits in making sure the `2.3` read side still reflects corrected local-date truth
- `2.3a-current-budget-read-model` follow-through is now complete, so the next execution risk sits in making sure the Today surface still reflects corrected local-date truth
- `2.3b-low-fi-today-ui` date-aware follow-through is now complete, so the current bounded wave is closed until a new slice is formalized

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

### Next Planner Selection

Most worthwhile next slice:

1. dispatch a bounded `2.3a-current-budget-read-model` follow-through slice that validates correction and cross-midnight local-date behavior on the read side
2. then reopen `2.3b-low-fi-today-ui` only if read-model truth remains aligned

## Active Task Artifacts

- sprint wrapper:
  - [`SPRINT-2026-04-CONTRACT-ASSIMILATION-INTAKE-CORRECTION.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/SPRINT-2026-04-CONTRACT-ASSIMILATION-INTAKE-CORRECTION.md)
- none
Completed task history has moved to [`docs/exec-plans/completed/tasks/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/completed/tasks).

## Active Handoff

- none

Completed handoff history has moved to [`docs/handoff/completed/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/completed).

## Working Rules

- do not write micro-tasks beyond the current workflow focus and the next workflow focus
- if `text_meal.py` or `app/schemas.py` absorbs another unrelated concern, stop and re-plan
- use behavior-first task wording; do not bind future work to a file unless the boundary is still clearly valid
- all execution decisions must conform to [`docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
