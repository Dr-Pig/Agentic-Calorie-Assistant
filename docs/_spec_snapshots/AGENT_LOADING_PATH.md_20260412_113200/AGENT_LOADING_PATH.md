# Agent Loading Path

This file defines the repository's progressive-loading path for agents.

Use it after entering through [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md).

## Layer 0: Must Read Now

Read these first for any task:

1. [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md)
2. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

These two documents answer:

- what the active execution truth trio is
- which documents count as present truth

Load these next if the task needs workflow-order or slice-registry detail:

3. [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
4. [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)

These four documents together answer:

- what the canonical workflow order is
- what slice exists
- what the current build wave is
- which documents count as present truth

## Layer 1: Read By Task Type

Read the matching set before implementation:

| Task Type | Read Next |
| --- | --- |
| spec or architecture change | [docs/specs/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs), [docs/SPEC_EDITING_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/SPEC_EDITING_PROTOCOL.md), [docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md) |
| feature implementation | [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md), the relevant code area, and the harness docs in [docs/quality/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality) |
| handoff or resume work | latest file under [docs/handoff/active/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/active), then [docs/HANDOFF_CONTRACT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/HANDOFF_CONTRACT.md); use only for explicit handoff or long-interruption recovery |
| repo governance or file placement | [docs/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/BUILD_FILE_PLACEMENT_RULES.md), [docs/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/LAYER_DEPENDENCY_RULES.md), [docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md) |
| eval or benchmark work | [docs/quality/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality) |

## Layer 2: Conditional Reads

Read only if the task requires them:

- [docs/exec-plans/active/MASTER_BUILD_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/MASTER_BUILD_MAP.md) for phase sequencing
- [docs/exec-plans/active/REPLAN_LOG.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md) for recent reality drift
- [docs/HARNESS_GO_NO_GO.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/HARNESS_GO_NO_GO.md) before starting a new build wave
- [docs/PLANNER_AUTONOMY_LOOP_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_AUTONOMY_LOOP_POLICY.md) before enabling planner-led autonomous continuation
- [docs/EXECUTION_OPTIMAL_BUILD_ORDER_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/EXECUTION_OPTIMAL_BUILD_ORDER_POLICY.md) before choosing among multiple legal next slices or reopening cross-domain sequencing questions
- [docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md) before deciding whether a newly formalized slice should stay planner-local or be dispatched to a worker
- [docs/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md) only when a task artifact is intentionally being used
- [docs/FREEZE_GROWTH_EXTRACTION_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/FREEZE_GROWTH_EXTRACTION_MAP.md) if touching a freeze-growth file

## Do Not Treat As Default Truth

These locations are not part of the default reading path:

- [docs/references/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references)
- [docs/archive/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/archive)
- [docs/_spec_snapshots/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/_spec_snapshots)

Use them only for:

- external context
- historical comparison
- forensic diff or preservation checks
