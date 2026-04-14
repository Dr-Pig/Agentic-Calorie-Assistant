# Harness Go / No-Go

Use this before starting a new build wave. It should take about 30 seconds.

## Go

- `main` has branch protection enabled with required checks: `layer-integrity`, `smoke-tests`, `integration-tests`
- `python scripts/check_layer_integrity.py` passes
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings` passes
- `python -m pytest -q -m smoke` passes
- `python -m pytest -q -m integration` passes
- `docs/exec-plans/active/REPLAN_LOG.md` has a current record for the last governance change
- the current task artifact includes `actual_touch_files[]` and `tests_run[]`

## No-Go

- any required check is missing or red
- any protected legacy file is growing
- any freeze-growth file exceeds its frozen line count
- any task artifact marked `COMPLETED` is missing structured completion fields
- `app/application/conversation_state_loader.py` or `app/application/conversation_state_assembler.py` fails layer integrity or targeted tests

## Fast Decision

- `GO` if every item above is true
- `NO-GO` if any item above is false
