# Layer Dependency Rules

## Purpose

This document defines which repository layers may depend on which other layers.

Use this together with:

- [`AGENTS.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
- [`docs/governance/BUILD_FILE_PLACEMENT_RULES.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/BUILD_FILE_PLACEMENT_RULES.md)

The goal is to stop quiet boundary seepage such as:

- route code reaching directly into persistence
- domain code importing framework or database libraries
- schema surfaces absorbing runtime behavior
- `app/agent/` becoming an unbounded god layer

## Canonical Layers

- `app/web`
  - route surfaces, transport adapters, router assembly
- `app/schema_defs`
  - typed request / response / trace contracts
- `app/application`
  - orchestration, read-model assembly, deterministic workflow policies
- `app/search`
  - query-time retrieval facades, ranking pipelines, external search composition
- `app/domain`
  - canonical business models and invariants
- `app/infrastructure`
  - persistence, storage, integration adapters
- `app/agent`
  - model-facing prompt contracts, output normalization, stage-local parsing helpers

## Allowed Dependency Direction

Preferred high-level dependency flow:

- `web -> application -> domain`
- `web -> schema_defs`
- `application -> domain`
- `application -> schema_defs`
- `application -> infrastructure`
- `application -> search`
- `search -> schema_defs`
- `search -> domain`
- `search -> infrastructure`
- `infrastructure -> domain`
- `infrastructure -> schema_defs`
- `agent -> schema_defs`
- `agent -> domain`
- `application -> agent`

This is not a requirement that every layer must depend on the next one. It is the allowed direction of ownership when a dependency exists.

## Hard Rules

### `app/web`

Must not import:

- `app.infrastructure`

Why:

- route modules must not become persistence owners
- DB ownership belongs behind application or infrastructure boundaries

Current enforcement note:

- `app/web -> app.infrastructure` is a hard failure
- `app/web -> sqlalchemy` is currently warning-only while route dependency injection is still being normalized

### `app/domain`

Must not import:

- `app.web`
- `app.infrastructure`
- `fastapi`
- `sqlalchemy`

Why:

- domain must stay framework-light and persistence-agnostic

### `app/schema_defs`

Must not import:

- `app.web`
- `app.infrastructure`
- `fastapi`
- `sqlalchemy`

Why:

- schema contracts should not depend on routing or storage behavior

### `app/search`

Must not import:

- `app.web`
- `fastapi`

Why:

- search modules are query-time composition and retrieval ownership, not route surfaces
- transport ownership belongs in `app/web`

## `app/agent` Role

`app/agent` is not a general-purpose execution layer.

It is reserved for:

- prompt text or prompt contracts
- model-facing parsing helpers
- stage-local normalization and output recovery
- lightweight evidence packet construction that stays storage-agnostic

It must not own:

- route handling
- persistence writes
- direct database access as the default pattern
- infrastructure adapters
- broad workflow orchestration that belongs in `app/application`

### Current Enforcement Scope

The repository will move toward stricter `app/agent` enforcement, but v1 layer integrity checks treat `app/agent` as:

- documented and reviewable
- advisory for dependency drift
- not yet a hard fail for all legacy imports

This avoids blocking the current codebase before the remaining `agent` split work is planned.

## Review Rule For `app/agent`

If an `app/agent/*` file needs:

- database access
- store-backed lookup
- route/context wiring
- commit-path persistence

move that ownership into `app/application` or `app/infrastructure` and keep `app/agent` focused on model-facing artifacts.

## Enforcement Script

Use:

- [`scripts/check_layer_integrity.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/check_layer_integrity.py)

`v1` hard-fails:

- `app/web` importing `app/infrastructure`
- `app/domain` importing forbidden framework or infrastructure layers
- `app/schema_defs` importing forbidden framework or infrastructure layers
- `app/search` importing `app/web` or `fastapi`

`v1` advisory-checks:

- `app/web` imports of `sqlalchemy`
- `app/agent` imports that suggest persistence or route ownership drift

As the repo stabilizes, advisory checks can be promoted into hard failures.
