# App Engineering Operating Entry

## Purpose

This document is the product-wide anti-drift operating entry for current app implementation work.

Use it before high-impact slices so the implementer starts from the correct owner docs, required planning fields, and forbidden shortcut patterns.

It complements canonical owner docs. It does not replace product specs, runtime specs, or task-specific bootstrap docs.

## Current Mainline Default

The current default mainline is the `Current Shell` split-delivery plan for the `Calorie Deficit Logging MVP local self-use foundation`.

For new windows, the default bootstrap after this operating entry is:

1. `docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md`
2. `docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md`
3. `docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml`
4. `docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml`
5. the relevant track-specific runbook or scope doc

`docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md` is the neutral entrypoint for older pre-self-use runtime docs.

## Use This Before High-Impact Work

Treat this entry as required before slices that touch:

- provider or model boundaries
- retrieval, web search, or extract seams
- DB or persistence ownership
- packet or evidence ownership
- mutation, commit, or ledger boundaries
- architecture-boundary changes
- fat-file-risk or freeze-growth-risk files

Every non-trivial PR-producing slice must include a best-practice alignment note before PR publication. Low-risk documentation or fixture-only slices may record `best_practice_evidence.required=false` with rationale. High-impact runtime, retrieval, database, API, testing, security, provider, tool-orchestration, memory, proactive, or mutation slices must check current official or primary sources and record adopted guidance, rejected guidance, conflicts with repo habits, and how the design changed. This evidence informs design, but the repo truth hierarchy still controls product semantics, owner docs, and runtime invariants.

## Owner Doc Map

| Concern | Owner doc |
| --- | --- |
| current bootstrap and document taxonomy | [docs/DOC_INDEX.md](../DOC_INDEX.md) |
| minimal current execution pointer | [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](../exec-plans/active/CURRENT_EXECUTION_PLAN.md) |
| current split-delivery ownership and coordination | [docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md](../quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md) |
| current shell contract and gate order | [docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml](../quality/CURRENT_SHELL_SYNC_CONTRACT.yaml), [docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml](../quality/MANAGER_RUNTIME_GATE_LEDGER.yaml) |
| historical pre-self-use runtime interpretation | [docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md](LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md) |
| business-domain-first architecture and layer discipline | [docs/specs/app_v2_ideal_architecture_final.md](app_v2_ideal_architecture_final.md) |

This entry is an operating layer, not a new semantic owner.

## Hard Operating Rules

- Product truth is higher-order than eval shape.
- Compatibility paths may remain temporarily, but only as explicit debt, not as templates for new code.
- Provider, model, transport, DB, and storage quirks must not become product semantics.
- Split by reason to change, not file length alone.
- Fake providers, test helpers, and local bridges must not become hidden semantic owners.
- Manager semantic ownership is mandatory for composition sufficiency, estimability, follow-up necessity, target attachment, correction/removal target, and final action. Deterministic runtime may validate, reject, downgrade, hide disallowed facts, block mutation, or request one bounded post-Manager repair round; it must not use raw user text, food names, keyword heuristics, fixture labels, or case IDs to decide those semantics before the Manager pass. Active runtime must not synthesize fallback/shadow 400 kcal or macro packets; missing approved nutrition evidence is represented as evidence unavailable, not as a default estimate.

## Shared Manager / Deterministic Ownership Invariant

LLM / Manager owns:

- composition sufficiency
- estimability
- whether to ask follow-up
- whether to call WebSearch
- exact/generic/component/basket posture
- attach target
- correction/removal target
- final workflow action
- user-facing response meaning

Deterministic code may only:

- validate schema
- validate source eligibility
- validate target existence / uniqueness
- enforce mutation legality
- hide unsupported kcal/macro/source facts
- reject/downgrade unsafe output
- request one bounded repair

Deterministic code must not:

- inspect raw user text or food name to decide semantic route
- classify a meal as unestimable before Manager output exists
- decide follow-up necessity
- decide WebSearch need
- create fallback kcal/macros
- rewrite Manager action to make a test pass

In short: deterministic code must not inspect raw user text, food name, case ID, or fixture label to decide semantic product behavior.

This invariant is repeated in the intake runtime and Golden Set specs so EDD work cannot drift into deterministic semantic routing when a live model behaves poorly.

## Read Order

1. `AGENTS.md`
2. [docs/DOC_INDEX.md](../DOC_INDEX.md)
3. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](../exec-plans/active/CURRENT_EXECUTION_PLAN.md)
4. this operating entry
5. the active Current Shell bootstrap pack
6. the relevant track-specific canonical spec or runbook
7. task-specific tests or eval gates

Use [docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md](LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md) only when the task explicitly needs historical pre-self-use architecture or harness reference.
