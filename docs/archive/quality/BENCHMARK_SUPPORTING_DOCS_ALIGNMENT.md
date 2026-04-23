# Benchmark Supporting Docs Alignment

## Purpose

This note records the current alignment requirements between:

- [`docs/quality/L5B_BENCHMARK_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5B_BENCHMARK_SPEC.md)
- [`docs/quality/BENCHMARK_CASE_SCHEMA.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/BENCHMARK_CASE_SCHEMA.md)
- [`docs/quality/BENCHMARK_FOLDER_LAYOUT.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/BENCHMARK_FOLDER_LAYOUT.md)
- [`docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md)

This exists to avoid silent drift when supporting docs lag behind the main benchmark spec.

## Current Alignment Status

### Already aligned

- bucket-oriented benchmark organization
- stateful multi-turn case structure
- use of `case.yaml`, `initial_state.json`, `memory_seed.json`, `turns.json`
- support for regression and safety-focused cases

### Needs explicit extension

The supporting docs should eventually be updated to explicitly support:

- `dataset_split`
- `oracle_type`

## Recommended `dataset_split` values

- `founder_golden`
- `general_sanity`
- `stress_only`
- `regression_only`

## Recommended `oracle_type` values

- `state_delta`
- `candidate_legality`
- `proposal_gate`
- `rescue_legality`
- `cross_flow_sync`

## Why this matters

`L5B` now distinguishes:

- founder-fit vs generalized sanity coverage
- benchmark buckets that use different oracle shapes

If supporting docs do not expose these fields, future benchmark authors may create cases that are structurally valid but under-specified for evaluation.

## Editing Note

The current supporting docs contain encoding/anchor instability in some sections.  
Until those files are safely normalized, use this alignment note as the source of truth for the extra fields above rather than forcing risky whole-file rewrites.
