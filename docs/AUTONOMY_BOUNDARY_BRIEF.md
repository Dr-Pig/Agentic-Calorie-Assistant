# Autonomy Boundary Brief

## Purpose

This brief defines what an agent may decide autonomously during checked-in implementation work, and what must be escalated, re-planned, or reflected back into source-of-truth docs before proceeding.

It exists to support long-running autonomous execution without letting local implementation choices silently rewrite product or architecture truth.

## Agent May Decide Autonomously

Inside the active task and approved slice boundary, an agent may:

- extract small helpers or services that reduce file bloat
- add or tighten tests inside the checked-in scope
- align implementation details to existing typed contracts and deterministic rules
- improve trace, logging, or read-helper structure without changing canonical truth
- update task artifacts, handoff docs, and re-plan notes

## Agent Must Not Decide Autonomously

An agent must not silently decide any of the following:

- change canonical workflow ordering
- move a later capability earlier in the execution sequence
- redefine a canonical enum, typed contract, or deterministic math rule without updating the source-of-truth docs
- introduce a new product-level UI surface or semantic behavior that changes product intent
- use an external reference to overrule canonical repo docs
- restore legacy transitional paths as de facto system truth
- delete-and-recreate canonical spec or architecture files

## Must Stop Or Escalate

Stop, re-plan, or wait for explicit approval if the work requires:

- a change to canonical workflow order
- a new architecture posture that changes framework, provider, or routing truth
- a product-level change to UI meaning, not just implementation shape
- a broad write scope outside the checked-in task boundary
- a structural rewrite of canonical docs

## Source-of-Truth Sync Rule

If the agent changes any canonical understanding, the corresponding truth docs must be updated before the work is treated as complete.

Code change without truth-sync is not considered a safe completion path.

## Related Documents

- [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- [docs/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md)
- [docs/HANDOFF_CONTRACT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/HANDOFF_CONTRACT.md)
- [docs/SPEC_EDITING_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/SPEC_EDITING_PROTOCOL.md)
