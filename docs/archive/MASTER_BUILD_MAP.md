# Master Build Map

> [!WARNING]
> **Authority Downgraded**: This file is no longer the ultimate Source-of-Truth for capability ordering. It is purely a construction control artifact.
> The absolute truth for feature dependency and context insertion order is now governed by:
> **[`WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)**

## Purpose

This document is the long-range implementation map for the repository.

It defines:

- the ordered build phases
- the dependency chain between phases
- what each phase must produce before the next phase begins

It does not define far-future micro-tasks.

Detailed task breakdown belongs only in the current execution plan.

This map is subordinate to:

- [`docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)

Its role is to group adjacent workflows into manageable execution bundles without changing the canonical dependency order.

## Phase Order

### Bundle A. Intake Foundation

Goal:

- stabilize canonical persistence, typed contracts, trace foundations, and the foundations needed by single-turn and multi-turn intake

Must produce:

- canonical repository skeletons
- canonical write bridge
- typed intake commit path
- minimal trace envelope and trace write path
- the foundations needed by:
  - `2.1 Single-turn Intake`
  - `2.2 Multi-turn Intake + Correction`

Prerequisites for next phase:

- canonical meal write path works
- trace events can be emitted during intake runtime
- typed contracts are no longer optional add-ons

### Bundle B. Read Models and Body Observation

Goal:

- expose canonical truth through read models and add the second data source required by later calibration

Must produce:

- `2.3 Today UI / Read Models`
- `2.4 Weight / Body Observation UI + Persistence`

Prerequisites for next phase:

- read models reflect canonical truth
- body observation data is persisted and visible
- rescue can rely on stable ledger surfaces

### Bundle C. Rescue and Calibration

Goal:

- introduce budget correction and expenditure adjustment only after intake, today views, and body observation are stable

Must produce:

- `2.5 Rescue Mechanism`
- `2.6 Calibration Core`

Prerequisites for next phase:

- rescue and calibration write through canonical objects
- budget and body-plan truth are stable enough for memory-aware recommendation

### Bundle D. Memory and Recommendation

Goal:

- deepen context and then introduce memory-aware recommendation on top of stable state, rescue, and calibration

Must produce:

- `2.7 Memory / Retrieval Deepening`
- `2.8 Recommendation`

Prerequisites for next phase:

- recommendation is memory-aware and budget-aware
- proactive behavior can use stable recommendation, rescue, and calibration signals

### Bundle E. Proactive and Hardening

Goal:

- add proactive behavior only after the relevant reactive systems exist, while hardening quality and provider behavior

Must produce:

- `2.9 Proactive Nudges`
- runnable benchmark/eval loops
- provider fallback/failover that preserves runtime contracts

## Re-plan Checkpoints

Re-plan is mandatory:

- after each phase completion
- after a major boundary refactor
- after a typed contract change
- after a fat-file trigger

## Active Build Posture

Current active implementation is focused on:

- `2.1 Single-turn Intake`
- `2.2 Multi-turn Intake + Correction`

with supporting foundation work that exists only to unblock those workflows.
