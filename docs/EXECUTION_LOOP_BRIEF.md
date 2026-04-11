# Execution Loop Brief

## Purpose

This brief defines the minimum execution loop a new agent should follow after entering the repository.

It does not define product truth or workflow order on its own. It compresses the existing operating model into a short runbook.

## Read Order For A New Agent

Read in this order:

1. [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
2. [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md)
3. [docs/AGENT_LOADING_PATH.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_LOADING_PATH.md)
4. [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
5. [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
6. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)
7. the relevant checked-in task artifact under `docs/exec-plans/active/tasks/`
8. if needed, the latest relevant handoff under `docs/handoff/active/`

## Execution Loop

### 1. Establish the current unit of work

- identify the active `slice_id`
- identify the active `task_id`
- confirm the task's `source_of_truth_refs[]`
- confirm the task's `planned_touch_files[]` and `forbidden_files[]`

Do not start broad implementation work without these.

### 2. Confirm the work is actually allowed now

- check that the slice is not ahead of the canonical workflow order
- check that the slice is present in the current execution plan
- check that the work does not require a higher-order architecture change

If any of these fail, stop and re-plan.

### 3. Implement only inside the checked-in boundary

- prefer the smallest write scope that satisfies the task
- do not absorb unrelated concerns into already-fat files
- if the real write scope differs materially from the checked-in task, update the task artifact first

### 4. Verify before claiming progress

- run the tests listed in the task artifact
- record what was actually touched
- record reality drift if assumptions expired

### 5. Close the loop

Before handoff or completion:

- update the task artifact
- update [`docs/exec-plans/active/REPLAN_LOG.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md) if reality drift occurred
- create or update a handoff doc if another worker must resume
- update source-of-truth docs if the work changed canonical understanding

### 6. Respect autonomy loop boundaries

- if [docs/PLANNER_AUTONOMY_LOOP_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_AUTONOMY_LOOP_POLICY.md) is active, the planner may continue into the next bounded task
- stop immediately when a mandatory human gate is reached
- do not continue autonomous execution past two bounded tasks without an explicit re-evaluation

## What This Brief Is Not

- not a replacement for the workflow ordering spec
- not a replacement for the task check-in protocol
- not a replacement for the handoff contract
- not a new source of product truth
