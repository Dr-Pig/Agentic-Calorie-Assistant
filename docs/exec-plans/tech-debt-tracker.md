# Execution Tech Debt Tracker

This file tracks repo and harness debt that is not part of the active execution state machine.

## Current Debt

- refresh any remaining live references that still point at retired `docs/handoff/` paths
- refresh any remaining live references that still point at retired `docs/_spec_snapshots/` paths
- keep root-directory purification aligned with `docs/governance/BUILD_FILE_PLACEMENT_RULES.md`
- keep task and handoff artifacts clearly exception-only, not primary execution truth

## Usage Rule

- do not store active branch state here
- do not use this file as a substitute for `CURRENT_EXECUTION_PLAN.md`
- move resolved items out rather than accumulating indefinite history
