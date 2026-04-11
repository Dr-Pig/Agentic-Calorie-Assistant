# Codex Desktop Operator Guide

## Purpose

This guide explains how to operate the repository's execution model inside Codex desktop.

It is written for the human operator, not as a new product spec.

## Recommended Thread Model

Use:

- one persistent `planner` thread
- one `worker` thread per active `task_id`
- one `reviewer` thread when independent review is needed

Do not use one long-lived thread for planner, implementation, and review at the same time.

## Official Execution Modes

This repository now treats the following as official operating modes:

- `Desktop Planner Mode`
  - keep the long-lived planner context in the Codex desktop thread
- `Codex Exec Bounded-Worker Mode`
  - use CLI-backed bounded `Worker` or `Reviewer` runs when the planner wants narrower execution context or when desktop round-trips would otherwise stall the loop

The default recommendation is:

- planner stays in desktop
- bounded workers and reviewers may run through CLI
- canonical truth and execution artifacts still live in repo docs, not inside CLI prompts
- default execution-surface bias is `planner-local`; worker use is selective, not automatic

## What To Read Before Starting A Thread

For any new thread:

1. [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
2. [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md)

For planner threads:

- [docs/AGENT_ROLE_EXECUTION_MODEL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_ROLE_EXECUTION_MODEL.md)
- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

For worker threads:

- [docs/EXECUTION_LOOP_BRIEF.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/EXECUTION_LOOP_BRIEF.md)
- the assigned task artifact
- the latest relevant handoff

For reviewer threads:

- [docs/AGENT_ROLE_EXECUTION_MODEL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_ROLE_EXECUTION_MODEL.md)
- the assigned task artifact
- the latest relevant handoff
- the touched files and source-of-truth refs

## Practical Judgment: When To Use Built-In Sub-Agents

The primary value of a sub-agent is **not** that it is smarter, but that it has a **cleaner, narrower context**, free from the historical burden of the entire repository planning lifecycle.

Use Codex desktop delegation or sub-agent features exclusively for bounded work:

- **Bounded Implementation**: A single checked-in `task_id` where the exact files to modify are known.
- **Isolated Audits**: Reading files to report on adherence to a spec.
- **Independent Reviews**: Passing a diff to a sub-agent to strictly check against guardrails.

**Do NOT use delegation for:**
- Undefined scope exploration or architecture decisions.
- Tasks without a checked-in `task_id`.
- Planner-owned execution-state decisions such as choosing the next slice or changing workflow order.

Process closeouts are not globally forbidden for sub-agents. If a closeout gap is already known and narrowly scoped, a worker may handle it as a bounded patch. The planner still owns the final convergence decision.

## Operator Preference In This Repository

Current operator preference:

- if the planner judges that bounded delegation would reduce context drift or avoid unnecessary planner-context growth, the planner should propose delegation by default
- if planner-local execution reaches the same result with lower cost and similar clarity, planner-local should be preferred
- for bounded worker tasks, the default operator posture is `yes` unless the planner identifies a concrete risk
- planner-owned architecture decisions, workflow ordering changes, and high-risk convergence steps still stay in the planner thread
- planner-led autonomous continuation is allowed inside the bounds defined by [docs/PLANNER_AUTONOMY_LOOP_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_AUTONOMY_LOOP_POLICY.md)
- detailed surface-selection judgment lives in [docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md)

## When To Open A Separate Thread Manually

Open a separate thread when:

- you want a dedicated planner thread
- the task needs a clean role boundary
- the UI delegation flow is unclear
- you want to isolate a reviewer from the worker context

Manual threads are an acceptable fallback when built-in sub-agent behavior is unclear or too loose for the task.

## When To Prefer Codex Exec Bounded-Worker Mode

Prefer `codex exec` bounded-worker mode when:

- the planner already has a checked-in `task_id`
- the worker scope is narrow and file-bounded
- you want the planner context to stay clean in desktop
- you want the task to run through the repo validator loop instead of waiting for the next desktop message turn

Do not prefer it when:

- the work is still exploratory
- the planner has not yet converged on the correct task scope
- the next step is primarily a product decision or manual-review gate

Operationally, this means:

- desktop thread = planner/control surface
- `codex exec` = bounded worker or reviewer runtime
- repo scripts/tests = validator layer

## Suggested First Prompt Shapes

Planner thread:

```text
Role: Lead Planner
Read AGENTS.md, docs/index.md, workflow ordering spec, slice registry, and current execution plan first.
Goal: choose the next active task, keep execution aligned, and update task or handoff artifacts when needed.
```

Worker thread:

```text
Role: Worker
Task: TASK-...
Slice: ...
Read the assigned task artifact and latest relevant handoff first.
Only work within planned_touch_files unless a re-plan trigger is hit.
```

Reviewer thread:

```text
Role: Reviewer
Review task TASK-...
Read the task artifact, latest handoff, touched files, and source_of_truth_refs first.
Prioritize boundary drift, contract mismatch, guardrail math mismatch, and missing tests.
Do not expand scope into new implementation work.
```

## The Standard Rhythmic Cycle (Minimal Operating Loop)

A healthy execution rhythm prevents cognitive drift. Follow this loop strictly:

1. **[Planner] Initiation**: Use the main planner thread to analyze the execution plan, pick the next `task_id`, and define the bounded context.
2. **[Sub-Agent] Execution**: Dispatch a delegated sub-agent (Worker) to implement the specific `task_id`. Let it complete and return the result.
3. **[Sub-Agent/Reviewer] Audit (If required)**: Dispatch a separate reviewer sub-agent if the code touches core domains/math.
4. **[Planner] Convergence & Closeout**: Return to the main planner thread to absorb the result. The planner decides whether to:
   - close the task directly
   - dispatch a tiny closeout worker
   - dispatch a reviewer
   - re-plan because reality drift occurred

## Multi-Round Continuation Rule

The default operating assumption is not "one worker round per user message."

Instead:

- if a bounded task closes cleanly
- and no mandatory human gate was reached
- and the next best-next slice is already clear from the current execution plan

then the planner may immediately start the next bounded worker round without waiting for another user message.

Use this rule to preserve planner momentum across multiple windows:

- planner thread keeps the durable execution context
- worker or reviewer windows stay disposable and task-bounded
- each completed round returns to the planner for the next stop/continue decision

Stop only when:

- a human gate is reached
- a canonical truth decision is needed
- the bounded wave is no longer clear
- checks or reviews fail and require re-plan

## Shared Reviewer Pattern

Use one shared reviewer across multiple workers when possible.

- The reviewer does not need to be dedicated one-to-one with a worker.
- Review one completed `task_id` at a time.
- Use the reviewer after worker completion, not in parallel on half-finished scope.

## Hard Operator Rules

- do not start implementation without a checked-in `task_id`
- do not let a worker decide workflow order
- do not let the reviewer become the implementer for the same task without opening a new task
- do not rely on chat history alone when task, handoff, or truth docs are stale
- if the planner is running in soft-loop mode, stop when a mandatory human gate is hit instead of auto-crossing it

## Related Docs

- [docs/AGENT_ROLE_EXECUTION_MODEL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_ROLE_EXECUTION_MODEL.md)
- [docs/PLANNER_AUTONOMY_LOOP_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_AUTONOMY_LOOP_POLICY.md)
- [docs/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md)
- [docs/HANDOFF_CONTRACT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/HANDOFF_CONTRACT.md)
- [docs/EXECUTION_LOOP_BRIEF.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/EXECUTION_LOOP_BRIEF.md)
- [docs/REPLAN_TRIGGER_BRIEF.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/REPLAN_TRIGGER_BRIEF.md)
- [docs/AUTONOMY_BOUNDARY_BRIEF.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AUTONOMY_BOUNDARY_BRIEF.md)
