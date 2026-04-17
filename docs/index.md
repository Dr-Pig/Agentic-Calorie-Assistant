# Docs Index

This is the human-facing docs portal.

Use [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md) for agent bootstrap. This index only explains the docs families, their truth level, and where to look for a topic.

## Start Here

If you need the shortest path to current execution truth:

1. [Current Execution Plan](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)
2. [Workflow Slice Registry](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
3. [Workflow Dependency & Context Ordering Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)

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
| what is active now | [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md) |
| what slices exist and who owns them | [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md) |
| what order is legal | [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md) |
| routing vs response boundary, anti-premature-taxonomy, eval label governance | [docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md) |
| suite inventory, authority tiers, benchmark migration mapping | [docs/quality/L5D_SUITE_GOVERNANCE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5D_SUITE_GOVERNANCE_SPEC.md) |
| LLM pass design, graph-first, decision-mode governance | [docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md) |
| forbidden patterns, slop log, definition of done | [docs/governance/ANTI_SLOP_CATALOG.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/ANTI_SLOP_CATALOG.md) |
| repo build rules | [docs/governance/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance) |
| handoff exception path | [docs/exec-plans/active/handoff/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/handoff) |
| quality / eval / benchmark | [docs/quality/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality) |
| reference material | [docs/references/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references) |

## Notes

- `docs/specs/` is still the canonical source of truth.
- `docs/exec-plans/active/` is the current execution reality.
- `docs/governance/` is not part of the default bootstrap path unless the task touches repo process.
- task and handoff artifacts stay exception-only under `docs/exec-plans/`.
- `docs/archive/` and `artifacts/docs-snapshots/` are important preservation layers, but they are not default reading paths.
