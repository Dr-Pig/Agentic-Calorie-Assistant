# App Target State Blueprint

This blueprint defines the long-term `app/` shape without requiring an immediate large move.

## Target Layout

- `app/domain/`
  - canonical entities
  - value objects
  - domain services
- `app/application/`
  - pass runners
  - orchestration services
  - commit / proposal gate services
  - use-case assembly
- `app/infrastructure/`
  - persistence
  - database adapters
  - external IO
  - filesystem / queue / storage integrations
- `app/providers/`
  - provider adapters only
  - model routing shims
  - BuilderSpace adapter
- `app/observability/`
  - trace envelope
  - metrics
  - replay support
- `app/usecases/`
  - thin entrypoints only

## Current Classification

### Keep as long-term homes

- `app/domain`
- `app/application`
- `app/infrastructure`
- `app/providers`
- `app/observability`

### Refactor gradually

- `app/usecases`
  - keep only thin entrypoints
  - move business orchestration into `app/application`

### Known legacy-entrypoint candidates

- `app/usecases/text_meal.py`
  - current vertical-slice entrypoint
  - should become a thin assembly layer over `app/application`

### Known refactor targets

- state transition modules still shaped around older meal-log assumptions
- wide orchestrator modules that mix planning, persistence, and response shaping
- provider/stage mapping code that still exposes provider model IDs too early

## Build Alignment

This blueprint should be applied gradually through `docs/specs/L6B_BUILD_STRATEGY_SPEC.md`, not by a single directory-wide move.
