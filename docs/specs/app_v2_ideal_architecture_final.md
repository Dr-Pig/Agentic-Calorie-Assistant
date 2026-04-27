# Design Document: App V2 Ideal Architecture (Final)

## Business-Domain-First Modular Monolith with Strict Layer Discipline

> **Status**: Working target architecture
>
> This is the recommended end-state for the repo.
>
> It is **not** pure horizontal layer-first.
> It is **not** unstructured feature buckets.
> It is a **business-domain-first modular monolith**, with **explicit internal layers per domain**, designed for **agent-first development**, **predictable placement**, and **mechanical architecture enforcement**.

---

## 1. Executive Summary

This architecture adopts the most useful parts of the Harness Engineering approach:

- agent readability
- strict boundaries
- predictable structure
- mechanical drift prevention via rules and tests

But this repo is the **runtime product itself**, not only a harness platform.
So the primary organizing axis should be **business domains / bounded contexts**, not only horizontal technical layers.

### Final position

- **Top level**: organize by business domains / bounded contexts
- **Inside each domain**: keep explicit clean layers
- **Runtime**: orchestration/platform context, not a business peer that absorbs product rules
- **Shared**: extremely thin; only truly neutral kernel and infra primitives
- **Agent layer**: optional per domain, only where model-facing artifacts are genuinely needed

---

## 2. Core Architecture Principles

1. **Business domains are the top-level organizing principle.**
2. **Layers are internal discipline, not the top-level ontology.**
3. **Runtime coordinates domains; it does not own their business semantics.**
4. **Shared must remain minimal and neutral.**
5. **Cross-domain interactions must be explicit.**
6. **Split by reason to change, not file length alone.**
7. **Use rules, linting, and tests to enforce boundaries.**
8. **Migrate incrementally, not with a big-bang rewrite.**

---

## 3. Target Top-Level Domains

The top-level structure should be organized around these domains:

- `intake`
- `nutrition`
- `budget`
- `body`
- `rescue`
- `recommendation`
- `memory`
- `runtime`
- `shared`
- `providers`
- `knowledge`

### Meaning of each domain

#### `intake`
Owns meal-thread lifecycle:
- text meal logging
- active meal
- pending followup attachment
- item correction / removal
- commit semantics

#### `nutrition`
Owns nutrition evidence and estimation:
- local nutrition lookup
- brand menu lookup
- official grounding / search
- exactness / uncertainty / estimate output

#### `budget`
Owns day-level energy budget and ledger state:
- consumed / remaining kcal
- overshoot
- ledger projections
- budget sync

#### `body`
Owns body plan and body-related state:
- body observations
- TDEE
- activity level
- exercise bonus
- recalibration-related state

#### `rescue`
Owns overshoot rescue logic:
- rescue trigger
- spread calculation
- rescue proposal creation
- rescue proposal acceptance

#### `recommendation`
Owns recommendation flow:
- candidate generation
- ranking / filtering
- suppression
- recommendation result semantics

#### `memory`
Owns durable preference/profile memory:
- long-term preferences
- negative preferences
- golden orders
- memory write/read policy
- top-preference summary

#### `runtime`
Owns orchestration/platform mechanics:
- thin state resolution
- manager orchestration
- tool invocation coordination
- renderer
- sidecar
- run / event trace

#### `shared`
Owns only truly neutral, cross-domain primitives:
- ids
- base entities
- base value objects
- clocks
- generic common request metadata / pagination types
- tiny infra facades

#### `providers`
Owns model/provider adapters only.
These are not domain-neutral utilities; keep them outside `shared`.

#### `knowledge`
Owns read-only static knowledge assets.

---

## 4. Final Folder Tree

> **Important**:
> Not every domain needs every layer on day one.
> Create only the layers that have real code to own.
> Do not create empty symmetry for its own sake.

```text
app/
├── intake/
│   ├── interface/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── schemas.py              # only if intake has transport contracts
│   ├── application/
│   │   ├── __init__.py
│   │   ├── intake_service.py
│   │   ├── commit_service.py
│   │   └── correction_service.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── meal_thread.py
│   │   ├── meal_version.py
│   │   ├── meal_item.py
│   │   └── events.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── persistence.py
│       └── read_models.py
│
├── nutrition/
│   ├── interface/
│   │   ├── __init__.py
│   │   └── schemas.py              # only if needed
│   ├── application/
│   │   ├── __init__.py
│   │   ├── estimation_service.py
│   │   └── lookup_service.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── estimate.py
│   │   ├── evidence.py
│   │   └── policies.py
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── db_lookup.py
│   │   ├── web_search.py
│   │   └── knowledge_loader.py
│   └── agent/
│       ├── __init__.py
│       ├── estimation_llm.py
│       ├── resolution_parser.py
│       └── prompts.py
│
├── budget/
│   ├── interface/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── schemas.py              # only if needed
│   ├── application/
│   │   ├── __init__.py
│   │   ├── budget_service.py
│   │   └── sync_service.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── day_budget.py
│   │   ├── ledger.py
│   │   └── invariants.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── persistence.py
│       └── read_models.py
│
├── body/
│   ├── interface/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── schemas.py              # only if needed
│   ├── application/
│   │   ├── __init__.py
│   │   ├── body_service.py
│   │   ├── exercise_service.py
│   │   └── tdee_service.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── body_profile.py
│   │   ├── body_plan.py
│   │   ├── observation.py
│   │   └── exercise.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── persistence.py
│       └── read_models.py
│
├── rescue/
│   ├── interface/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── schemas.py              # only if needed
│   ├── application/
│   │   ├── __init__.py
│   │   ├── rescue_service.py
│   │   ├── proposal_service.py
│   │   └── acceptance_service.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── proposal.py
│   │   ├── option.py
│   │   └── rescue_calculator.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── persistence.py
│       └── read_models.py
│
├── recommendation/
│   ├── interface/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── schemas.py              # only if needed
│   ├── application/
│   │   ├── __init__.py
│   │   ├── recommendation_service.py
│   │   ├── ranking_service.py
│   │   └── location_service.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── candidate.py
│   │   ├── scoring.py
│   │   └── location_context.py
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── places_client.py
│   │   └── preference_matcher.py
│   └── agent/
│       ├── __init__.py
│       ├── scoring_llm.py          # only if actually needed
│       └── prompts.py
│
├── memory/
│   ├── interface/
│   │   ├── __init__.py
│   │   └── schemas.py              # only if needed
│   ├── application/
│   │   ├── __init__.py
│   │   ├── memory_service.py
│   │   └── preference_service.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── preference.py
│   │   ├── negative.py
│   │   └── pattern.py
│   └── infrastructure/
│       ├── __init__.py
│       ├── persistence.py
│       └── read_models.py
│
├── runtime/
│   ├── interface/
│   │   ├── __init__.py
│   │   └── schemas.py              # runtime-wide transport contracts
│   ├── application/
│   │   ├── __init__.py
│   │   ├── state_resolver.py
│   │   ├── manager_service.py
│   │   ├── execution_guard.py
│   │   ├── renderer.py
│   │   └── sidecar_service.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── run.py
│   │   ├── event.py
│   │   └── decision_envelope.py
│   ├── contracts/
│   │   ├── __init__.py
│   │   ├── sidecar.py
│   │   └── trace.py
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── trace_persistence.py
│   │   └── latency_tracker.py
│   └── agent/
│       ├── __init__.py
│       ├── system_prompts.py
│       └── tool_definitions.py
│
├── shared/
│   ├── kernel/
│   │   ├── __init__.py
│   │   ├── ids.py
│   │   ├── base_entities.py
│   │   ├── value_objects.py
│   │   └── clock.py
│   ├── contracts/
│   │   ├── __init__.py
│   │   └── common.py              # truly common transport bits only
│   └── infra/
│       ├── __init__.py
│       ├── database.py
│       ├── logging.py
│       └── env.py
│
├── providers/
│   ├── __init__.py
│   └── builderspace_adapter.py
│
├── knowledge/
│   ├── __init__.py
│   ├── nutrition_db.json
│   ├── exact_item_cards.json
│   ├── common_dish_priors.json
│   └── meal_templates.json
│
└── main.py
```

---

## 5. Layer Ownership Within a Domain

This matrix applies **inside each business domain**.

### Allowed internal dependency direction

- `interface -> application`
- `application -> domain`
- `application -> infrastructure` (only through explicit adapter/repository usage appropriate to the use case)
- `application -> agent` (when model-facing artifacts are needed)
- `infrastructure -> domain` or `infrastructure -> application contracts`
- `agent -> domain/contracts`
- `domain -> no outward layer dependency`

### Forbidden internal dependency direction

- `domain -> infrastructure`
- `domain -> interface`
- `domain -> framework/provider SDK`
- `interface -> domain logic directly`
- `infrastructure -> agent`
- `agent -> persistence`
- `agent -> route handling`
- `agent -> broad orchestration ownership`

### Meaning of each layer

#### `interface`
Owns:
- routes
- transport mapping
- request parsing
- response mapping

Does not own:
- persistence
- business rules
- provider-specific reasoning

#### `application`
Owns:
- orchestration
- use-case sequencing
- deterministic workflow policy
- selectors
- read-model assembly

Does not own:
- raw DB details
- provider SDK details
- transport concerns

#### `domain`
Owns:
- canonical business models
- invariants
- business rules
- domain-level state transitions

Does not own:
- framework concerns
- persistence concerns
- provider concerns

#### `infrastructure`
Owns:
- persistence
- repositories
- storage adapters
- external integrations
- provider adapters if domain-specific

Does not own:
- business intent decisions
- orchestration policy

#### `agent`
Owns only model-facing artifacts:
- prompts
- model-specific parsing helpers
- output normalization
- recovery helpers

Does not own:
- DB access
- route handling
- broad workflow orchestration
- persistence writes

---

## 6. Cross-Domain Interaction Patterns

> Do **not** think of these as direct domain-to-domain arrows.
> Think of them as **allowed interaction patterns**.

### Preferred interaction patterns, in order

1. **Application-level contracts**
   - For explicit write/intentionful collaboration
   - Example: intake commit updates budget via application contract

2. **Read-model boundaries**
   - For read-only sharing
   - Example: recommendation reads memory preferences through read model

3. **Published events / trace events**
   - For decoupled reactions
   - Example: budget overshoot emits an event that rescue can react to

4. **Runtime orchestration via tools**
   - Important path for manager-driven orchestration
   - Not the only legal communication mechanism

### Examples by domain

#### `intake`
Can:
- write to `budget` through an application-level contract
- emit runtime trace events
- be orchestrated by runtime via tools

Should not:
- directly import nutrition internals
- directly import recommendation or memory internals

#### `nutrition`
Can:
- read `knowledge`
- use shared kernel/common contracts

Should not:
- directly depend on other business domains

#### `budget`
Can:
- read body-plan data through a read-model boundary
- trigger rescue proposal creation through event or application contract

Should not:
- directly import recommendation or memory internals

#### `body`
Can:
- update budget through explicit application contract

Should not:
- directly import intake, rescue, or recommendation internals

#### `rescue`
Can:
- modify ledger state via budget application contract
- read body-plan data through read-model boundary

Should not:
- directly import intake or recommendation internals

#### `recommendation`
Can:
- read memory preferences through read-model boundary

Should not:
- directly import intake, budget, body, or rescue internals

#### `memory`
Can:
- expose read-model and write-contract boundaries

Should not:
- directly depend on other domains

#### `runtime`
Can:
- orchestrate all domains through tools
- use contracts, read models, and events where appropriate

Should not:
- accumulate business rules that belong to intake/budget/body/rescue/etc.

#### `shared`
Can:
- be depended on by everyone, but only for neutral primitives

Should not:
- depend on any domain
- absorb product-specific policy or business logic

---

## 7. Domain Responsibilities, Points of Change, and Side Effects

### `intake`
**Responsibility**
- food intake logging
- meal-thread lifecycle
- item-level correction
- followup attachment

**Points of change**
- new intake types (text/voice/image)
- commit workflow
- correction semantics
- meal-thread model

**Main side effects**
- persist meal-thread state
- update budget through contract
- emit trace events
- optionally update preference memory through explicit boundary

### `nutrition`
**Responsibility**
- evidence gathering
- nutrition estimation
- uncertainty / exactness policy

**Points of change**
- estimation model selection
- evidence hierarchy
- lookup policy
- grounding rules

**Main side effects**
- read knowledge DB
- trigger external search
- emit evidence/trace data

### `budget`
**Responsibility**
- daily budget ledger
- consumed / remaining kcal
- overshoot state

**Points of change**
- ledger sync logic
- overshoot thresholds
- budget projection rules

**Main side effects**
- persist ledger state
- emit rescue trigger events when needed

### `body`
**Responsibility**
- body profile
- body plan
- exercise and body observations
- TDEE logic

**Points of change**
- TDEE formula
- activity-level mapping
- recalibration policy

**Main side effects**
- persist body observations/exercise
- update budget through application contract

### `rescue`
**Responsibility**
- rescue proposals
- overshoot recovery
- acceptance flow

**Points of change**
- proposal types
- rescue calculation rules
- acceptance semantics

**Main side effects**
- persist proposals
- modify budget/ledger through explicit contract

### `recommendation`
**Responsibility**
- recommendation candidates
- ranking/filtering
- suggestion semantics

**Points of change**
- ranking algorithm
- scoring logic
- location enrichment
- suppression policy

**Main side effects**
- read memory preferences
- call external places/location services

### `memory`
**Responsibility**
- long-term preferences
- negative preferences
- pattern memory
- preference summaries

**Points of change**
- consolidation algorithm
- preference inference rules
- read-model shape

**Main side effects**
- persist preference state
- expose read-models to runtime/recommendation

### `runtime`
**Responsibility**
- state resolution
- orchestration
- tool invocation
- renderer
- sidecar
- run/event trace

**Points of change**
- manager prompts
- tool schemas
- orchestration rules
- trace schema
- renderer behavior

**Main side effects**
- call tools/domains
- persist trace data
- emit sidecar data
- produce final response

### `shared`
**Responsibility**
- neutral primitives only

**Points of change**
- base entity shape
- common request metadata
- logging/env/db facade shape

**Main side effects**
- none beyond basic infra utility behavior

---

## 8. Current-to-Target Mapping

### Active ownership map

| Owner | Active location | Notes |
|---|---|---|
| Intake | `app/intake/` | meal-thread lifecycle, pending followup, correction/removal, commit semantics |
| Nutrition | `app/nutrition/` | lookup, web/search grounding, evidence eligibility, exactness, estimate output |
| Budget | `app/budget/` | consumed/remaining, overshoot, ledger projections, aggregate truth |
| Body | `app/body/` | body profile, body plan, observations, TDEE and exercise-related application services |
| Rescue | `app/rescue/` | rescue trigger/proposal/acceptance semantics |
| Recommendation | `app/recommendation/` | recommendation candidate/ranking/suppression semantics |
| Memory | `app/memory/` | durable preference/profile memory and conversation context infrastructure |
| Runtime | `app/runtime/` | state resolution, manager orchestration, tool coordination, guard, sidecar, trace |
| Providers | `app/providers/` | model/provider adapters only |
| Knowledge | `app/knowledge/` | read-only static knowledge assets |

### Root facade status
- The previous vertical-slice entrypoint folder has been fully purged.
- `app/routes.py`, `app/schemas.py`, and `app/models.py` are the ONLY root-level facades kept for test compatibility, but they STRICTLY route to internal domains.

These must remain **thin shims only**.

### Freeze-growth files

Business-domain application services and provider adapters should stay within the active file-size guardrails. New logic belongs in the owning domain module, not in root facades or cross-domain runtime files.

---

## 9. Architecture Enforcement

### Phase 1 hard-fail rules

These should fail CI immediately once introduced:

1. `no_direct_cross_domain_import`
2. `no_circular_dependencies`
3. `layer_order_enforcement`

### Phase 1 advisory rules

These should be reported first, then upgraded to hard-fail later:

1. `runtime_direct_domain` (where runtime bypasses intended orchestration boundaries)
2. `no_shared_policies`
3. `no_empty_symmetry_files`
4. `protected_legacy_no_growth`

### Review questions

Before placing new code, answer:

1. Which business domain owns this behavior?
2. Which internal layer owns its main reason to change?
3. Does this introduce a new cross-domain dependency?
4. Should this be a contract, read model, event, or runtime tool interaction?
5. Is this code truly shared, or just currently convenient to share?

---

## 10. Incremental Migration Plan

> **Do not build the entire tree at once.**
> Validate the main path before expanding.

### Phase 1: Architecture gates

**Goal**: establish mechanical enforcement before moving code.

Deliverables:
- lint rules for cross-domain imports
- circular dependency detection
- layer-order enforcement
- import graph validation script
- CI gate configuration
- initial empty domain structure only where needed

### Phase 2: Runtime seams

**Goal**: extract cross-cutting runtime ownership.

Deliverables:
- `runtime/application/state_resolver.py`
- `runtime/application/manager_service.py`
- `runtime/application/renderer.py`
- `runtime/application/sidecar_service.py`
- `runtime/application/execution_guard.py`
- `runtime/agent/tool_definitions.py`
- `runtime/agent/system_prompts.py`
- `runtime/contracts/sidecar.py`
- `runtime/contracts/trace.py`
- `runtime/infrastructure/trace_persistence.py`

### Phase 3: Core-path contexts

**Goal**: migrate the main user path first.

Priority order:
1. `intake`
2. `nutrition`
3. `budget`

Deliverables:
- entities moved into domain folders
- application services moved into domain application layers
- persistence/read-model code moved into domain infrastructure layers
- routes moved into domain interface layers
- legacy shims preserved for compatibility

### Later phases (not immediate scope)

Phase 4:
- `body`
- `rescue`
- `recommendation`
- `memory`

Phase 5:
- final shared-kernel cleanup
- provider cleanup
- contract cleanup

Phase 6:
- pass-era removal
- bundle-era removal
- legacy shim cleanup when safe

---

## 11. Anti-Patterns to Avoid

### Structural anti-patterns

- **Runtime as god context**
- **Cross-domain direct import**
- **Circular dependencies**
- **Layer inversion**
- **Pure horizontal dumping grounds**
- **Pure context buckets with no internal discipline**

### Code anti-patterns

- `shared` becoming a dumping ground
- giant service files
- business logic leaking into infrastructure
- orchestration leaking into agent or infrastructure
- hardcoded provider-specific behavior in business layers
- empty symmetry files created only for aesthetics

### Process anti-patterns

- skipping gates before migration
- big-bang rewrite
- endless architecture-doc rewriting without executable rules
- migrating all domains before validating core path

---

## 12. Final Summary

This architecture is the recommended end-state:

- **business-domain-first** at the top level
- **strict internal layers** inside each domain
- **runtime as orchestration/platform**, not business owner
- **shared as very thin neutral kernel**, not a dumping ground
- **agent layer only where needed**
- **architecture enforced mechanically** through lint/tests/gates
- **migration done incrementally** with enforcement first

This is the right balance between:
- the agent-legibility and mechanical governance ideas from Harness Engineering
- and the product-domain-first structure needed for a long-lived runtime application
