# Handoff Contract

## Purpose

This document defines the minimum structure required for future handoff notes in `docs/handoff/`.

Entry and loading context:

- [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md) is the only root agent bootstrap
- [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md) identifies active vs historical handoff locations
- [docs/AGENT_LOADING_PATH.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_LOADING_PATH.md) tells resume workers when to read active handoff

It does not replace individual handoff documents. It constrains them so that a new agent can resume work without relying on long chat history.

## Recommended Handoff Locations

Preferred structure:

- active handoffs: `docs/handoff/active/`
- completed handoffs: `docs/handoff/completed/`

If the repository keeps a flat `docs/handoff/` layout for now, each new handoff file should still follow this contract.

## Minimum Handoff Fields

Each handoff document should define at least:

- `handoff_id`
- `task_id`
- `slice_id`
- `current_status`
- `what_changed`
- `what_did_not_change`
- `files_touched[]`
- `blockers[]`
- `tests_run[]`
- `source_of_truth_docs_touched[]`
- `reality_drift`
- `next_recommended_action`
- `unsafe_assumptions_to_avoid`

## Hard Rules

- Handoff notes must not be free-form narrative only.
- A handoff must make it possible for a new agent to answer:
  - where the work stopped
  - what changed
  - what is still blocked
  - what files are safe or unsafe to touch next
  - which assumptions already expired
- If a task changed canonical understanding, the handoff must point to the canonical docs that were updated.

## Pre-commit Soft Gate

- [`scripts/check_task_checkin_and_handoff.ps1`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/check_task_checkin_and_handoff.ps1) checks staged handoff docs in `warn` mode by default.
- Missing required sections are treated as warnings now, not hard blockers.
- This keeps friction low while the operating layer is still being adopted.

## Relationship To Other Execution Documents

- `Workflow Slice Registry` defines what unit of work exists
- `Task Check-in Protocol` defines how a task is checked in and completed
- this handoff contract defines how the current state of a task/slice is transferred to the next worker

Completed-task handoffs should move to `docs/handoff/completed/` once their paired task artifact is archived out of `active/`.

## Suggested Handoff Structure

Recommended sections:

1. Handoff identity
2. Task and slice identity
3. Current state
4. Files and tests
5. Drift and expired assumptions
6. Recommended next step

This contract defines the minimum information, not a single mandatory prose template.
