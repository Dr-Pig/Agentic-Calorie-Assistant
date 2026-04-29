# App V2 Engineering Operating Entry

## Purpose

This document is the product-wide anti-drift operating entry for App V2 implementation work.

Use it before high-impact slices so the implementer starts from the correct owner docs, required planning fields, and forbidden shortcut patterns.

It complements canonical owner docs. It does not replace product specs, runtime specs, or phase-specific bootstrap docs.

---

## Use This Before High-Impact Work

Treat this entry as required before slices that touch:

- provider or model boundaries
- retrieval, web search, or extract seams
- DB or persistence ownership
- packet or evidence ownership
- mutation, commit, or ledger boundaries
- architecture-boundary changes
- fat-file-risk or freeze-growth-risk files

If the slice is routine, local, and clearly inside an existing boundary, use the normal phase bootstrap and task-specific spec path instead.

---

## Owner Doc Map

Use these docs as the actual rule owners:

| Concern | Owner doc |
| --- | --- |
| Business-domain-first architecture, layer discipline, reason-to-change | [`docs/specs/app_v2_ideal_architecture_final.md`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/app_v2_ideal_architecture_final.md) |
| Staged seam timing, dependency inversion timing, transition order | [`docs/specs/WAVE_1_ARCHITECTURE_TRANSITION_LADDER.md`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_ARCHITECTURE_TRANSITION_LADDER.md) |
| Wave 1 build order and phase-specific guardrails | [`docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md) |
| Runtime objects, ownership, and canonical state transitions | [`docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md) |
| Re-plan, fat-file, freeze-growth, and boundary review protocol | [`docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md) |

This entry is an operating layer, not a new semantic owner.

---

## Hard Operating Rules

- App, domain, and application code must depend on ports, repositories, and app-owned contracts, not concrete adapters.
- Provider, model, transport, DB, and storage quirks must not become product semantics.
- Candidate, support, accepted evidence, synthesis, draft, committed truth, and mutation layers must stay distinct.
- Concrete compatibility paths may remain temporarily, but only as trace-visible debt; they are not templates for new code.
- Split by reason to change, not file length alone.
- Fake providers, test helpers, and producer-local bridges must not become hidden semantic owners.
- Retrieval intent must stay separate from retrieval execution.
- Packet acceptance, hard recheck, and final synthesis ownership must not collapse back into one surface for convenience.

---

## Capability Dependency Build Order

Do not use product journey order or local slice momentum as implementation order.

Implementation order must follow the product capability dependency pyramid:

- `L0 Product Operating Rules`
- `L1 InteractionEvent / CurrentTurnContext`
- `L2 AttachmentDecision / TransitionGuardResult`
- `L3 MealThread / Draft / Commit Boundary`
- `L4 RetrievalIntent / Source Selection`
- `L5 Evidence / Packet Layer`
- `L6 Nutrition Synthesis`
- `L7 Final Mapping Boundary`
- `L8 Mutation / Ledger / Version`
- `L9 Same-Truth / UI / Memory / Proactive`

Planning rule:

- downstream diagnostic-only work may proceed before every upstream layer is fully closed
- downstream user-facing behavior, runtime truth, or mutation must not proceed before required upstream context, ownership, and transition boundaries are contract-backed
- if a local next step conflicts with the capability dependency pyramid, stop and re-plan

---

## Required Planning Fields For High-Impact Slices

Before implementing a high-impact slice, the planner and reviewer output must explicitly state:

- `repo_truth_used`
- `external_references_checked`
- `adopted_guidance`
- `rejected_guidance`
- `owners_touched`
- `dependency_direction_changed`
- `forbidden_promotions`
- `why_this_slice_is_still_narrow`
- `stop_conditions`
- `verification_gate`
- `capability_layer`
- `upstream_dependencies`
- `slice_mode`
- `user_facing_behavior_changed`
- `runtime_truth_changed`
- `mutation_changed`
- `safe_to_proceed_now`
- `why_not_local_next_step_trap`

Required slice dependency check shape:

```yaml
capability_layer:
upstream_dependencies:
  - layer:
    contract_status: missing | draft | contract_backed | tested
    risk_if_missing:
slice_mode:
  - diagnostic_only
user_facing_behavior_changed: true | false
runtime_truth_changed: true | false
mutation_changed: true | false
safe_to_proceed_now: true | false
why_not_local_next_step_trap:
```

`slice_mode` is a list, not a single enum. Some slices intentionally span more than one planning posture, for example `diagnostic_only + offline_runtime` or `fixture_only + producer_honesty`.

If these fields are missing, the slice is not ready for worker implementation.

---

## Forbidden Shortcut Patterns

Do not let new code:

- consume Tavily, OpenAI-compatible, BuilderSpace, or other provider raw shapes directly in app or domain layers
- branch on model names or provider names to decide product semantics
- depend on SQL table shape, JSON path shape, file layout, or ORM quirks in application/domain behavior
- promote producer/test/local-fallback helpers into hidden truth owners
- copy concrete dispatch branches into new application code
- let search candidates carry final truth, packet verdicts, exactness posture, or mutation authority

Concrete adapter details belong in adapter or profile policy layers, not in product contracts.

---

## Compatibility Surface Rule

Existing concrete runtime paths may remain temporarily when they are:

- trace-visible
- documented as local debt
- not silently promoted into canonical product truth

When a slice touches such a path, either:

- add the thin seam first, or
- record the debt explicitly and keep the slice narrow

Do not copy a compatibility surface forward just because it is already present in the repo.

---

## Deferred Mechanisms

This slice does not add enforcement scripts yet.

Future governance slices may add:

- import or boundary checks
- file-size and fat-file reports
- architecture-debt automation
- stronger repo hygiene gates

Until then, use this entry plus the current owner docs as the manual anti-drift mechanism.

---

## How This Fits With Phase Bootstrap

Use the read order:

1. `AGENTS.md`
2. [`docs/V2_DOC_INDEX.md`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/V2_DOC_INDEX.md)
3. this operating entry
4. the relevant phase bootstrap
5. task-specific canonical spec
6. task-specific tests or eval gates

For Wave 1, this means reading this entry before [`docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md).

---

## Not In Scope Here

This operating entry does not:

- refactor runtime code
- define new product semantics
- replace owner docs
- authorize live provider or live Tavily rollout
- change readiness criteria by itself

Its only job is to make future implementation less likely to drift.
