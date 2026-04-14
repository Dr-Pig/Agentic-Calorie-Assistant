# Active Task Artifacts

This directory is reserved for checked-in active task artifacts governed by:

- [docs/governance/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/TASK_CHECKIN_PROTOCOL.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)

Each task artifact should identify:

- `task_id`
- `slice_id`
- `source_of_truth_refs[]`
- planned write scope
- completion criteria
- tests to run

Task artifacts are an optional exception path.

Routine local execution should default to:

- `AGENTS.md`
- `docs/index.md`
- `docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md`
- `git diff` and harness output

Use a checked-in task artifact only when delegation, long interruption recovery, or explicit written scope control is valuable.
