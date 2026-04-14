# Build File Placement Rules

## Purpose

This document defines the repository-wide build path for new files, module naming, and boundary-safe splitting.

Use this together with:

- [`AGENTS.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
- [`docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)

The goal is not "small files at any cost". The goal is:

- role-based placement
- stable naming
- predictable splitting paths
- fewer cross-layer relapses into legacy fat files

## Decision Table

When a change introduces a new responsibility, place it by primary role:

- new route surface or router assembly:
  - `app/web/<capability>_routes.py`
- new request / response schema or typed workflow contract:
  - `app/schema_defs/<capability>.py`
- new orchestration or workflow assembly:
  - `app/application/<capability>_service.py`
- new deterministic decision policy:
  - `app/application/<capability>_policy.py`
- new read-side assembly or projection:
  - `app/application/<capability>_read_model.py`
- new selector / ranking / bounded decision helper:
  - `app/application/<capability>_selector.py`
- new query-time retrieval chain or ranking flow:
  - `app/search/<capability>_retrieval.py`
  - `app/search/<capability>_lookup.py`
- new external search provider adapter:
  - `app/search/<provider>_adapter.py`
- new domain invariant or canonical rule:
  - `app/domain/<capability>_rules.py`
- new canonical model family:
  - `app/domain/<capability>_models.py`
- new persistence or store-backed write path:
  - `app/infrastructure/<capability>_persistence.py`
- new repository / loader / storage bridge:
  - `app/infrastructure/<capability>_store.py`
  - `app/infrastructure/<capability>_repository.py`
  - `app/infrastructure/<capability>_adapter.py`

If more than one role seems plausible, choose the layer that matches the code's main reason to change.

## Naming Rules

Suffixes are ownership signals, not style preferences.

- `*_routes.py`
  - only route surface, dependency injection, router wiring, transport normalization
- `*_service.py`
  - only orchestration, workflow sequencing, use-case assembly
- `*_policy.py`
  - only deterministic decision logic or guardrail policy
- `*_read_model.py`
  - only read-side assembly / projection / response composition
- `*_selector.py`
  - only bounded selection / ranking / filtering
- `*_retrieval.py`
  - only query-time retrieval flow, ranking pipeline, or retrieval composition
- `*_lookup.py`
  - only lookup facade for query-time read access across storage-backed or exact-match sources
- `*_rules.py`
  - only domain invariants or deterministic business rules
- `*_models.py`
  - only canonical business models
- `*_persistence.py`
  - only db-backed persistence or commit-path storage operations
- `*_store.py`
  - only storage retrieval / persistence helpers with store semantics
- `*_repository.py`
  - only repository-style persistence boundary
- `*_adapter.py`
  - only external or subsystem integration adaptation

Avoid generic names like:

- `helpers.py`
- `utils.py`
- `misc.py`
- `support.py`

unless the module is truly scoped to one workflow boundary and the name is already part of an existing family.

## Split Rules

When an existing file starts mixing responsibilities, split by change reason:

- orchestration moves to `*_service.py`
- deterministic branching or scoring moves to `*_policy.py`
- response or projection assembly moves to `*_read_model.py`
- retrieval composition or ranking moves to `*_retrieval.py`
- lookup-only query access moves to `*_lookup.py`
- persistence writes move to `*_persistence.py`
- route-specific transport code moves to `*_routes.py`
- canonical rules move to `*_rules.py`

Do not split only by "this file is long". Split because the code changes for different reasons.

## Protected Legacy File Handling

The following files are protected:

- `app/routes.py`
- `app/schemas.py`
- `app/usecases/text_meal.py`

If a change cannot safely fit there:

1. identify the new responsibility
2. place it in the correct module family using the decision table above
3. keep the protected file limited to wiring, re-export, or router inclusion
4. record the touch reason when the task or replan artifact is boundary-sensitive

## Touched-Area Discipline

Tasks that touch boundary-sensitive files or add new modules should declare:

- `allowed_touch_areas`
- `forbidden_touch_areas`
- `new_files_expected`

Recommended examples:

- `allowed_touch_areas: app/web, app/application/current_budget_read_model.py`
- `forbidden_touch_areas: app/routes.py, app/schemas.py`
- `new_files_expected: app/web/today_routes.py`

This keeps file placement explicit before implementation starts.

## Review Questions

Before adding a new file or extending a current one, answer:

1. what is this code's primary role?
2. what is its main reason to change?
3. which layer should own that reason?
4. if this code grows later, what is the next clean split boundary?

If the answers are unclear, stop and make the boundary decision explicit in the active plan or replan note.

## Appendix: Workspace Layout

Tracked areas:

- `app/`: application code
- `scripts/`: developer scripts and tooling
- `tests/`: intentionally versioned tests and fixtures
- `docs/`: design notes and operating docs

Ignored runtime areas:

- `runtime/db/`: SQLite database files
- `runtime/logs/`: request traces and audit logs
- `runtime/artifacts/session_records/`: session transcript output
- `runtime/tmp/`: temporary repair scripts and scratch runtime output
- `runtime/trash/`: disposable local scratch residue
- `data_build/`: generated build output
- `data_build/normalized/`: normalized and reproducible nutrition build outputs

Ignored data workspace:

- `workspace_data/`: local datasets, exports, downloaded files
- `減肥駐守/raw_data/`: legacy crawl data still kept in-place for compatibility
- `減肥駐守/*.jsonl.gz`: large compressed exports

Legacy scratch paths that should be migrated out of root:

- `tmp/`
- `.trash/`
- `child_outputs/`

Rules:

1. keep application code and docs in tracked directories only
2. write runtime output under `runtime/`
3. write reproducible build output under `data_build/`
4. write large downloaded or manually collected datasets under `workspace_data/`
5. do not stage or push files larger than the hook threshold unless you intentionally raise the limit
