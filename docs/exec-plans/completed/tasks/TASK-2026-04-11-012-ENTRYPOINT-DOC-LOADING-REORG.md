# Task Artifact

- `task_id`: `TASK-2026-04-11-012-ENTRYPOINT-DOC-LOADING-REORG`
- `slice_id`: `repo-doc-loading-entrypoint-reorg`
- `status`: `COMPLETED`
- `owner`: `codex-local`
- `started_at`: `2026-04-11`

## Source Of Truth Refs

- [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
- [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md)
- [docs/SPEC_EDITING_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/SPEC_EDITING_PROTOCOL.md)
- [docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)

## Goal

Collapse root documentation bootstrap into a single agent entrypoint and make docs loading progressively navigable without moving the main docs families.

## Planned Touch Files

- `AGENTS.md`
- `docs/index.md`
- `docs/AGENT_LOADING_PATH.md`
- governance and operator docs that still pointed to `agent.md`
- `scripts/block_delete_recreate_specs.ps1`
- `docs/exec-plans/active/REPLAN_LOG.md`

## Forbidden Files

- `docs/specs/*` content rewrites unrelated to cross-link alignment
- `docs/quality/*`
- broad path renames under `docs/specs/`, `docs/exec-plans/`, `docs/handoff/`, `docs/archive/`

## Completion Criteria

- `AGENTS.md` is the only root agent bootstrap
- `agent.md` no longer participates in the default loading path
- `docs/index.md` clearly distinguishes canonical, active, reference, archive, and snapshot families
- a dedicated progressive loading doc exists
- non-archive active docs no longer rely on `agent.md` links

## Tests To Run

- targeted link/reference grep for `agent.md` under the active docs path
- manual read-path verification from `AGENTS.md` to workflow order, current execution plan, task protocol, and handoff contract

## Expected Re-plan Impact

Should lower entry confusion for future agents and reduce duplicate bootstrap guidance across root and docs governance files.

## Completion Record

- `completed_at`: `2026-04-11`
- `actual_touch_files[]`:
  - `AGENTS.md`
  - `docs/index.md`
  - `docs/AGENT_LOADING_PATH.md`
  - `docs/EXECUTION_LOOP_BRIEF.md`
  - `docs/SPEC_EDITING_PROTOCOL.md`
  - `docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md`
  - `docs/TASK_CHECKIN_PROTOCOL.md`
  - `docs/HANDOFF_CONTRACT.md`
  - `docs/AGENT_ROLE_EXECUTION_MODEL.md`
  - `docs/AUTONOMY_BOUNDARY_BRIEF.md`
  - `docs/CODEX_DESKTOP_OPERATOR_GUIDE.md`
  - `docs/ENCODING_POLICY.md`
  - `docs/exec-plans/active/HARNESS_ENGINEERING_REORG_V2.md`
  - `docs/generated/CANONICAL_DOCS_MANIFEST.md`
  - `docs/generated/DOC_CLASSIFICATION_REGISTRY.md`
  - `docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`
  - `scripts/block_delete_recreate_specs.ps1`
  - `.editorconfig`
  - `docs/exec-plans/active/tasks/TASK-2026-04-11-012-ENTRYPOINT-DOC-LOADING-REORG.md`
  - `docs/exec-plans/active/REPLAN_LOG.md`
- `tests_run[]`:
  - `Get-ChildItem AGENTS.md,docs,scripts,.editorconfig -Recurse -File | Select-String -Pattern 'agent\\.md'`
  - `manual read-path verification from AGENTS.md into docs/index.md, docs/AGENT_LOADING_PATH.md, workflow ordering spec, slice registry, current execution plan`
- `reality_drift_notes`:
  - `agent.md` was removed intentionally to eliminate dual-entry ambiguity; delete/rename blocker was expanded so AGENTS.md and loading-path docs cannot be casually deleted or renamed later`
- `source_of_truth_updated`:
  - `yes`
- `followup_task_ids[]`:
  - `[]`
- `handoff_doc_path`:
  - `none`
