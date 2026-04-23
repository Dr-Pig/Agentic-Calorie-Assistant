# V2 Benchmark Regression Manifest

## Purpose

This manifest governs how archived benchmark suites are admitted into the active V2 quality loop without silently overriding canonical bundle truth.

Current sources:

- [benchmark_test_set_v1.txt](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/archive/quality/benchmark_test_set_v1.txt)
- [benchmark_test_set_v2.txt](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/archive/quality/benchmark_test_set_v2.txt)
- [turn2_hybrid_replay_pack_v1.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/archive/quality/benchmarks_v1/intake/multi_turn/turn2_hybrid_replay_pack_v1.json)

These sources are not default truth. They enter the active loop through normalization, dedupe, and shadow governance.

## Governance

- archived benchmarks must first be normalized into a machine-readable registry under `runtime/evals/benchmark_registry/normalized/`
- dedupe is by behavior family + workflow effect, not by raw string only
- normalized cases are classified into:
  - `duplicate_of_official`
  - `duplicate_of_founder_realism`
  - `benchmark_unique_blocking_candidate`
  - `benchmark_unique_shadow_candidate`
  - `duplicate_of_archive_case:*`
- no archived case becomes blocking until it is:
  - unique versus official/founder gates
  - stable under repeated execution
  - semantically approved

## Initial Promotion Families

The first families eligible for promotion are:

- multi-turn `ask_followup_only -> completion`
- `estimate_with_followup -> refinement`
- exactness honesty / sibling-variant rejection
- correction ownership / same-thread attachment

Promotion is not case-count based. It is constrained by:

- behavior family
- workflow effect
- evidence topology
- source-domain representation

This means archived exact-item cases are not all promoted as blocking. Instead, the active blocking set keeps:

- all unique replay families from the turn-2 hybrid pack
- one representative exactness-honesty case per source domain / topology
- the rest remain shadow unless they add new product coverage

## Output Contract

The benchmark shadow pipeline writes:

- normalized registry JSON under `runtime/evals/benchmark_registry/normalized/`
- blocking registry JSON under `runtime/evals/benchmark_registry/normalized/`
- shadow report JSON under `runtime/evals/benchmark_registry/`

The promoted blocking runner writes:

- blocking regression report JSON under `runtime/evals/v2_benchmark_regression/`

Each shadow report must include:

- `shadow_case_status`
- `dedupe_status`
- `promotion_candidate_status`
- `quality_gap_status`
- `blocking_case_count`
- `blocking_family_counts`

## Quality Oracle

Benchmark quality uses a behavioral oracle, not verbatim answer matching.

Tracked parity goals:

- ask for missing portion-critical details before finalizing
- do not overclaim exactness without strong evidence
- keep component explanations honest to evidence quality
- preserve uncertainty posture when evidence is not exact
- keep user-visible chat/UI synchronization intact
