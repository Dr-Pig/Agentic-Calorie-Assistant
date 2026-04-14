# Handoff Contract

## Purpose

This document defines an **optional exception-path handoff**.

Routine local execution should not require a handoff document. Default execution truth remains:

1. `git diff / commit history`
2. CI and harness output
3. the minimal active state in [CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

## When A Handoff Is Worth Writing

Write a handoff only when at least one of these is true:

- work is transferring to another person or another agent context
- work will pause long enough that a fresh reader needs a restart brief
- a high-risk rollout or migration needs an explicit operational warning record
- the user explicitly asks for a written handoff

## When Not To Write One

Do not create a handoff just because:

- a small bounded slice completed
- tests ran successfully
- git already makes the change boundary obvious
- the current execution plan already captures the next action

## Minimum Handoff Content

If a handoff is intentionally created, it should answer only the restart-critical questions:

- where the work stopped
- what materially changed
- what remains blocked or risky
- what should happen next
- which assumptions are unsafe to revive

Suggested fields:

- `handoff_id`
- `task_id` or equivalent work reference
- `current_status`
- `what_changed`
- `blockers[]`
- `tests_run[]`
- `next_recommended_action`
- `unsafe_assumptions_to_avoid`

## Relationship To Other Execution Records

- use git for the primary change record
- use harness output for verification truth
- use [CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md) for the active execution board
- use this handoff contract only when an explicit transfer record is actually needed

## Locations

- optional active handoffs: `docs/exec-plans/active/handoff/`
- historical completed handoffs: `docs/exec-plans/completed/handoff/`
- stable operator references: `docs/exec-plans/reference/handoff/`

These locations stay available, but active handoff is not part of the default read path for routine local execution.
