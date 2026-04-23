# TASK-2026-04-12-028-DOCS-BOOTSTRAP-STATE-MACHINE-REORG

## Status

- `COMPLETED`

## Goal

Restructure the docs entry layer around a planner state machine so bootstrap reads are short, active execution truth is obvious, and non-default governance/reference material is removed from the default path.

## Allowed Touch Areas

- `AGENTS.md`
- `docs/index.md`
- `docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md`
- `docs/governance/**`
- `docs/archive/**`
- `docs/references/**`
- `docs/generated/**`
- docs governance scripts and CI references needed for moved owner docs

## Forbidden Touch Areas

- canonical spec content under `docs/specs/**` except link updates
- product/runtime code under `app/**`
- active/completed handoff semantics

## New Files Expected

- `docs/governance/EXECUTION_OPERATING_MODEL.md`
- `docs/governance/EXECUTION_SELECTION_POLICY.md`
- `docs/governance/CHANGE_CONTROL_GUARDS.md`

## Completion Record

- `completed_at`: `2026-04-12 13:09:18 +08:00`
- `actual_touch_files[]`:
  - `AGENTS.md`
  - `docs/index.md`
  - `docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md`
  - `docs/governance/EXECUTION_OPERATING_MODEL.md`
  - `docs/governance/EXECUTION_SELECTION_POLICY.md`
  - `docs/governance/CHANGE_CONTROL_GUARDS.md`
  - `docs/governance/BUILD_FILE_PLACEMENT_RULES.md`
  - `docs/governance/ENCODING_POLICY.md`
  - `docs/governance/SPEC_EDITING_PROTOCOL.md`
  - `docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md`
  - `docs/governance/TASK_CHECKIN_PROTOCOL.md`
  - `docs/governance/HANDOFF_CONTRACT.md`
  - `docs/governance/LAYER_DEPENDENCY_RULES.md`
  - `docs/governance/GITHUB_REPO_GOVERNANCE.md`
  - `docs/governance/DATA_SOURCE_POLICY.md`
  - `docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md`
  - `docs/references/context_memory_architecture.md`
  - `docs/archive/AGENT_LOADING_PATH.md`
  - `docs/archive/MASTER_BUILD_MAP.md`
  - `scripts/check_protected_doc_rewrites.ps1`
  - `scripts/block_delete_recreate_specs.ps1`
- `tests_run[]`:
  - `powershell -ExecutionPolicy Bypass -File scripts/check_task_checkin_and_handoff.ps1 -AuditRepo`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`
- `reality_drift_notes`:
  - `AGENT_LOADING_PATH.md` was retired from the default bootstrap path and archived.
  - `CURRENT_EXECUTION_PLAN.md` now acts as the planner dashboard / execution clock.
  - repo-level governance owner docs were moved under `docs/governance/`.
  - root `docs/` now retains only `index.md`.