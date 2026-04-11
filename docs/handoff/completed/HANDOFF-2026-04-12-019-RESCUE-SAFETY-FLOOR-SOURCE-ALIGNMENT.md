# Handoff

- `handoff_id`: `HANDOFF-2026-04-12-019-RESCUE-SAFETY-FLOOR-SOURCE-ALIGNMENT`
- `task_id`: `TASK-2026-04-12-019-RESCUE-SAFETY-FLOOR-SOURCE-ALIGNMENT`
- `slice_id`: `2.5a-rescue-deterministic-overlay`
- `current_status`: `task completed; rescue safety-floor source aligned to canonical BodyPlan hard-floor truth`

## What Changed

- deterministic rescue runtime now resolves `safety_floor(user)` from active `BodyPlan.safety_floor_kcal` or an explicit override
- rescue runtime no longer relies on hidden sex / gender / profile fallback inside runtime code
- rescue regressions now cover the persisted body-plan safety-floor path
- canonical rescue spec now distinguishes hard floor from separately computed personalized target

## What Did Not Change

- no rescue UI or rescue response surface was added
- no recommendation or calibration target calculator was added in this slice
- no recommendation, memory, or proactive logic was introduced
- no protected legacy files were touched

## Files Touched

- `app/application/rescue_overlay.py`
- `tests/test_rescue_overlay.py`
- `tests/test_canonical_persistence.py`
- `docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md`
- `docs/references/SAFETY_FLOOR_AND_TARGET_DECISION_NOTE.md`
- `docs/exec-plans/active/tasks/TASK-2026-04-12-019-RESCUE-SAFETY-FLOOR-SOURCE-ALIGNMENT.md`

## Blockers

- none for this slice

## Tests Run

- `python -m pytest tests/test_rescue_overlay.py -q`
- `python -m pytest tests/test_canonical_persistence.py -q -k "body_plan_persists_safety_floor_kcal"`

## Source Of Truth Docs Touched

- [docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md)
- [docs/references/SAFETY_FLOOR_AND_TARGET_DECISION_NOTE.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references/SAFETY_FLOOR_AND_TARGET_DECISION_NOTE.md)

## Reality Drift

- older rescue wording still treated `1200 / 1500` as an in-runtime heuristic fallback, while newer canonical state already treated `BodyPlan.safety_floor_kcal` as the resolved scalar source
- this slice closed that cross-spec drift by making `1200 / 1500` a hard lower-bound policy and moving personalized daily target math into a separate queued task

## Next Recommended Action

Keep `TASK-2026-04-12-020-RECOMMENDED-TARGET-KCAL-FOUNDATION` queued until its slice registry entry is formalized, then open a bounded worker for deterministic target calculation.

## Unsafe Assumptions To Avoid

- do not treat `BodyPlan.safety_floor_kcal` as the user’s personalized daily target
- do not reintroduce hidden sex-based runtime fallback when the canonical scalar is missing
- do not open `TASK-020` as an autonomous loop task until its slice is formally registered and bounded
