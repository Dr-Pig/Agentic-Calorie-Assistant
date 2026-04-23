# Docs Index

This is the human-facing docs portal.

Use [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md) for agent bootstrap. This index only explains the docs families, their truth level, and where to look for a topic.

## Start Here

If you need the shortest path to current execution truth:

1. [V2 Implementation Plan](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/APP_V2_IMPLEMENTATION_PLAN.md)
2. [V2 Eval Bundle 1 Cases](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/V2_EVAL_BUNDLE_1_CASES.md)
3. [V2 Eval Bundle 2 Cases](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/V2_EVAL_BUNDLE_2_CASES.md)

## Docs Families

| Docs Family | Role | Default Truth? | Read When |
| --- | --- | --- | --- |
| [`docs/specs/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs) | canonical product, runtime, and architecture truth | yes | changing behavior, contracts, or legality |
| [`docs/exec-plans/active/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active) | active planner state, current slice, and execution sequencing | yes | implementing or selecting current work |
| [`docs/governance/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance) | repo operation, guardrails, and editing discipline | conditional | only when the task touches repo process or governance rules |
| [`docs/quality/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality) | eval, benchmark, safety, and harness policy | yes for quality work | eval, benchmark, or harness work |
| [`docs/exec-plans/active/handoff/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/handoff) | current exception-path handoff | no | explicit handoff or long interruption recovery |
| [`docs/references/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references) | supporting notes and non-canonical context | no | topic-specific supporting context |
| [`docs/archive/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/archive) | historical or superseded docs | no | historical comparison only |
| [`artifacts/docs-snapshots/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/artifacts/docs-snapshots) | preservation snapshots | no | forensic compare only |

## Where To Find What

| Need | Primary Location |
| --- | --- |
| what is active now | [docs/specs/APP_V2_IMPLEMENTATION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/APP_V2_IMPLEMENTATION_PLAN.md) |
| V2 bundle status (eval gates) | [docs/quality/V2_EVAL_BUNDLE_1_CASES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/V2_EVAL_BUNDLE_1_CASES.md), [V2_EVAL_BUNDLE_2_CASES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/V2_EVAL_BUNDLE_2_CASES.md) |
| V2 target architecture, single manager, domain-first design | [docs/specs/app_v2_ideal_architecture_final.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/app_v2_ideal_architecture_final.md) |
| V2 implementation packages, repo gap map, schema migration | [docs/specs/APP_V2_IMPLEMENTATION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/APP_V2_IMPLEMENTATION_PLAN.md) |
| onboarding budget/bootstrap happy path and shared `/today`/`/body-plan` truth | [docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md) |
| body observation, weight update, exercise input workflow | [docs/specs/L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md) |
| proactive scheduler, trigger conditions, suppression, nudge design | [docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md) |
| suite inventory, authority tiers, benchmark migration mapping | [docs/quality/L5D_SUITE_GOVERNANCE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5D_SUITE_GOVERNANCE_SPEC.md) |
| forbidden patterns, slop log, definition of done | [docs/governance/ANTI_SLOP_CATALOG.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/ANTI_SLOP_CATALOG.md) |
| repo build rules | [docs/governance/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance) |
| handoff exception path | [docs/exec-plans/active/handoff/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/handoff) |
| quality / eval / benchmark | [docs/quality/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality) |
| UX journey to slice mapping, human gates, founder test scenarios | [docs/quality/UX_JOURNEY_TO_SLICE_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/UX_JOURNEY_TO_SLICE_MAP.md) |
| reference material | [docs/references/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references) |

## Notes

- V2 uses **eval-first** execution model — execution progress is tracked via eval bundle gates, not slice-based planning.
- `docs/specs/APP_V2_IMPLEMENTATION_PLAN.md` is the execution blueprint.
- `docs/quality/V2_EVAL_BUNDLE_X_CASES.md` are the completion gates — each bundle must pass E2E eval before moving to the next.
- `docs/governance/` is not part of the default bootstrap path unless the task touches repo process.
- `docs/archive/` and `artifacts/docs-snapshots/` are important preservation layers, but they are not default reading paths.
