# Repo Agent Rules

These rules are repository-level build rules for human and agent contributors.

## Primary Principle

`responsibility boundaries > local convenience`

Do not choose a file because it is nearby or already imported. Choose a file because its role matches the responsibility being added.

## Canonical File Roles

New code should follow these ownership boundaries by default:

- `app/web/*`: route surfaces, transport adapters, router assembly
- `app/schema_defs/*`: contracts, DTOs, payload models, response models
- `app/application/*`: orchestration, read models, deterministic policies, workflow assembly
- `app/search/*`: query-time retrieval facades, ranking pipelines, external search composition
- `app/domain/*`: canonical business models, invariants, domain state rules
- `app/infrastructure/*`: persistence, storage bridges, external adapters
- `app/usecases/*`: thin workflow entrypoints and compatibility shims only

Do not place new persistence, response shaping, prompt logic, or deterministic business rules into a thin entrypoint module.

For placement and naming details, use:

- [`docs/BUILD_FILE_PLACEMENT_RULES.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/BUILD_FILE_PLACEMENT_RULES.md)

## Protected Legacy Files

The following files are protected thin-entrypoint or compatibility surfaces:

- `app/routes.py`
- `app/schemas.py`
- `app/usecases/text_meal.py`

These files may only receive:

- extraction or thinning work
- compatibility re-exports
- thin router assembly
- boundary-safe wiring that does not expand responsibility
- tightly scoped bug fixes inside the file's current responsibility

These files must not receive:

- new route handlers
- new schema/model definitions
- new orchestration logic
- new persistence logic
- new response shaping logic
- new deterministic policy or math

If a change needs more than thin wiring in a protected file, stop and move the new responsibility into the correct module family first.

## Existing File Edit Rule

For existing code files, prefer targeted edits over delete-and-recreate replacement.

Default rule:

- do not delete an existing code file only to recreate the same path with rewritten contents

Allowed exceptions:

- the file is being retired or moved as part of an explicit boundary refactor
- patch-anchor, tooling, or encoding constraints make a safe targeted edit impractical
- the replacement is a deliberate thin-entrypoint conversion or compatibility shim extraction

If an exception is used:

- keep the path and responsibility transition explicit
- preserve behavior and exports unless the task intentionally changes them
- record the reason in the task artifact or replan note when the file is boundary-sensitive

## File Growth Policy

File size is a guardrail, not the design goal. The real problem is mixed responsibility.

Use these default ranges:

- thin entrypoints / routes: `80-180` lines preferred
- application services / read-model assemblers: `120-250` lines preferred
- policy / deterministic rule modules: `40-180` lines preferred
- workflow-specific schema files: `80-220` lines preferred

Protection thresholds:

- `app/usecases/text_meal.py`: `350`
- `app/schemas.py`: `450`
- `app/routes.py`: `400`

Freeze-growth architecture risk files:

- `app/application/evidence_assembly.py`
- `app/application/context_assembly.py`
- `app/agent/knowledge_packets.py`

Watchlist architecture risk files:

- `app/agent/nutrition_engine.py`

Crossing a threshold is a boundary-review event, not permission to keep growing the file.

Freeze-growth rule:

- freeze-growth files may shrink, stay flat for tightly scoped bug fixes, or accept boundary-safe wiring
- freeze-growth files must not grow until a deliberate extraction task reduces their responsibility pressure
- if a freeze-growth file is touched at all, the staged task artifact or re-plan note must name the file and classify the change as `shrink-only extraction`, `contained bug fix`, or `boundary-safe wiring`
- touching a freeze-growth file without that explicit justification is a governance failure even if line count stays flat

## Build Rule For New Work

When adding new behavior:

- new API surface goes to `app/web/*`
- new contract or payload type goes to `app/schema_defs/*`
- new orchestration or read-model logic goes to `app/application/*` or a focused support module
- new query-time retrieval facade or ranking pipeline goes to `app/search/*`
- new domain invariant goes to `app/domain/*`
- new persistence or adapter logic goes to `app/infrastructure/*`

Do not default to adding code into an existing large file just because the call path already passes through it.

If a protected or boundary-sensitive file is not the right home for the new responsibility, create a focused module in the correct family from the placement rules instead of inventing an ad-hoc location.

## Protected-File Gate

The repo includes:

- `scripts/check_fat_files.ps1`

This gate checks:

- protected-file line thresholds
- staged growth of protected files
- protected-file thin-entrypoint structure
- freeze-growth architecture files
- watchlist architecture audit visibility

If the gate reports a protected-file structure violation, the change is mislocated even if the file is still short.

## Planning Rule

When a task touches a protected file or a boundary-sensitive area, the task or replan note should state:

- why this file was touched
- whether the change is pure wiring / compatibility
- where the real responsibility lives after the change

For boundary-sensitive work, prefer explicitly stating:

- `allowed_touch_areas`
- `forbidden_touch_areas`
- `new_files_expected`

Avoid task wording like "put this in `text_meal.py`" unless that file is already the canonical thin entrypoint for the change.

## Migration Discipline

Schema-sensitive ORM changes must ship with Alembic migrations.

Current hard rule:

- if `app/models.py` changes, the same change set must also include a migration file under `alembic/versions/`

Do not rely on runtime schema repair or startup-time stamping to cover model drift.
