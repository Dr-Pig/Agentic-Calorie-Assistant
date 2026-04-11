# Planner Autonomy Loop Policy

## Purpose

This document defines the repository's `Planner-Led Soft Loop v1`.

It does not define product truth, workflow order, or task scope. It defines what the planner may run autonomously inside the current canonical truth and when the planner must stop and wait for human input.

## Default Loop Mode

The default operating mode is:

- `planner-led in app`
- bounded `Worker` delegation
- shared `Reviewer`
- validator-driven closeout
- `Product Gates` as the default human stop condition
- bounded worker or reviewer execution may run through `codex exec` while planner context remains in the desktop thread

This is a soft loop, not a fully unattended build pipeline.

## Multi-Round Planner Loop

The repository's default planner loop is multi-round, not single-round.

This means:

- the planner may complete one bounded task, review it, close it out or re-plan it, and then continue into the next bounded task
- the planner does not need a fresh user message between every bounded task
- the planner should continue until a mandatory human gate, failed check, or explicit re-plan boundary is reached

This multi-round loop may run across:

- a desktop planner thread
- one or more bounded worker or reviewer threads
- `codex exec` bounded-worker runs
- planner-local rounds where the planner does the slice directly without opening a worker

The planner remains the owner of stop/continue decisions across all of these execution surfaces.

## What The Planner May Run Autonomously

The planner may autonomously:

- choose the next bounded `task_id` within the current execution plan
- open bounded `Worker` tasks
- open a shared `Reviewer` for bounded task review
- run governance checks:
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
  - task / handoff completeness checks
- run relevant targeted, smoke, and integration tests
- re-plan inside the current canonical product truth
- close completed tasks and archive handoff artifacts
- continue into the next bounded task if no human gate has been reached
- continue across multiple bounded tasks in sequence when the current bounded wave remains valid and no human gate has been reached
- choose between `planner-local` and `worker-worthy` rounds using [docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md)

Worker and reviewer runs may report changed files, tests run, risks, and review findings, but they do not decide stop conditions, human gates, or whether the loop continues. Those decisions belong to the planner/runner.

## Mandatory Human Gates

The planner must stop and wait for the user when any of the following becomes true:

- a new UI or surface is ready for manual review
- product wording, semantics, or interaction behavior need human judgment
- founder-fit benchmark seeds, real examples, or manual test input are required
- canonical workflow order, product truth, or guardrail truth would need to change
- work is entering an explicit LLM behavior evaluation stage and product meaning is uncertain
- the next task would move beyond the current bounded wave in the execution plan

## Loop Boundaries

- The planner must not auto-change canonical specs without user involvement.
- The planner must not cross a re-plan trigger by silently broadening task scope.
- The planner must not use the loop to bypass file-placement, layer, freeze-growth, or protected-file rules.
- The planner must not continue past a failed governance or test check.

## Per-Loop Requirements

Every bounded task completed inside the loop must produce:

- an updated task artifact
- recorded `actual_touch_files[]`
- recorded `tests_run[]`
- a handoff or completion record

Every loop cycle must leave the repository in a state where:

- governance checks pass
- relevant tests pass
- active vs completed task state is accurate
- source-of-truth sync is preserved

## Consecutive Autonomy Limit

The default autonomy limit is:

- at most `2` consecutively completed bounded tasks

After two bounded tasks, the planner must explicitly re-evaluate:

- whether a human gate has been reached
- whether the current wave is still the right one
- whether context drift or product ambiguity is increasing

This re-evaluation may result in continuing autonomously if no human gate exists.

This is a re-evaluation point, not an automatic stop point. If the bounded wave is still valid and no human gate has been reached, the planner may continue into the next round.

## Relationship To Other Docs

- bootstrap and loading order still start at [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md) and [docs/AGENT_LOADING_PATH.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_LOADING_PATH.md)
- task execution rules still live in [docs/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md)
- stop conditions still live in [docs/REPLAN_TRIGGER_BRIEF.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/REPLAN_TRIGGER_BRIEF.md)
- role ownership still lives in [docs/AGENT_ROLE_EXECUTION_MODEL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_ROLE_EXECUTION_MODEL.md)
- operator usage still lives in [docs/CODEX_DESKTOP_OPERATOR_GUIDE.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/CODEX_DESKTOP_OPERATOR_GUIDE.md)
