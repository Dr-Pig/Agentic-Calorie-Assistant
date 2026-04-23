# Handoff

- `handoff_id`: `HANDOFF-2026-04-12-020-RECOMMENDED-TARGET-KCAL-FOUNDATION`
- `task_id`: `TASK-2026-04-12-020-RECOMMENDED-TARGET-KCAL-FOUNDATION`
- `slice_id`: `2.6a-recommended-target-kcal-foundation`
- `current_status`: `task completed; deterministic recommended-target baseline checked in`

## What Changed

- added a standalone deterministic `recommended_target_kcal` calculator using `Mifflin-St Jeor`, fixed activity multipliers, and weekly-loss-to-daily-deficit conversion
- clamped the personalized target to `BodyPlan.safety_floor_kcal` so hard floor and recommended target remain separate
- added focused regression tests for floor clamping and larger-body personalized targets
- synced the formula choice into explicit repository truth docs

## What Did Not Change

- no UI or recommendation response surface was added
- no calibration feedback loop or body-trend correction was added
- no rescue hard-floor semantics were changed
- no protected legacy files were touched

## Files Touched

- `app/application/target_calculation.py`
- `tests/test_target_calculation.py`
- `docs/references/RECOMMENDED_TARGET_KCAL_DECISION_NOTE.md`
- `docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md`
- `docs/exec-plans/active/tasks/TASK-2026-04-12-020-RECOMMENDED-TARGET-KCAL-FOUNDATION.md`

## Blockers

- none for this slice

## Tests Run

- `python -m pytest tests/test_target_calculation.py -q`

## Source Of Truth Docs Touched

- [docs/references/RECOMMENDED_TARGET_KCAL_DECISION_NOTE.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references/RECOMMENDED_TARGET_KCAL_DECISION_NOTE.md)
- [docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md)

## Reality Drift

- the worker correctly produced a bounded deterministic implementation, but the formula family had to be promoted into explicit truth before the task could be governance-complete

## Next Recommended Action

Use this deterministic baseline as the input posture for later calibration / recommendation work, not as a substitute for future weight-trend-based calibration.

## Unsafe Assumptions To Avoid

- do not treat `recommended_target_kcal` as the same thing as `BodyPlan.safety_floor_kcal`
- do not assume this baseline replaces later calibration from intake and body-trend evidence
- do not silently change formula coefficients in code without updating canonical truth
