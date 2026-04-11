# Task Artifact

- `task_id`: `TASK-2026-04-11-011-HARNESS-HARD-GATE-HARDENING`
- `slice_id`: `repo-governance-hard-gate-hardening`
- `status`: `COMPLETED`
- `owner`: `codex-local`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
- [docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)
- [docs/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md)
- [docs/GITHUB_REPO_GOVERNANCE.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/GITHUB_REPO_GOVERNANCE.md)

## Goal

Turn the remaining harness governance gaps into executable gates before the next feature-heavy build wave.

## Planned Touch Files

- `scripts/check_task_checkin_and_handoff.ps1`
- `scripts/check_fat_files.ps1`
- `scripts/check_migration_discipline.py`
- `.github/workflows/ci.yml`
- `AGENTS.md`
- `docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md`
- `docs/TASK_CHECKIN_PROTOCOL.md`
- `docs/exec-plans/active/REPLAN_LOG.md`

## Forbidden Files

- application runtime behavior unrelated to governance
- recommendation / memory / calibration feature files
- protected thin-entrypoint files unless required by governance-only wiring

## Completion Criteria

- task artifacts are CI-audited in block mode
- freeze-growth files require explicit staged justification when touched
- schema-sensitive ORM changes are blocked without Alembic migrations
- required governance docs reflect the new hard-gate behavior

## Tests To Run

- `powershell -ExecutionPolicy Bypass -File scripts/check_task_checkin_and_handoff.ps1 -AuditRepo`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
- `python scripts/check_migration_discipline.py`
- `python scripts/check_layer_integrity.py`
- `python -m pytest -q -m smoke`

## Expected Re-plan Impact

Should reduce the remaining harness drift between local hooks, CI, and task/migration governance before the next execution bundle starts.

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `scripts/check_task_checkin_and_handoff.ps1`
  - `scripts/check_fat_files.ps1`
  - `scripts/check_migration_discipline.py`
  - `.github/workflows/ci.yml`
  - `AGENTS.md`
  - `docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md`
  - `docs/TASK_CHECKIN_PROTOCOL.md`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-011-HARNESS-HARD-GATE-HARDENING.md`
  - `docs/exec-plans/active/REPLAN_LOG.md`
- `tests_run[]`:
  - `powershell -ExecutionPolicy Bypass -File scripts/check_task_checkin_and_handoff.ps1 -AuditRepo`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
  - `python scripts/check_migration_discipline.py`
  - `python scripts/check_layer_integrity.py`
  - `python -m pytest -q -m smoke`
- `reality_drift_notes`:
  - `migration discipline is intentionally scoped to app/models.py for the first hard-gate pass; broader ORM boundary coverage can expand later without delaying current build work`
- `source_of_truth_updated`:
  - `yes`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`:
  - `none`
