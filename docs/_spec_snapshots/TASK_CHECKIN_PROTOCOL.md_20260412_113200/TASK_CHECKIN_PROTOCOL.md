# Task Check-in Protocol

## Purpose

This protocol now defines an **optional** task-artifact path.

It no longer governs the default day-to-day execution record. The repository's default execution record is:

1. `git diff / commit history`
2. CI and harness output
3. the minimal active state in [CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

Use a task artifact only when the task shape benefits from a separate written record.

## Default Rule

For routine local execution:

- do not create a task artifact by default
- do not block implementation on handwritten `actual_touch_files[]` or `tests_run[]`
- prefer proving completion through git plus harness

## Git Recording Discipline

Because git is now a primary execution record:

- commit only after a bounded slice is verifiable
- commit messages should name the slice intent, not just a vague mechanical action
- if a round is intentionally left uncommitted, the staged diff or working tree diff should still make the write boundary legible

## When To Use A Task Artifact

Create or update a task artifact only when at least one of these is true:

- work is being transferred across people or sessions
- a bounded slice needs an explicit written scope boundary before delegation
- a high-risk migration or rollout needs a separate operational record
- the user explicitly asks for task-level written tracking

## Minimum Optional Task Fields

If a task artifact is intentionally used, keep it lean. The minimum recommended fields are:

- `task_id`
- `slice_id`
- `status`
- `goal`
- `owner`
- `source_of_truth_refs[]`
- `planned_touch_files[]` when the write scope is known
- `required_harness[]`
- `next_action`

## Completion Rule

If a task artifact is used and marked complete, it should summarize only the minimum extra value not already obvious from git and harness:

- completion time or closeout date
- the verification commands that actually ran
- any expired assumption or execution drift that materially changes the next step
- whether follow-up work remains

Do not treat a task artifact as the primary place to re-list every touched file or duplicate commit history.

## Relationship To Harness

The check-in concept remains valid, but it is now harness-first:

1. run the required harness
2. inspect the resulting diff and verification outcome
3. update [CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md) only if the active execution state changed
4. write a task artifact only if the task meets the exception criteria above

## Script Status

- [`scripts/check_task_checkin_and_handoff.ps1`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/check_task_checkin_and_handoff.ps1) is now an advisory compatibility audit
- it no longer acts as the default blocking governance gate in CI or pre-commit
- use it only when intentionally validating legacy task/handoff artifacts

## Artifact Locations

- optional active tasks: `docs/exec-plans/active/tasks/`
- historical completed tasks: `docs/exec-plans/completed/tasks/`

These locations remain available for explicit task tracking, but they are no longer part of the default read path for routine implementation.
