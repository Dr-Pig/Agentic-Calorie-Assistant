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
| [`docs/handoff/active/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/active) | current operational handoff | yes, operationally | resuming or transferring work |
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

## Where To Find What

| Need | Primary Owner Doc |
| --- | --- |
| workflow order truth | [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md) |
| current build target | [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md) |
| slice ownership | [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md) |
| repo build rules | [docs/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/BUILD_FILE_PLACEMENT_RULES.md), [docs/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/LAYER_DEPENDENCY_RULES.md), [docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md) |
| task execution state | [docs/exec-plans/active/tasks/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/tasks) |
| runtime handoff | [docs/handoff/active/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/active) |
| eval / benchmark | [docs/quality/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality) |
| references or research notes | [docs/references/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references) |

## Canonical Specs

Core product and runtime specs live in [`docs/specs/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs).

Read in this order:

1. [L0 Product Capability Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md)
2. [L1 Runtime Ownership Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md)
3. [L2 Data State Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)
4. [L2A Data Dictionary Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2A_DATA_DICTIONARY_SPEC.md)
5. L3 runtime specs under [`docs/specs/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs)
The most implementation-critical supplements are:
- [L3T Typed Runtime Contract Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md)
- [L3M Guardrail Math Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3M_GUARDRAIL_MATH_SPEC.md)
Read these with `L6E`: `L3T` constrains output shape after decision mode is chosen, while `L3M` defines deterministic math that must not be re-delegated to LLM truth decisions.
6. [L6E LLM Pass Design Policy Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md)
This is the canonical cross-domain pass-design governance spec. Read this before using `L6C` role mapping or assuming any domain defaults to 4-pass.
7. L4 memory / retrieval / context specs under [`docs/specs/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs)
8. L6 framework / build / routing specs under [`docs/specs/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs)
9. [Workflow Dependency & Context Ordering Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
This is the canonical workflow order and execution prioritization authority. Execution plans must conform to it.

Canonical supporting specs:

- [LLM Ownership Rule](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/LLM_OWNERSHIP_RULE.md)
- [L6E LLM Pass Design Policy Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md)
- [Nutrition Output Contract](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/nutrition_output_contract.md)
- [Deterministic Macro Derivation Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/deterministic_macro_derivation_spec.md)
- [Macro Reconciliation Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/macro_reconciliation_spec.md)
- [L6D Repo Tech Stack / Code Style Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6D_REPO_TECH_STACK_CODE_STYLE_SPEC.md)

## Quality

Quality and evaluation docs live in [`docs/quality/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality).

Primary canonical quality docs:

- [L5A Eval Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5A_EVAL_SPEC.md)
- [L5B Benchmark Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5B_BENCHMARK_SPEC.md)
- [L5C Safety Guardrail Spec](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md)

Benchmark supporting docs:

- [Benchmark Case Schema](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/BENCHMARK_CASE_SCHEMA.md)
- [Benchmark Folder Layout](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/BENCHMARK_FOLDER_LAYOUT.md)
- [Stateful Multi-Turn Case Template](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md)
- [Runtime Experiment Checklist](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/RUNTIME_EXPERIMENT_CHECKLIST.md)

## Active Execution

Current execution docs live in [`docs/exec-plans/active/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active).

Read these when doing current implementation work:

- [Workflow Slice Registry](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [Harness Engineering Reorg v2](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/HARNESS_ENGINEERING_REORG_V2.md)
- [Sprint 2026-04 Contract Assimilation / Intake Correction](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/SPRINT-2026-04-CONTRACT-ASSIMILATION-INTAKE-CORRECTION.md)
- [Master Build Map](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/MASTER_BUILD_MAP.md)
- [Current Execution Plan](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)
- [Re-plan Log](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md)

Do not treat [`docs/exec-plans/completed/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/completed) as active truth.

## Governance

Governance docs define how the repo is operated. They are authoritative for process, not product behavior.

- [Harness Go / No-Go](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/HARNESS_GO_NO_GO.md)
- [Freeze-Growth Extraction Map](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/FREEZE_GROWTH_EXTRACTION_MAP.md)
- [Agent Loading Path](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_LOADING_PATH.md)
- [Execution Loop Brief](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/EXECUTION_LOOP_BRIEF.md)
- [Re-plan Trigger Brief](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/REPLAN_TRIGGER_BRIEF.md)
- [Autonomy Boundary Brief](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AUTONOMY_BOUNDARY_BRIEF.md)
- [Agent Role Execution Model](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_ROLE_EXECUTION_MODEL.md)
- [Codex Desktop Operator Guide](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/CODEX_DESKTOP_OPERATOR_GUIDE.md)
- [Encoding Policy](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/ENCODING_POLICY.md)
- [Spec Editing Protocol](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/SPEC_EDITING_PROTOCOL.md)
- [Implementation Planning & Re-plan Protocol](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)
- [Task Check-in Protocol](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md)
- [Handoff Contract](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/HANDOFF_CONTRACT.md)
- [Workspace Layout](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/WORKSPACE_LAYOUT.md)
- [Data Source Policy](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/DATA_SOURCE_POLICY.md)
- [Context Memory Architecture](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/context_memory_architecture.md)

## References

Research notes and external-reference-derived files live in [`docs/references/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references).

They are useful context, but they are not canonical truth unless a canonical spec points to them explicitly.

The desktop runtime reference library at `C:\Users\User\Desktop\agent runtime` is also an approved reference source for:

- framework selection
- orchestration patterns
- memory / retrieval patterns
- provider and failover patterns

It is reference-only and must never outrank canonical repo docs.

## Handoff

Current operational handoff lives in [`docs/handoff/active/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/active).

Use [`docs/handoff/completed/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff/completed) for historical handoff only.

Root-level files under [`docs/handoff/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/handoff) are stable operator reference docs, not the default active handoff queue.

## Archive

Historical, superseded, or quarantined material lives in [`docs/archive/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/archive).

Archive material should not be used as default truth.

## Snapshots

[`docs/_spec_snapshots/`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/_spec_snapshots) is for preservation and forensic comparison only.

Do not include snapshot directories in the default reading path for new work.

See:

- [Canonical Docs Manifest](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/generated/CANONICAL_DOCS_MANIFEST.md)
- [Archive Manifest](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/generated/ARCHIVE_MANIFEST.md)
- [Doc Classification Registry](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/generated/DOC_CLASSIFICATION_REGISTRY.md)
