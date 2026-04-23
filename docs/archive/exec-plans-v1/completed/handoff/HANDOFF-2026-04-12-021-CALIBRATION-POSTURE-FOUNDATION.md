# Handoff

- `handoff_id`: `HANDOFF-2026-04-12-021-CALIBRATION-POSTURE-FOUNDATION`
- `task_id`: `TASK-2026-04-12-021-CALIBRATION-POSTURE-FOUNDATION`
- `slice_id`: `2.6b-calibration-posture-foundation`
- `current_status`: `task completed; deterministic calibration posture foundation checked in`

## What Changed

- added a deterministic calibration model that classifies `insufficient_data`, `logging_quality_first`, `monitor_only`, `calibration_candidate`, and `high_confidence_mismatch`
- kept `operating_expenditure_estimate_kcal` separate from `intake_estimation_bias_posture`
- encoded the v1 `14-day / 5-observation / 80% intake coverage` thresholds in focused regression tests

## What Did Not Change

- no calibration proposal runtime was added
- no canonical `BodyPlan` writeback or accept flow was introduced
- no UI, recommendation, rescue, or memory-selector logic was changed
- no protected legacy files were touched

## Files Touched

- `app/application/calibration_model.py`
- `tests/test_calibration_model.py`
- `docs/exec-plans/active/tasks/TASK-2026-04-12-021-CALIBRATION-POSTURE-FOUNDATION.md`

## Blockers

- none for this slice

## Tests Run

- `python -m pytest tests/test_calibration_model.py -q`
- `python scripts/check_layer_integrity.py`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Source Of Truth Docs Touched

- none

## Reality Drift

- the first calibration-core slice stayed intentionally narrower than proposal policy or canonical writeback
- the next calibration decision now sits at the proposal-gate boundary, not at `BodyPlan` adoption

## Next Recommended Action

Formalize and dispatch a bounded deterministic proposal-gate slice that consumes the `2.6b` calibration outputs and decides whether proposal flow is allowed under `L3.3B`.

## Unsafe Assumptions To Avoid

- do not treat `proposal_eligibility` as equivalent to proposal option generation
- do not silently adopt `operating_expenditure_estimate_kcal` into active `BodyPlan` without a proposal-first boundary
- do not merge calibration posture, proposal policy, and UI response into one slice
