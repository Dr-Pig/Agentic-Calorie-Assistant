# Re-plan Trigger Brief

## Purpose

This brief defines the minimum conditions under which an agent must stop extending the current implementation path and re-plan.

It exists to prevent stale-plan execution, file bloat, and silent architecture drift.

## Mandatory Re-plan Triggers

Re-plan before continuing if any of the following becomes true:

- the current task needs to touch files outside `planned_touch_files[]` in a non-trivial way
- a file boundary is clearly wrong and continuing would make an already-fat file fatter
- the actual workflow dependency order appears different from the current assumption
- the work requires changing a typed runtime contract, canonical enum, or deterministic math rule
- the work requires introducing a new canonical concept that is not already covered by the relevant truth docs
- the next step depends on a source-of-truth clarification that does not yet exist
- a transitional legacy path is about to regain de facto truth ownership
- the task is blocked and another worker will need to resume with incomplete context

## High-Risk File Pressure Triggers

Stop and re-plan if a task would add another unrelated concern into files such as:

- `app/usecases/text_meal.py`
- `app/schemas.py`
- any other file already acting as both orchestration surface and boundary-crossing sink

The default corrective action is:

- extract boundary-safe logic first
- then continue feature work

## Required Re-plan Actions

When a trigger fires:

1. stop broadening the current implementation
2. update the active task artifact
3. record the reality drift in [`docs/exec-plans/active/REPLAN_LOG.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md) if the drift affects the plan
4. update source-of-truth docs first if canonical understanding changed
5. only then reopen or replace the task

## What Does Not Automatically Require Re-plan

These do not require re-plan by themselves:

- small helper extraction inside the checked-in boundary
- test additions that do not alter the task scope
- implementation details that remain inside the approved slice and touch scope

## Related Documents

- [docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)
- [docs/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md)
- [docs/exec-plans/active/REPLAN_LOG.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md)
