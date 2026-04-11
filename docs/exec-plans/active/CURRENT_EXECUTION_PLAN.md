# Current Execution Plan

> [!WARNING]
> **Authority Limit**: this file is the minimal active execution board only.
> It does not replace canonical workflow order, slice legality, or product/runtime truth.
> For those, use:
> - [WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
> - [WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)

## Purpose

This file keeps only the minimum active execution state needed to answer:

- what the current goal is
- what slice is active now
- what verification is required
- what happens next
- whether a human decision is currently blocking progress

Detailed historical drift belongs in [REPLAN_LOG.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md), completed tasks, completed handoffs, and git history.

## Execution Truth Trio

Default execution truth comes from:

1. `git diff / commit history`
2. CI and harness output
3. this minimal active execution board

Task artifacts and handoff docs are optional exception tools. They are not required for routine local execution.

## Active Execution State

- `goal`: keep the product main flow stable while waiting for the next bounded slice to be formalized
- `current_slice`: `none`
- `status`: `planner formalization required`
- `owner_mode`: `local`
- `key_files_or_subsystem`: `2.2-2.3 main flow follow-through is closed; no new bounded write scope is active yet`
- `required_harness`:
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`
  - relevant targeted, smoke, integration, or eval commands for the actual slice
- `verification_status`: `pending next slice`
- `verification_reason`: `there is no active bounded slice to verify yet; the next slice must define its own required harness set`
- `next_action`: `formalize the next bounded slice before more implementation continues`
- `human_decision_needed`: `none currently`

## Current Product / Workflow Focus

- `current_workflow_focus`: `2.3 Today UI / Read Models`
- `critical_path_note`: `today-surface follow-through is closed; planner re-evaluation is required before the next bounded slice`
- `non_blocking_parallel_note`: `2.4 Weight / Body Observation remains required before 2.6 Calibration, but it does not block the current mainline until a new bounded slice is formalized`

## Immediate Selection State

- `legal_next_set`: `none formalized`
- `selected_best_next_slice`: `none`
- `selection_reason`: `all currently formalized bounded slices in the active wave are complete; continuing without a new bounded slice would widen scope beyond the current execution board`
- `last_replan_at`: `2026-04-12`

## Working Rules

- keep this file minimal; do not duplicate touched files, full drift narratives, or handoff prose here
- if a task completes without a commit, the working tree or staged diff must still make the write boundary legible
- if required harness has not run, keep `verification_status` explicit instead of implying completion
- if a real handoff is needed, use [docs/HANDOFF_CONTRACT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/HANDOFF_CONTRACT.md) as an exception path
- use [docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md) only when delegation is actually being considered

## Pointer Map

- active sequencing support: [MASTER_BUILD_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/MASTER_BUILD_MAP.md)
- recent planning drift and corrections: [REPLAN_LOG.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md)
- completed task history: [docs/exec-plans/completed/tasks/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/completed/tasks)
- completed handoff history: [docs/handoff/completed/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/completed)
