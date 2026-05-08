# App Engineering Operating Entry

## Purpose

This document is the product-wide anti-drift operating entry for current app implementation work.

Use it before high-impact slices so the implementer starts from the correct owner docs, required planning fields, and forbidden shortcut patterns.

It complements canonical owner docs. It does not replace product specs, runtime specs, or task-specific bootstrap docs.

## Current Mainline Default

The current default mainline is the `Current Shell` split-delivery plan for the `Calorie Deficit Logging MVP local self-use foundation`.

For new windows, the default bootstrap after this operating entry is:

1. `docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md`
2. `docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml`
3. `docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml`
4. the relevant track-specific runbook or scope doc

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

## Owner Doc Map

| Concern | Owner doc |
| --- | --- |
| current bootstrap and document taxonomy | [docs/DOC_INDEX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/DOC_INDEX.md) |
| current split-delivery ownership and coordination | [docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md) |
| current shell contract and gate order | [docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml), [docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml) |
| historical pre-self-use runtime interpretation | [docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md) |
| business-domain-first architecture and layer discipline | [docs/specs/app_v2_ideal_architecture_final.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/app_v2_ideal_architecture_final.md) |

This entry is an operating layer, not a new semantic owner.

## Hard Operating Rules

- Product truth is higher-order than eval shape.
- Compatibility paths may remain temporarily, but only as explicit debt, not as templates for new code.
- Provider, model, transport, DB, and storage quirks must not become product semantics.
- Split by reason to change, not file length alone.
- Fake providers, test helpers, and local bridges must not become hidden semantic owners.

## Read Order

1. `AGENTS.md`
2. [docs/DOC_INDEX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/DOC_INDEX.md)
3. this operating entry
4. the active Current Shell bootstrap pack
5. the relevant track-specific canonical spec or runbook
6. task-specific tests or eval gates

Use [docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md) only when the task explicitly needs historical pre-self-use architecture or harness reference.
