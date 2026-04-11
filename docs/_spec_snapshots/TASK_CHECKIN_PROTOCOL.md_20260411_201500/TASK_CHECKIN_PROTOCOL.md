# Task Check-in Protocol

## Purpose

This protocol defines the checked-in task artifact required before and after slice-level implementation work.

It is a repository-level governance and operational rule. It exists to make multi-agent and multi-engineer execution inspectable, auditable, and handoff-safe.

It is subordinate to:

- [`docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [`docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)

## Artifact Locations

- active tasks: `docs/exec-plans/active/tasks/`
- completed tasks: `docs/exec-plans/completed/tasks/`

If these directories do not yet exist, they should be created before broad multi-agent execution begins.

## Minimum Active Task Fields

Every active task artifact must include:

- `task_id`
- `slice_id`
- `status`
- `owner`
- `started_at`
- `source_of_truth_refs[]`
- `planned_touch_files[]`
- `forbidden_files[]`
- `goal`
- `completion_criteria[]`
- `tests_to_run[]`
- `expected_replan_impact`

## Minimum Completion Fields

Before a task may be marked complete, it must also include:

- `completed_at`
- `actual_touch_files[]`
- `tests_run[]`
- `reality_drift_notes`
- `source_of_truth_updated`
- `followup_task_ids[]`
- `handoff_doc_path`

## Hard Rules

- No slice-level implementation work should start without `task_id + slice_id + source_of_truth_refs`.
- No task may be marked complete without `tests_run + reality_drift_notes + source_of_truth_updated`.
- If the task changes capability ordering, dependency understanding, or architecture assumptions, canonical docs must be updated before completion.
- `planned_touch_files[]` and `forbidden_files[]` are mandatory because they reduce accidental overlap between simultaneous workers.

## Pre-commit Soft Gate

- [`scripts/check_task_checkin_and_handoff.ps1`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/check_task_checkin_and_handoff.ps1) runs in pre-commit `warn` mode by default.
- It currently warns when code changes are staged without corresponding checked-in task artifacts, or when task/handoff files miss required sections.
- This is intentionally a soft gate first. It may be upgraded to block mode later if the repo begins seeing repeated execution drift.

## Relationship To Re-plan

- Every completed task should be eligible to feed into [`docs/exec-plans/active/REPLAN_LOG.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md)
- If the task invalidates the current execution plan, re-plan must happen before the next task starts

## Suggested Task Artifact Shape

Recommended sections:

1. Header / task identity
2. Slice identity and source-of-truth refs
3. Planned write scope
4. Completion criteria
5. Tests to run
6. Completion record
7. Drift and follow-up

This protocol defines required fields, not a single markdown template.
