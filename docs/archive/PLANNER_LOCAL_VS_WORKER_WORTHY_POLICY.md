# Planner-Local vs Worker-Worthy Selection Policy

## Purpose

This document defines the repository's execution-surface selection rule.

It answers a narrower question than workflow ordering or planner autonomy:

- when a slice is already legal and task-formalized, should it run as `planner-local` or `worker-worthy`

This document extends, but does not replace:

- [docs/governance/EXECUTION_OPERATING_MODEL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/EXECUTION_OPERATING_MODEL.md)
- [docs/governance/EXECUTION_SELECTION_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/EXECUTION_SELECTION_POLICY.md)
- [docs/governance/EXECUTION_SELECTION_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/EXECUTION_SELECTION_POLICY.md)

It does not define:

- workflow ordering truth
- product truth or runtime truth
- slice legality
- task check-in format
- human-gate policy

Those remain owned by their existing documents.

## Default Bias

The repository default is:

- `planner-local`

Do not escalate a slice into worker mode just because multi-agent execution appears more sophisticated.

If one planner thread can complete the slice cleanly inside an already clear scope, prefer `planner-local`.

## Execution Surface Types

### `planner-local`

- the planner completes the slice directly in the main thread
- no worker is opened
- reviewer remains optional and selective

### `worker-worthy`

- the planner first formalizes the task
- the planner then dispatches a bounded worker
- a shared reviewer may be added if the task risk justifies it

## Principle Alignment

This policy follows five repository-level principles:

1. use the simplest viable execution surface first
2. plan before implementation and define boundaries before dispatch
3. keep execution rules in repo docs, not only in chat memory
4. use multi-agent execution only for high-noise, high-coupling, or high-risk implementation
5. rely on verifiable feedback, not intuition alone

## Decision Precedence

Apply these rules in order:

1. if the slice is planning-heavy, truth-sync-heavy, re-plan-heavy, or closeout-heavy, choose `planner-local`
2. if the slice is regression-only, docs-only, or governance-only, choose `planner-local`
3. if scope is not yet clear enough to enumerate touched files, stay `planner-local` until scope convergence is complete
4. only after the first three checks pass, evaluate whether the slice is `worker-worthy`

## Hard Questions

Before opening a worker, the planner should answer:

1. is this already a formalized bounded slice
2. will this round produce substantial noisy exploration or implementation churn
3. would keeping that churn in the planner thread materially pollute long-lived planning context
4. is the write scope already explicit, narrow, and enumerable
5. can the worker return in a standard format
6. is this primarily implementation work, rather than planning, truth sync, closeout, or re-plan

If these questions cannot be answered clearly, keep the work `planner-local`.

## Worker-Worthy Conditions

A slice is `worker-worthy` only when most of the following are true:

- a checked-in `task_id` already exists
- `planned_touch_files[]` is explicit
- the work is primarily production implementation
- the implementation is expected to generate significant exploration, trial-and-error, or noisy local context
- that noise would reduce later planner quality if kept in the planner thread
- the worker output can be standardized as:
  - changed files
  - tests run
  - known risks
  - re-plan trigger or none

Worker value is context isolation, not ceremony for its own sake.

## Planner-Local Default Categories

The following should default to `planner-local`:

- next-slice selection
- execution plan updates
- task formalization
- truth or spec sync
- re-plan log updates
- handoff or closeout patching
- governance cleanup
- regression-only follow-through
- small test hardening without production-code changes
- human-gate decisions
- convergence on worker or reviewer outputs
- planner stop/continue decisions inside the loop

## Relationship To Review

This policy does not require a reviewer for every slice.

Use a shared reviewer selectively when:

- the task touches core canonical or persistence boundaries
- the task alters guardrail math
- the task has meaningful scope-creep risk
- the planner should not self-approve a non-trivial implementation change

## Required Planner Recording

When a new slice is formalized, the planner should record one of:

- `execution_surface: planner-local`
- `execution_surface: worker-worthy`

and a short `selection_reason`.

This may live in:

- the task artifact
- or [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

The intent is that another planner, worker, or reviewer can understand why the chosen execution surface was selected without relying on chat history.

## Worked Classification Examples

- `TASK-2026-04-12-025-CURRENT-BUDGET-READMODEL-DATE-FOLLOWTHROUGH`
  - `planner-local`
  - reason: regression-only, no production patch, closeout-heavy
- `2.2a-active-meal-continuation`
  - `planner-local` if the slice is proving behavior through regression rather than implementing new production changes
- `2.2c-cross-midnight-attribution`
  - `worker-worthy`
  - reason: bounded implementation, production patch, clear write scope
- `2.6b` and `2.6c` calibration foundation
  - may be `worker-worthy` at the implementation level
  - but still remain constrained by build-order policy
- truth-sync slices
  - always `planner-local`

## Quota-Aware Rule

This policy is not anti-worker.

It formalizes a quota-aware rule:

- prefer `planner-local` when it reaches the same outcome with lower execution cost
- use `worker-worthy` when the context-isolation benefit is real
- do not turn every implementation task into a worker by default
- do not turn every worker completion into an automatic reviewer requirement
