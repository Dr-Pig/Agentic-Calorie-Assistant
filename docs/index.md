# Docs Index

This is the human-facing docs portal.

Use [AGENTS.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/AGENTS.md) for agent bootstrap. This index only explains the docs families, their truth level, and where to look for a topic.

## Start Here

If you need the shortest path to current execution truth:

1. [V2 Documentation Index](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/V2_DOC_INDEX.md)
2. [V2 Wave 1 Coding Agent Bootstrap](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md)
3. [V2 Execution Architecture and Wave Plan](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md)

## Docs Families

| Docs Family | Role | Default Truth? | Read When |
| --- | --- | --- | --- |
| [`docs/specs/`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs) | canonical product, runtime, and architecture truth | yes | changing behavior, contracts, or legality |
| [`docs/governance/`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance) | repo operation, guardrails, and editing discipline | conditional | only when the task touches repo process or governance rules |
| [`docs/quality/`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality) | eval, benchmark, safety, and harness policy | yes for quality work | eval, benchmark, or harness work |
| [`docs/agent/`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent) | bounded autonomy and EvoMap operating guidance | conditional | planner/evaluator workflow or reusable-lesson work |
| [`docs/provider/`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider) | provider contracts and capability evidence | conditional | transport, structured output, or model selection work |
| [`docs/archive/`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/archive) | historical or superseded docs | no | historical comparison only |
| [`artifacts/docs-snapshots/`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/docs-snapshots) | preservation snapshots | no | forensic compare only |

## Where To Find What

| Need | Primary Location |
| --- | --- |
| what is active now | [docs/V2_DOC_INDEX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/V2_DOC_INDEX.md) |
| Wave 1 build order and bootstrap | [docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md) |
| V2 bundle status (acceptance gates, not build order) | [docs/quality/V2_EVAL_BUNDLE_1_CASES.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/V2_EVAL_BUNDLE_1_CASES.md), [V2_EVAL_BUNDLE_2_CASES.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/V2_EVAL_BUNDLE_2_CASES.md) |
| V2 target architecture, single manager, domain-first design | [docs/specs/app_v2_ideal_architecture_final.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/app_v2_ideal_architecture_final.md) |
| Wave 1 implementation closure and contracts | [docs/specs/V2_WAVE_1_DEEP_CAPABILITY_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_WAVE_1_DEEP_CAPABILITY_SPEC.md), [V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md) |
| onboarding budget/bootstrap happy path and shared `/today`/`/body-plan` truth | [docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md) |
| body observation, weight update, exercise input workflow | [docs/specs/L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md) |
| proactive scheduler, trigger conditions, suppression, nudge design | [docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md) |
| repo build rules and guardrails | [docs/governance/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance) |
| quality / eval / benchmark | [docs/quality/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality) |
| UX journey to slice mapping, human gates, founder test scenarios | [docs/quality/UX_JOURNEY_TO_SLICE_MAP.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/UX_JOURNEY_TO_SLICE_MAP.md) |
| bounded autonomy workflow, planner/evaluator/worker, stop gates | [docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md) |
| Wave 1 Phase B-2 product-intelligence architecture draft | [docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md) |
| Wave 1 Phase B-2 P0 execution plan | [docs/specs/WAVE_1_PHASE_B2_P0_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_P0_EXECUTION_PLAN.md) |
| Wave 1 Phase B-2 alignment audit | [docs/specs/WAVE_1_PHASE_B2_ALIGNMENT_AUDIT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_ALIGNMENT_AUDIT.md) |
| Wave 1 architecture transition ladder | [docs/specs/WAVE_1_ARCHITECTURE_TRANSITION_LADDER.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_ARCHITECTURE_TRANSITION_LADDER.md) |
| historical reference material | [docs/archive/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/archive) |

## Notes

- V2 Wave 1 starts from the bootstrap and execution-architecture docs, not from bundle order.
- `docs/specs/APP_V2_IMPLEMENTATION_PLAN.md` is a legacy/historical implementation plan unless reconciled.
- `docs/quality/V2_EVAL_BUNDLE_X_CASES.md` are acceptance/regression reference, not build order.
- `docs/governance/` is not part of the default bootstrap path unless the task touches repo process.
- `docs/archive/` and `artifacts/docs-snapshots/` are important preservation layers, but they are not default reading paths.
