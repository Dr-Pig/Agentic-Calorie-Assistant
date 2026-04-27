# EvoMap Workflow

## Purpose

EvoMap is a reusable lesson system, not a patch log.

Use it to reduce repeated architectural forgetting across slices, especially for:

- provider and transport capability lessons
- contract and boundary lessons
- workflow and debugging lessons
- durable architecture rules

Do not use it as the source of truth for current runtime behavior. Repo docs, code, and artifacts remain the primary truth.

## Operating Rule

Not every substantive slice needs an EvoMap touchpoint.

Use EvoMap when the current slice introduces a reusable capability need, a generic workflow gap, or a problem likely to recur across models, providers, or repos.

Do not use EvoMap mechanically on every slice. If the current blocker is already well-explained by current repo docs, artifacts, readiness reports, and tests, continue from repo truth unless reuse value is likely.

If EvoMap is unavailable, say so explicitly and continue with repo truth. Do not fabricate recall or recorded memory.

## Before a Slice

Run EvoMap recall (`gep_recall`) before planning or implementation only when the slice touches reusable architecture, runtime behavior, provider/model strategy, transport, evaluation design, debugging workflow, or another capability pattern likely to generalize.

Required behavior:

- if EvoMap is relevant, recall relevant lessons
- say which recalled lessons affect the current slice
- if no relevant lesson is found, say none
- if EvoMap is not materially relevant, say so and continue with repo truth

EvoMap recall informs planning. It does not override current repo truth.

External lookup order:

1. local repo truth
2. local EvoMap recall
3. external Skills or community GEP assets only when the need is generic enough to justify capability lookup

Do not search external Skills or GEP assets on every slice.

## During a Slice

Use EvoMap as a reuse guide, not as permission to bypass repo rules.

Hard rules:

- do not use EvoMap to justify parser widening
- do not use EvoMap to justify schema loosening
- do not use EvoMap to justify product semantics inside provider adapters
- keep current repo docs, code, and artifacts as source of truth
- use recalled lessons only where they generalize to the current slice
- treat external Skills as procedural guides and GEP assets as validated capability hints, not architecture truth

## After a Slice

Record EvoMap outcomes (`gep_record_outcome`) only when the result produces reusable lessons.

Good candidates for recording:

- a reusable debugging pattern
- a provider capability attribution lesson
- a boundary or contract lesson
- a workflow lesson that should change future slice planning
- an architecture debt lesson that implies later cleanup

Do not record:

- artifact filenames
- exact pytest passed counts
- timestamps
- one-off provider noise
- temporary local patch details
- narrow slice-specific trivia with no reuse value

If the slice only moved a repo-local blocker without producing a reusable lesson, do not record it just to satisfy process.

## Good Memory Shape

Prefer lessons such as:

- provider adapters must not own product semantics
- manager boundaries should move from prompt obedience into shared contract helpers
- prompt guides shape behavior, schema narrows validate shape, guards reject unsafe actions, verifiers attribute failure families
- contract should remain model-agnostic, prompt rendering model-aware, provider adapters transport-aware, and validation shared
- targeted diagnostics need stable artifact separation and explicit failure attribution

## Reporting Expectation

When closing a slice, explain whether EvoMap changes the next plan.

- if yes, say what reusable lesson affects the next slice
- if no, say EvoMap is not materially changing the next slice
