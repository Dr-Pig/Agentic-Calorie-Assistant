# Agent Role Execution Model

## Purpose

This document defines the minimum multi-agent role model for this repository.

It does not define product truth or workflow order. It defines who does what once a task is active.

## Role Set

The repository uses three working roles:

- `Lead Planner`
- `Worker`
- `Reviewer`

Do not invent new execution roles unless the canonical operating docs are updated first.

## Why We Split Roles

If one continuous agent thread acts as planner, worker, and reviewer, three failure modes become much more likely:

1. context from old tasks pollutes the current slice
2. planning and implementation boundaries blur
3. self-review becomes weak and scope drift is easier to miss

Role splitting exists to give workers and reviewers narrower context, not to force every action through a separate agent.

## Execution Surfaces

This repository supports two official execution surfaces:

- `desktop planner mode`
  - the long-lived planner context stays in the Codex desktop thread
- `codex exec bounded-worker mode`
  - bounded `Worker` and `Reviewer` runs may be dispatched through [scripts/run_planner_loop_v1.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/run_planner_loop_v1.py) and [scripts/run_codex_exec_with_prompt.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/run_codex_exec_with_prompt.py)

Default intent:

- keep planning context in desktop
- push bounded implementation and review into CLI worker or reviewer runs when that reduces planner-context pollution

## Delegation Rules: Planner vs Sub-Agent

### When the Planner should do it directly
- Selecting the next `slice_id` and `task_id`
- Re-planning or altering the execution plan
- Making high-risk architecture boundary decisions
- Updating execution-control artifacts when the work changes overall plan state
- Small process closeouts when opening another worker would add more ceremony than value

The planner must proactively suggest delegation when a bounded task would materially reduce context drift or safely enable parallel progress. The planner should not wait for the operator to invent delegation first.
Delegation judgment is owned by [docs/governance/EXECUTION_SELECTION_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/EXECUTION_SELECTION_POLICY.md), not by worker convenience alone.

### When to hand it to a Sub-Agent (Worker)
- A bounded, explicitly defined implementation within a `task_id`
- The scope and target files are explicitly clear
- A specific bug fix that does not require re-architecting
- A small closeout-only patch if the gap is narrow and already known
- A `codex exec` bounded-worker run driven by the planner loop runner when desktop thread continuation would otherwise stall autonomous progress

If these conditions are met, the planner should normally recommend opening a worker instead of silently absorbing the task into the planner thread.

### When to hand it to a Sub-Agent (Reviewer)
- A clean, isolated review of one bounded task
- Boundary checking after a worker finishes
- Contract, math, or test-sufficiency review when planner should not self-approve

### When a Reviewer is strongly preferred
- When a task touches core canonical domain or persistence boundaries
- When a task alters safety guardrail math
- When the planner detects potential scope creep from a worker
- When a task is being marked complete after non-trivial code changes


## Lead Planner

Read first:

1. [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
2. [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md)
3. [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
4. [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
5. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

Primary responsibilities:

- choose the current active `slice_id` and `task_id`
- keep execution aligned with workflow ordering truth
- create or update task artifacts and handoff artifacts
- maintain [docs/exec-plans/active/REPLAN_LOG.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md) when reality drift occurs
- decide whether work stays in the current task or requires re-plan
- inside [docs/governance/EXECUTION_SELECTION_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/EXECUTION_SELECTION_POLICY.md), continue through bounded tasks until a human gate is reached
- own the multi-round loop across windows or execution surfaces; workers and reviewers may finish tasks, but only the planner decides whether the next round starts immediately

Must not:

- silently expand worker scope
- self-approve architecture truth changes without updating canonical docs
- let execution plans override canonical workflow order
- cross a mandatory human gate without stopping for the operator
- delegate the stop/continue decision to workers or reviewers

## Worker

Read first:

1. [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
2. [docs/governance/EXECUTION_OPERATING_MODEL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/EXECUTION_OPERATING_MODEL.md)
3. the assigned task artifact under `docs/exec-plans/active/tasks/`
4. the latest relevant handoff under `docs/handoff/active/`

Primary responsibilities:

- implement exactly one checked-in `task_id`
- stay within `planned_touch_files[]`
- run the task's listed tests
- update task artifacts with actual touched files and results
- surface reality drift instead of guessing through it
- report facts and risks; do not decide whether the planner should stop, continue, or open the next task

Must not:

- change workflow ordering on its own
- expand into another slice without re-plan
- redefine canonical contracts or math without updating truth docs
- act as the final reviewer of its own task

## Reviewer

Read first:

1. the assigned task artifact
2. the latest relevant handoff
3. the canonical refs listed in `source_of_truth_refs[]`
4. the touched files

Primary responsibilities:

- review for boundary drift
- review for contract mismatch
- review for guardrail math mismatch
- review for missing or weak tests
- verify source-of-truth sync when canonical understanding changed

Must not:

- silently broaden scope into new implementation work
- replace planner decisions about ordering or active slices
- approve work that changed canonical understanding without doc updates

## Default Operating Pattern

- one `Lead Planner`
- one shared `Reviewer`
- up to two or three `Worker`s, only when write scopes do not conflict

Parallel workers are allowed only when:

- they have different `task_id`s
- their write scopes do not materially overlap
- they are not both changing the same canonical contract boundary

The reviewer is shared across tasks. It does not need to be one reviewer per worker. Review should happen one task at a time.

## Relationship To Other Docs

- workflow order lives in [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- slice definitions live in [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- task rules live in [docs/governance/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/TASK_CHECKIN_PROTOCOL.md)
- handoff rules live in [docs/governance/HANDOFF_CONTRACT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/HANDOFF_CONTRACT.md)
- stop conditions live in [docs/governance/CHANGE_CONTROL_GUARDS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/CHANGE_CONTROL_GUARDS.md)
- autonomy limits live in [docs/governance/EXECUTION_OPERATING_MODEL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/EXECUTION_OPERATING_MODEL.md)
