# Execution Optimal Build Order Policy

## Purpose

This document defines the repository's execution-selection policy.

It answers a narrower question than canonical workflow ordering:

- when more than one slice is legal, which slice is the best next slice to execute now

This document extends, but does not replace:

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)

It does not define:

- product truth
- runtime truth
- slice boundary ownership
- task check-in format
- planner autonomy rights

Those remain owned by their existing documents.

## Owner Mapping

- ordering legality: [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- slice boundary and forbidden touch areas: [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- re-plan mechanics: [docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)
- autonomy and human gates: [docs/PLANNER_AUTONOMY_LOOP_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_AUTONOMY_LOOP_POLICY.md)
- task closeout and tests-run recording: [docs/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md)

## Legal Next vs Best Next

`legal next slice` means a slice that:

- respects the canonical workflow ordering
- respects current dependency state
- respects the slice registry and current execution reality

`best next slice` means the slice, chosen from the current legal-next set, that best satisfies this execution policy.

Planner rules:

- do not advance a slice just because it is legal
- always identify the current legal-next set before selecting the next task
- record the selected best-next slice and a short selection reason in [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

## Principle Precedence

When execution principles conflict, apply them in this order:

1. `Strict deferment of later-domain foundation`
2. `State/contract lock before domain advance`
3. `Minimize rework`
4. `Incremental pass design within the active domain`

Interpretation:

- later-domain foundation is deferred by default unless it clearly qualifies for early work
- current-domain state and contract stability outrank rework convenience
- rework minimization only applies after the first two constraints are satisfied
- incremental pass design is a convergence rule inside the active domain, not a cross-domain prioritization rule

## Domain Advance Gate

A domain may advance into the next domain only when all of the following are true:

- the current domain's core state shape is stable enough for downstream use
- the current domain's core contract is stable enough for downstream use
- at least one real main-flow path is verifiable
- no unresolved governance blockers remain for the current domain
- verification depth is sufficient for domain advance

### Partial Pass Rule

- a partial pass is not a pass
- the planner may record a partial-pass state for later re-evaluation
- the planner must not lower the gate threshold without user approval

### Retreat Rule

If a downstream slice exposes that the prior domain was not actually stable enough:

- the planner may retreat to the earlier domain
- retreat is gate enforcement, not failure
- the retreat reason must be written into the re-plan log before further implementation continues

## Later-Domain Foundation Deferment Rule

This section extends execution selection on top of canonical ordering. It does not replace ordering legality.

A later-domain foundation slice may start early only if all of the following are true:

- it directly removes a blocker on the current critical-path segment
- doing it now materially reduces expected rework
- it will not convert provisional policy into code truth ahead of source-of-truth sync
- it will not consume the main execution bandwidth needed by the current domain
- its write scope is already bounded and does not expand context density across unrelated areas

If any of these conditions fail, the later-domain foundation remains legal but is not the best next slice.

## Critical Path Usage

The canonical source of workflow critical-path order remains:

- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)

This document does not restate the full capability order.

Instead, the planner must record in [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md):

- the current active segment of the critical path
- whether the selected best-next slice is on that segment or is an explicitly justified parallel prerequisite

Current standing interpretation:

- `2.4 Weight / Body Observation` does not block `2.2-2.5` mainline progress
- `2.4 Weight / Body Observation` does block entry into `2.6 Calibration`
- therefore `2.4` is neither ignorable nor the default best-next slice during `2.2-2.5`

## Verification Accumulation Policy

This section extends execution-level advance criteria on top of [docs/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TASK_CHECKIN_PROTOCOL.md). It does not replace task-local test requirements.

Rules:

- task artifacts still own slice-level required tests
- slice-local green checks are enough for slice completion only
- crossing a domain advance gate requires more than slice-local tests

Before advancing domains, the planner must confirm the existence of:

- domain-level integration evidence
- at least one verifiable main-flow scenario for the current domain
- any manual review or LLM-behavior check required by the current domain's semantics

Do not treat unit, regression, or governance checks alone as sufficient evidence for cross-domain advance.

## Multi-Agent Arbitration

This document provides selection rules. It does not grant final arbitration authority to non-user agents.

If multiple planners or analysis agents produce different best-next recommendations:

- record the competing choices
- explain the rule-level disagreement
- attempt to resolve the disagreement using this document's precedence rules
- if the disagreement still remains, escalate to the user

The user remains the final arbitrator of competing best-next recommendations.

## Required Planner Outputs

When selecting the next slice, the planner should leave behind:

- current legal-next set
- selected best-next slice
- active critical-path segment
- short selection reason
- any deferred legal slices that were intentionally not selected

These may be brief, but they must be explicit in the current execution plan or linked task artifact.
