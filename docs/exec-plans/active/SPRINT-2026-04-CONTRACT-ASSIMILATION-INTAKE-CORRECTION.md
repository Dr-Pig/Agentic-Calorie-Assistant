# Sprint Plan

## Sprint ID

- `SPRINT-2026-04-CONTRACT-ASSIMILATION-INTAKE-CORRECTION`

## Purpose

This sprint is the first post-harness implementation sprint.

Its job is to absorb the existing intake/runtime code into the current canonical contracts and state model before starting the first read-model and UI-facing slices.

This sprint does not introduce new product capabilities. It reduces truth drift between:

- current implementation
- typed runtime contracts
- canonical persistence
- deterministic math rules

## Why This Sprint Comes First

The repository already has working intake/runtime code and a canonical persistence bridge.

The highest-value next step is not to add new features on top of that mixed state. The highest-value next step is to make the current working path conform more tightly to:

- [docs/specs/L2A_DATA_DICTIONARY_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2A_DATA_DICTIONARY_SPEC.md)
- [docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md)
- [docs/specs/L3M_GUARDRAIL_MATH_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3M_GUARDRAIL_MATH_SPEC.md)

Only after that should the repo start the first stable read-model and UI-facing slice.

## Scope

### In Scope

- contract assimilation for current intake/runtime code
- historical correction hardening
- explicit canonical version/correction behavior
- preparation for `2.3a-current-budget-read-model`

### Out Of Scope

- recommendation work
- calibration work
- rescue work
- proactive work
- polished UI work

## Slice / Task Mapping

### Primary Active Slice

- `2.2b-historical-correction`
  - active task: [`TASK-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/tasks/TASK-2026-04-11-001-INTAKE-CORRECTION-FOUNDATION.md)

### Secondary Queued Slice

- `2.3a-current-budget-read-model`
  - queued task: [`TASK-2026-04-11-002-READMODEL-FOUNDATION.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/tasks/TASK-2026-04-11-002-READMODEL-FOUNDATION.md)

### Supporting Current Slices

- `2.1a-simple-provisional-estimate`
- `2.2a-active-meal-continuation`

These are not the main sprint target, but they must remain stable while the sprint work proceeds.

## Work Packages

### Work Package A. Contract Assimilation

Goal:

- reduce vocabulary drift between existing implementation and `L3T / L2A / L3M`

Focus:

- align intake result shapes to `L3T`
- keep `CommitRequestCandidate` and canonical write semantics authoritative
- keep deterministic math and ledger semantics aligned to `L3M`

Expected touch areas:

- `app/schemas.py`
- `app/application/*`
- `app/infrastructure/canonical_persistence.py`
- `app/application/canonical_commit_bridge.py`

### Work Package B. Historical Correction Hardening

Goal:

- make correction target resolution, version supersession, and correction-safe canonical writes explicit and test-covered

Focus:

- correction path must create a new `MealVersion`
- correction path must not regress into in-place overwrite
- legacy meal-log path must remain transitional only

Expected touch areas:

- `app/application/*`
- `app/infrastructure/canonical_persistence.py`
- `app/usecases/text_meal.py`
- `tests/test_text_meal.py`
- `tests/test_canonical_persistence.py`

### Work Package C. Read-Model Readiness

Goal:

- prepare `2.3a-current-budget-read-model` to start immediately after correction semantics stabilize

Focus:

- identify canonical query helpers needed by current-budget views
- keep read-model semantics separate from recommendation logic

Expected touch areas:

- query/read helper modules under `app/application/*` or `app/infrastructure/*`
- read-model-facing tests

## Acceptance Criteria

This sprint is complete when:

- historical correction is explicit, typed, and test-covered
- correction writes create new versions and trigger correct recompute behavior
- intake/runtime result vocabulary is closer to `L3T` and no longer drifts silently
- the queued `2.3a-current-budget-read-model` task can start without ambiguity about correction semantics
- no new unrelated responsibility is pushed into fat files just to finish the sprint

## Tests

Minimum sprint-level verification:

- `historical correction path`
- `version supersession path`
- `canonical persistence regression tests`
- `text meal regression tests`
- any newly introduced read-helper unit tests required to de-risk `2.3a`

## Re-plan Conditions

Re-plan the sprint before continuing if:

- historical correction requires a broader write scope than the checked-in task allows
- `app/schemas.py` or `app/usecases/text_meal.py` would absorb another unrelated concern
- a canonical truth doc must change to support the work
- read-model requirements materially change the correction-path boundary

## Next Sprint Candidate

If this sprint closes cleanly, the next sprint should start with:

- `2.3a-current-budget-read-model`
- then `2.3b-low-fi-today-ui`

Recommendation, rescue, calibration, and proactive work remain out of sequence until the canonical ordering spec says they are ready.
