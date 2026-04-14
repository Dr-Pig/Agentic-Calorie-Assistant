# Follow-Up Closure Seed Inventory

## Purpose

This inventory defines the seed sources for `2.2d-followup-closure-validation-foundation`.

It does not replace the benchmark sources. It records which existing benchmark cases should be converted into stateful two-turn closure cases.

## Sources

- [`tests/fixtures/benchmark_test_set_v1.json`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/tests/fixtures/benchmark_test_set_v1.json)
- [`docs/quality/benchmark_test_set_v1.txt`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/benchmark_test_set_v1.txt)
- [`docs/quality/benchmark_test_set_v2.txt`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/benchmark_test_set_v2.txt)
- [`docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md)

## Decision Seeds

### `ask_followup_only`

Structured seeds from `benchmark_test_set_v1.json`:

- `case_002`
- `case_017`

Text seeds from `benchmark_test_set_v2.txt`:

- `case_010_shared_stirfry_generic`
- `case_017_luwei_generic`

### `estimate_with_followup`

Structured seeds from `benchmark_test_set_v1.json`:

- `case_010`
- `case_012`
- `case_013`
- `case_016`

Text seeds from `benchmark_test_set_v2.txt`:

- `case_012_poke_generic`
- `case_014_zhajiangmian_generic`

### `direct_estimate` control set

Structured controls from `benchmark_test_set_v1.json`:

- `case_011`
- `case_014`
- `case_015`
- `case_018`

## Conversion Rule

- use benchmark cases only as decision/closure seeds
- do not treat single-turn benchmark fixtures as finished stateful multi-turn cases
- author explicit follow-up replies that close the unresolved slot
- validate backend continuity first:
  - same intake boundary
  - correct closure/supersession behavior
  - no duplicate meal thread creation
- do not require durable memory or retrieval deepening for this wave

## Initial Founder-Fit Cases

The first authored stateful cases for this wave are:

- `intake_multi_turn_golden_ask_followup_brand_completion_001`
- `intake_multi_turn_golden_estimate_followup_drink_refinement_001`

These are intentionally narrow:

- one case for `ask_followup_only -> completion`
- one case for `estimate_with_followup -> refinement`

If runtime validation reveals additional gaps, add more founder-fit stateful cases before widening into `2.2e`.
