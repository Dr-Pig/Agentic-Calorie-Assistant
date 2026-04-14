# TASK-2026-04-11-013 — Doc Gate And Archival Cleanup

- `task_id`: `TASK-2026-04-11-013-DOC-GATE-AND-ARCHIVAL-CLEANUP`
- `slice_id`: `governance-doc-entrypoint-hardening`
- `status`: `COMPLETED`
- `owner`: `codex`
- `started_at`: `2026-04-11`
- `completed_at`: `2026-04-11`

## Source Of Truth Refs

- [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
- [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md)
- [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/archive/AGENT_LOADING_PATH.md)
- [docs/governance/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/TASK_CHECKIN_PROTOCOL.md)
- [docs/governance/SPEC_EDITING_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/SPEC_EDITING_PROTOCOL.md)
- [docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)

## Planned Touch Files

- `scripts/check_protected_doc_rewrites.ps1`
- `.githooks/pre-commit`
- `.github/workflows/ci.yml`
- `scripts/check_task_checkin_and_handoff.ps1`
- `docs/governance/TASK_CHECKIN_PROTOCOL.md`
- `docs/governance/SPEC_EDITING_PROTOCOL.md`
- `docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md`
- `docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md`
- `docs/exec-plans/reference/handoff/README.md`
- `docs/index.md`

## Forbidden Files

- `docs/specs/**`
- `app/**`
- `alembic/**`

## Goal

Harden entrypoint/governance docs against near-total rewrites and clean `active/` vs `completed/` task/handoff drift so agents load the correct current state by default.

## Completion Criteria

- protected entrypoint and governance docs have a staged rewrite-churn blocker
- completed tasks no longer remain under `docs/exec-plans/active/tasks/`
- completed handoffs no longer remain under `docs/exec-plans/active/handoff/`
- current execution plan points active readers only at still-active task/handoff artifacts

## Tests To Run

- `powershell -ExecutionPolicy Bypass -File scripts/check_protected_doc_rewrites.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/check_task_checkin_and_handoff.ps1 -AuditRepo`
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`

## Expected Re-plan Impact

- none on product behavior
- reduces docs bootstrap drift and archival confusion for future agents

## Completion Record

- `actual_touch_files[]`:
  - `scripts/check_protected_doc_rewrites.ps1`
  - `.githooks/pre-commit`
  - `.github/workflows/ci.yml`
  - `scripts/check_task_checkin_and_handoff.ps1`
  - `docs/governance/TASK_CHECKIN_PROTOCOL.md`
  - `docs/governance/SPEC_EDITING_PROTOCOL.md`
  - `docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md`
  - `docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md`
  - `docs/exec-plans/reference/handoff/README.md`
  - `docs/index.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-013-DOC-GATE-AND-ARCHIVAL-CLEANUP.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-002-READMODEL-FOUNDATION.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-003-LOWFI-TODAY-UI.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-004-BODY-OBSERVATION-PERSISTENCE.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-005-WEIGHT-UI.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-006-RESCUE-DETERMINISTIC-OVERLAY.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-007-EXACT-DB-ITEM-LANE.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-008-CLARIFY-REQUIRED-LANE.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-009-CANNOT-ESTIMATE-LANE.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-010-LAYER-INTEGRITY-WARNING-CLEANUP.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-011-HARNESS-HARD-GATE-HARDENING.md`
  - `docs/exec-plans/completed/tasks/TASK-2026-04-11-012-ENTRYPOINT-DOC-LOADING-REORG.md`
  - `docs/exec-plans/completed/handoff/HANDOFF-2026-04-11-002-READMODEL-FOUNDATION.md`
  - `docs/exec-plans/completed/handoff/HANDOFF-2026-04-11-003-LOWFI-TODAY-UI.md`
  - `docs/exec-plans/completed/handoff/HANDOFF-2026-04-11-005-WEIGHT-UI.md`
  - `docs/exec-plans/completed/handoff/HANDOFF-2026-04-11-006-RESCUE-DETERMINISTIC-OVERLAY.md`
  - `docs/exec-plans/completed/handoff/HANDOFF-2026-04-11-007-EXACT-DB-ITEM-LANE.md`
  - `docs/exec-plans/completed/handoff/HANDOFF-2026-04-11-008-CLARIFY-REQUIRED-LANE.md`
  - `docs/exec-plans/completed/handoff/HANDOFF-2026-04-11-009-CANNOT-ESTIMATE-LANE.md`
- `tests_run[]`:
  - `powershell -ExecutionPolicy Bypass -File scripts/check_protected_doc_rewrites.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_task_checkin_and_handoff.ps1 -AuditRepo`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
- `reality_drift_notes`:
  - `active/tasks` and `handoff/active` had accumulated completed artifacts and required archival cleanup
  - protected-doc deletion blocking already existed, but near-total same-path rewrites were still unguarded
- `source_of_truth_updated`: `yes`
- `followup_task_ids[]`:
  - none
- `handoff_doc_path`: `none`
