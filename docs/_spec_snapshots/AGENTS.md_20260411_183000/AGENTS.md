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
- `app/domain/*`: canonical business models, invariants, domain state rules
- `app/infrastructure/*`: persistence, storage bridges, external adapters
- `app/usecases/*`: thin workflow entrypoints and compatibility shims only

Do not place new persistence, response shaping, prompt logic, or deterministic business rules into a thin entrypoint module.

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

Crossing a threshold is a boundary-review event, not permission to keep growing the file.

## Build Rule For New Work

When adding new behavior:

- new API surface goes to `app/web/*`
- new contract or payload type goes to `app/schema_defs/*`
- new orchestration or read-model logic goes to `app/application/*` or a focused support module
- new domain invariant goes to `app/domain/*`
- new persistence or adapter logic goes to `app/infrastructure/*`

Do not default to adding code into an existing large file just because the call path already passes through it.

## Protected-File Gate

The repo includes:

- `scripts/check_fat_files.ps1`

This gate checks:

- protected-file line thresholds
- staged growth of protected files
- protected-file thin-entrypoint structure

If the gate reports a protected-file structure violation, the change is mislocated even if the file is still short.

## Planning Rule

When a task touches a protected file or a boundary-sensitive area, the task or replan note should state:

- why this file was touched
- whether the change is pure wiring / compatibility
- where the real responsibility lives after the change

Avoid task wording like "put this in `text_meal.py`" unless that file is already the canonical thin entrypoint for the change.
