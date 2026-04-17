# Execution Operating Model

## Purpose

This document is the owner doc for execution governance.

It defines:

- how the planner should choose the next slice
- when planner-local work is acceptable
- when worker-worthy delegation is justified
- when human-gate or re-plan stops are mandatory
- how Codex desktop interaction should stay narrow and execution-oriented

This document extends, but does not replace:

- [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)
- [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
- [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)

This document is now the single owner for execution selection and execution surface rules. [docs/governance/EXECUTION_SELECTION_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/EXECUTION_SELECTION_POLICY.md) is a redirect only.

## Default Mode

- `planner-local` is the default
- keep high-impact semantic/architecture work in a single stream
- do not keep bounded non-semantic follow-through in a single stream by default when delegation has clear value
- use docs as retrieval targets, not preload targets
- prefer code and harness truth over narrative status writing

## Required Selection Path

When the planner is choosing the next slice, read in this order:

1. [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
2. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)
3. [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
4. [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
5. this document

Next-slice selection is not a conditional governance read.

## Next-Slice Selection

The planner must distinguish:

- `legal next`
- `best next`

Do not advance a slice just because it is legal.

Use this precedence:

1. canonical legality from the ordering spec
2. current global and local state from `CURRENT_EXECUTION_PLAN.md`
3. slice ownership and write-boundary truth from `WORKFLOW_SLICE_REGISTRY.md`
4. domain advance gate and human-gate state
5. harness readiness and write-boundary clarity

When multiple slices are legal, prefer the slice that best respects:

1. later-domain deferment by default
2. current-domain state and contract lock before domain advance
3. mainline validation before downstream foundation when both are legal
4. rework reduction only after the first three checks pass

Do not use "easiest to verify now" or "least likely to cross unresolved product semantics" as primary selection heuristics.

## Domain Advance Gate

A domain may advance only when all are true:

- the current domain's core state shape is stable enough for downstream use
- the current domain's core contract is stable enough for downstream use
- at least one real main-flow path is verifiable
- no unresolved governance blockers remain for the current domain
- verification depth is sufficient for domain advance

Partial pass is not pass.

If downstream work proves the prior domain was not actually stable enough:

- retreat to the earlier domain is allowed
- retreat is gate enforcement, not failure

## Human Gate Rule

If the best legal next slice is blocked by a human semantics gate:

- do not force a substitute slice just because it is cleaner or easier
- only redirect to another legal branch when the global build state in `CURRENT_EXECUTION_PLAN.md` explicitly identifies that branch as the current best-next path
- if no such branch is already justified, re-plan before continuing

High-impact human gates are limited to:

- global pass / architecture decisions
- new cross-workflow product semantics
- new `Utterance-Governed Suite` official canonical truth

Do not treat ordinary `Official Golden` follow-through, runner activation, registry work, fixture work, regression work, or other non-semantic execution as human-gated by default.

## Autonomy Boundary

The planner may continue local implementation when:

- the next slice is already legal
- the next slice is already selected as best-next in the execution dashboard
- no high-impact human semantics gate is active
- the write boundary is bounded enough to verify

The planner must stop or replan when:

- legal next and best next diverge but the dashboard has not yet recorded the redirect
- product semantics are unresolved
- the slice boundary is unclear
- the task would cross protected or freeze-growth boundaries without an explicit reason
- the harness no longer gives a clear pass or fail result

## Planner-Local vs Worker-Worthy

`planner-local` remains the default.

Keep work planner-local when:

- the slice is planning-heavy, truth-sync-heavy, re-plan-heavy, or closeout-heavy
- the slice is regression-only, docs-only, or governance-only
- the next action depends immediately on the result
- scope is not yet clear enough to enumerate touched files

Treat a slice as worker-worthy only when most are true:

- a bounded task already exists
- `planned_touch_files[]` is explicit
- the work is primarily production implementation
- the implementation will generate noisy exploration or local churn
- that churn would pollute planner quality if kept in the main thread
- the worker can return in a standard format

Worker value is context isolation, not ceremony.

### Worker-First Default For Non-Semantic Follow-Through

When a slice is already semantically settled and the remaining work is primarily:

- registry / fixture / runner extension
- migration mapping
- executable-pack derivation
- mechanical promotion
- regression / verification authoring
- docs sync without new product semantics

prefer worker-worthy delegation whenever the write scopes can be cleanly separated.

Keep the main thread for:

- architecture decisions
- product-semantics decisions
- utterance-governed official truth
- integration and final review

## Execution Loop

1. read the execution dashboard
2. confirm the global build ladder, current pointer, legal-next set, deferred legal slices, and best-next choice
3. confirm slice legality and write boundary
4. choose `planner-local` or `worker-worthy`
5. execute the slice
6. run the narrowest harness that can prove the slice
7. update reality through code, tests, and execution docs only where needed

For repo-structure or docs-ontology work, also run the advisory hygiene scan:

- `python scripts/harness_garbage_collect.py`

## Desktop / Operator Rule

Desktop interaction should stay lean:

- do not turn ordinary local work into handoff-heavy ritual
- do not create task artifacts unless the boundary actually needs them
- use handoff only for explicit transfer or long interruption recovery
- keep status visible through `CURRENT_EXECUTION_PLAN.md`, harness output, and git history
