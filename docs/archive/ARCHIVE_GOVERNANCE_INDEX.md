# Archive Governance Index

## Purpose

This index defines the boundary between:

- current V2 / Wave 1 truth
- governance tooling that stays in the main repo
- historical archive material that must not drive active implementation

## Current Truth

The following remain mainline truth:

- `docs/specs/` files that are still aligned with current V2 / Wave 1 ownership
- `docs/quality/` files that define current evaluation, grading, and regression governance
- governance tooling docs that describe current repo operating policy

Current-truth docs may guide implementation, runtime ownership, or governance checks.

## Governance Tooling

The following stay in the main repo as governance tooling, not product-runtime truth:

- `docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md`
- `docs/agent/autonomy-prompts/`
- `docs/agent/autonomy-schemas/`
- dry-run / bounded-autonomy operator guidance that supports repo execution discipline

These documents may control planner/evaluator/worker workflow or bounded autonomy behavior, but they are not user-facing product capability specs.

## Historical Archive

Archive content includes:

- pre-V2 build order and implementation plans
- superseded runtime taxonomies
- old autonomy or execution workflow briefs that no longer define current governance
- pre-V2 rescue, recommendation, and memory product semantics
- references, research, and completed artifacts that preserve history but must not be treated as active truth

Archive content may be useful for context recovery, but it must not be used as a default implementation entrypoint.

## App Code Alignment

The repo uses `Archive Hard` for future-wave or pre-V2 app families that are intentionally excluded from Wave 1 mainline ownership:

- `app/archive/rescue/`
- `app/archive/recommendation/`
- `app/archive/memory/`

These code families are preserved for history, tests, or targeted governance tooling only. Active mainline app packages must not import them.

## Practical Rule

Use mainline docs when the content still governs:

- current Wave 1 behavior
- current architecture ownership
- current guardrail or governance tooling

Use archive docs only when you are:

- tracing historical decisions
- reconciling old artifacts
- recovering context for later-wave reimplementation

If a document is not aligned with current V2 / Wave 1 truth, it should live under `docs/archive/`.
