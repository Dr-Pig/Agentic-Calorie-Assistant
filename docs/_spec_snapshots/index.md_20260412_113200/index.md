# Docs Index

This is the human-facing docs map.

Use [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md) for agent bootstrap.
Use [docs/AGENT_LOADING_PATH.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_LOADING_PATH.md) for progressive agent loading.

## Truth Levels

| Docs Family | Role | Default Truth? | Read When |
| --- | --- | --- | --- |
| [`docs/specs/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs) | canonical product, runtime, and architecture specs | yes | changing behavior, contracts, or architecture |
| [`docs/exec-plans/active/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active) | current execution state and active build sequencing | yes | implementing current work |
| [`docs/exec-plans/completed/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/completed) | completed execution artifacts | no | historical lookup only |
| [`docs/handoff/active/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/active) | optional operational handoff | no, exception path only | cross-person transfer, long interruption, or explicit handoff request |
| [`docs/quality/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality) | eval, benchmark, and safety docs | yes for quality | eval or benchmark work |
| [`docs/references/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references) | external or research-derived notes | no | supporting context only |
| [`docs/archive/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/archive) | historical or superseded material | no | historical comparison only |
| [`docs/_spec_snapshots/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/_spec_snapshots) | preservation snapshots | no | forensic compare or spec editing only |

## Start Here

If you need the shortest path to current truth:

1. [Workflow Dependency & Context Ordering Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
2. [Workflow Slice Registry](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
3. [Current Execution Plan](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)
4. [Agent Loading Path](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_LOADING_PATH.md)

## Execution Truth Trio

Default execution truth is intentionally lightweight:

1. `git diff / commit history`
2. CI and harness output
3. the minimal active state in [Current Execution Plan](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

Task check-ins and handoff docs are no longer part of the default execution path. Use them only when the task shape requires an explicit transfer record.

## Where To Find What

| Need | Primary Owner Doc |
| --- | --- |
| workflow order truth | [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md) |
| execution-optimal next-slice selection | [docs/EXECUTION_OPTIMAL_BUILD_ORDER_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/EXECUTION_OPTIMAL_BUILD_ORDER_POLICY.md) |
| planner-local vs worker-worthy selection | [docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md) |
| current build target | [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md) |
| slice ownership | [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md) |
| repo build rules | [docs/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/BUILD_FILE_PLACEMENT_RULES.md), [docs/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/LAYER_DEPENDENCY_RULES.md), [docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md) |
| optional task artifact reference | [docs/exec-plans/active/tasks/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/tasks) |
| optional runtime handoff | [docs/handoff/active/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/active) |
| eval / benchmark | [docs/quality/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality) |
| references or research notes | [docs/references/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references) |

## Canonical Specs

Canonical product, runtime, and architecture truth lives in [`docs/specs/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs).

Use this short path unless your task requires deeper spec reads:

1. [L0 Product Capability Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md)
2. [L1 Runtime Ownership Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md)
3. [L2 Data State Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)
4. [L6E LLM Pass Design Policy Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md)
5. [Workflow Dependency & Context Ordering Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)

For detailed spec discovery, use:

- [`docs/specs/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs)
- [Canonical Docs Manifest](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/generated/CANONICAL_DOCS_MANIFEST.md)

## Quality

Quality, eval, and benchmark docs live in [`docs/quality/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality).

Start with:

- [L5A Eval Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5A_EVAL_SPEC.md)
- [L5B Benchmark Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5B_BENCHMARK_SPEC.md)
- [L5C Safety Guardrail Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md)

## Active Execution

Current execution docs live in [`docs/exec-plans/active/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active).

Default execution path:

- [Workflow Slice Registry](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [Master Build Map](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/MASTER_BUILD_MAP.md)
- [Current Execution Plan](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)
- [Re-plan Log](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md)

Do not treat [`docs/exec-plans/completed/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/completed) as active truth.

## Governance

Governance docs define repo process, not product behavior.

Primary owner docs:

- [Encoding Policy](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/ENCODING_POLICY.md)
- use [`scripts/normalize_encoding.ps1`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/normalize_encoding.ps1) for explicit repair when policy-scope markdown drifts
- [Spec Editing Protocol](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/SPEC_EDITING_PROTOCOL.md)
- [Implementation Planning & Re-plan Protocol](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)
- [Planner Autonomy Loop Policy](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_AUTONOMY_LOOP_POLICY.md)
- [Execution Optimal Build Order Policy](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/EXECUTION_OPTIMAL_BUILD_ORDER_POLICY.md)
- [Planner-Local vs Worker-Worthy Selection Policy](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md)
- [Build File Placement Rules](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/BUILD_FILE_PLACEMENT_RULES.md)
- [Layer Dependency Rules](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/LAYER_DEPENDENCY_RULES.md)

Optional governance references:

- [Task Check-in Protocol](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md)
- [Handoff Contract](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/HANDOFF_CONTRACT.md)
- [Agent Role Execution Model](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_ROLE_EXECUTION_MODEL.md)

Supporting governance briefs and maps remain under [`docs/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs).

The BOM hard gate applies to `docs/**/*.md` and `AGENTS.md`; it is not a repo-wide rule for all source files or all markdown.

## References

Research notes and external-reference-derived files live in [`docs/references/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references).

They are useful context, but they are not canonical truth unless a canonical spec points to them explicitly.

## Handoff

Current operational handoff lives in [`docs/handoff/active/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/active).

It is an exception path, not a default read requirement for routine local execution.

Use [`docs/handoff/completed/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/completed) for historical handoff only.

Root-level files under [`docs/handoff/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff) are stable operator reference docs, not the default active handoff queue.

Stable handoff reference docs now live under [`docs/handoff/reference/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/reference).

## Archive

Historical, superseded, or quarantined material lives in [`docs/archive/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/archive).

Archive material should not be used as default truth.

## Snapshots

[`docs/_spec_snapshots/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/_spec_snapshots) is for preservation and forensic comparison only.

Do not include snapshot directories in the default reading path for new work.

For manifests and classification, use:

- [Canonical Docs Manifest](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/generated/CANONICAL_DOCS_MANIFEST.md)
- [Archive Manifest](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/generated/ARCHIVE_MANIFEST.md)
- [Doc Classification Registry](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/generated/DOC_CLASSIFICATION_REGISTRY.md)
