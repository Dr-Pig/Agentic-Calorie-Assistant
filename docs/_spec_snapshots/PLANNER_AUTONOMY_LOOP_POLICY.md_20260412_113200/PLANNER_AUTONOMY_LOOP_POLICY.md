# Planner Autonomy Loop Policy

## Purpose

This document defines the repository's default autonomy posture.

It governs how work should continue inside the current canonical truth. It does not define product truth, workflow order, or slice legality.

## Default Loop Mode

The default operating mode is:

- `single-stream local planner`
- harness-driven verification
- delegation only when the task shape justifies it
- human stop conditions at product or truth boundaries

This repository no longer treats multi-agent circulation as the default loop shape.

## What The Planner May Do By Default

The planner may autonomously:

- choose the next bounded slice within the current execution plan
- implement the slice directly in the main thread
- run governance and harness checks
- run targeted, smoke, integration, or eval commands relevant to the slice
- re-evaluate whether another bounded slice should continue
- update the minimal active execution state in [CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

## Delegation Rule

`planner-local` is the default.

Open a worker only when the slice is clearly bounded and the context-isolation value is real. Use [PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md) only when delegation is actively being considered.

Reviewer use is selective, not automatic.

## Mandatory Human Gates

The planner must stop and wait for the user when:

- a new UI or surface is ready for manual review
- product wording, semantics, or interaction behavior need human judgment
- canonical workflow order, product truth, or guardrail truth would need to change
- founder-fit examples, benchmark seeds, or manual test input are required
- the next move would widen scope beyond the current bounded wave

## Loop Boundaries

- do not auto-change canonical specs without user involvement
- do not silently widen scope across a re-plan boundary
- do not bypass file-placement, layer, freeze-growth, or protected-file rules
- do not continue past a failed blocking harness

## Per-Round Completion Standard

Every round should leave the repo with:

- a legible diff or commit boundary
- relevant harness results
- an accurate minimal active execution state

Task artifacts and handoff notes are optional exception tools, not default per-round requirements.

## Relationship To Other Docs

- bootstrap starts at [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md) and [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md)
- active execution state lives in [CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)
- optional task artifact rules live in [TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md)
- optional handoff rules live in [HANDOFF_CONTRACT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/HANDOFF_CONTRACT.md)
- stop conditions still live in [REPLAN_TRIGGER_BRIEF.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/REPLAN_TRIGGER_BRIEF.md)
