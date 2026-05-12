# FoodDB Self-Use v1 1000 Packet-Ready Coverage Plan

Status: active target spec

Owner: FoodDB

Consumers:

- ManagerRuntime packet consumption and live diagnostic gates
- AppShell same-truth verification after ManagerRuntime gates are green
- human/operator dogfood review

This document defines the FoodDB coverage target required before claiming the Current Shell v1 desktop local self-use FoodDB lane is sufficiently broad for daily calorie logging. It extends [ACCURATE_INTAKE_FOODDB_EXPANSION_SPEC.md](ACCURATE_INTAKE_FOODDB_EXPANSION_SPEC.md) and does not replace the existing source, candidate, validation, promotion, macro, or rebuild rules.

## Mainline Slice

```yaml
current_mainline: Current Shell self-use MVP local desktop dogfood
is_detour: false
mainline_blocker_being_removed: FoodDB coverage is too narrow for realistic daily calorie logging and full live Manager diagnostics
capability_layer: L4-L6 retrieval_intent_to_evidence_packet_to_nutrition_synthesis
upstream_dependencies:
  - layer: L0 Product Operating Rules
    contract_status: contract_backed
    risk_if_missing: FoodDB expansion would create product-readiness or production-data claims
  - layer: L5 Evidence / Packet Layer
    contract_status: contract_backed
    risk_if_missing: expanded records could leak raw source rows into ManagerRuntime
  - layer: L6 Nutrition Synthesis
    contract_status: draft
    risk_if_missing: expanded evidence may not be evaluated for estimate quality
slice_mode:
  - contract_guard
  - product_capability
  - offline_runtime
user_facing_behavior_changed: false
runtime_truth_changed: false
mutation_changed: false
safe_to_proceed_now: true
why_not_local_next_step_trap: the plan freezes coverage targets and gates before data batches, preventing broad ingestion from becoming unreviewed runtime truth
```

## Scope

In scope:

- define the `1000` packet-ready target for self-use FoodDB v1
- define runtime lane counts and category quotas
- define source, promotion, macro, and rebuild gates for the 1000-record target
- define ManagerRuntime handoff gates after expanded FoodDB batches
- define the live LLM acceptance standard for the fixed 18-case matrix and edge-case matrix
- define the PR train estimate for this coverage target

Out of scope:

- production DB
- product readiness or private self-use approval
- broad WebSearch promotion
- AppShell truth math
- ManagerRuntime semantic ownership changes
- automatic promotion from dogfood feedback
- new runtime lane names beyond the existing approved roles

## Best-Practice Evidence

```yaml
best_practice_evidence:
  required: true
  sources_checked:
    - official_or_primary_source: https://www.fao.org/infoods/infoods/standards-guidelines/en/
      adopted_guidance:
        - preserve food matching, data-quality, source, unit, and denominator evidence
        - do not hide conversion or matching assumptions during publication or use
    - official_or_primary_source: https://www.fda.gov.tw/tc/site.aspx?sid=271
      adopted_guidance:
        - use Taiwan food nutrition data as local source evidence
        - keep per-100g or per-unit source posture separate from serving-level runtime anchors
    - official_or_primary_source: https://data.nat.gov.tw/dataset/8543?feature=featurea09&kv=default
      adopted_guidance:
        - use open Taiwan nutrition rows as source evidence, not automatic runtime truth
    - official_or_primary_source: https://fdc.nal.usda.gov/download-datasets
      adopted_guidance:
        - keep data type/source class explicit across generic, survey, foundation, and branded records
    - official_or_primary_source: https://platform.openai.com/docs/guides/agent-evals
      adopted_guidance:
        - evaluate workflow-level agent behavior with traces, not final answer text only
    - official_or_primary_source: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
      adopted_guidance:
        - include multi-turn and tool-use traces in agent evals
  rejected_guidance:
    - do not treat large raw food tables as packet-ready runtime truth
    - do not use live LLM failures alone as product semantics or prompt-hardening authority
    - do not require all generic or component records to have macros before calorie logging
  conflict_with_repo_habits:
    - older readiness artifacts sometimes tracked evidence volume without proving runtime consumption
  how_the_design_changed:
    - coverage target is expressed as packet-ready records, not raw rows
    - expansion is split by runtime lane and food category
    - full live LLM acceptance is tied to trace-layer grading and fixed case manifests
```

## Decision Ownership

```yaml
llm_deterministic_boundary:
  decision_surface: food identity, portion uncertainty, evidence use, final nutrition synthesis
  truth_owner: hybrid
  deterministic_role: validate source, schema, units, runtime lane, macro visibility, promotion, mutation legality
  llm_role: synthesize user food semantics and uncertainty from approved packets during ManagerRuntime diagnostic runs
  do_not_override:
    - deterministic code must not infer user intent or target attachment from raw text
    - LLM must not invent kcal, macro, source exactness, or packet approval

semantic_owner:
  user_intent: ManagerRuntime
  food_semantics: ManagerRuntime synthesis over approved FoodDB/WebSearch packets
  routing_or_workflow_effect: ManagerRuntime
  mutation_legality: deterministic guard
  persistence_truth: domain services and read models
  food_source_truth: FoodDB approved packet-ready artifact
```

## Current Baseline

The current baseline is useful for pipeline validation but too narrow for realistic daily use.

```yaml
current_packet_ready_profile:
  packet_ready_records: 462
  exact_brand_item_macro_complete: 94
  generic_common_serving_anchor: 194
  listed_component_anchor: 174
  source_evidence_only_tfda_rows: 848
  source_evidence_only_runtime_truth_allowed: false
  self_use_gap: coverage density, not lane architecture
```

Build the current-vs-target gap report with:

```powershell
python scripts/build_fooddb_self_use_v1_coverage_gap.py --build-current-artifact --output artifacts/fooddb_self_use_v1_1000_packet_ready_coverage_gap.json
```

The generated artifact is report-only. It reads approved packet-ready lane counts and reports the remaining gap to the 1000-record target. It must not create FoodDB truth, promote candidates, change ManagerRuntime semantics, or claim readiness.

## Self-Use v1 Coverage Target

`1000 packet-ready` means 1000 approved records that can enter the approved packet-ready artifact and be consumed by ManagerRuntime through existing FoodDB packet contracts. It does not mean raw source rows, WebSearch snippets, validator-only candidates, aliases, or modifier-only rules.

```yaml
fooddb_self_use_v1_target:
  total_packet_ready_records: 1000
  runtime_lane_targets:
    exact_brand_item: 250
    generic_common_serving_anchor: 400
    listed_component_anchor: 350
  exact_macro_complete_minimum: 200
  generic_or_component_macro_present_target_non_blocking: 150
  modifier_rules_not_counted_as_packet_ready_records: 100-150
  broad_raw_source_rows_not_counted_as_packet_ready: true
```

### Runtime Lane Definitions

```yaml
exact_brand_item:
  target_count: 250
  examples:
    - convenience store packaged food
    - packaged dairy and protein drinks
    - chain restaurant item with official nutrition
    - chain cafe drink with official nutrition
  required:
    - strong product identity
    - source refs
    - serving denominator
    - kcal
    - protein_g, carbs_g, fat_g when official source provides them
    - macro_visibility_status
  forbidden:
    - near-match exact promotion
    - WebSearch snippet-as-truth
    - LLM macro or kcal guessing

generic_common_serving_anchor:
  target_count: 400
  examples:
    - Taiwan breakfast item
    - rice bowl or bento
    - noodle or soup bowl
    - common drink serving
    - home-style dish
  required:
    - serving basis or serving range
    - kcal point or range
    - uncertainty/portion basis
    - source refs or source-evidence lineage
    - macro fields present as values or null
  forbidden:
    - pretending generic estimates are exact labels
    - blocking kcal logging only because macro is unknown

listed_component_anchor:
  target_count: 350
  examples:
    - luwei item
    - oden item
    - hot pot item
    - salty fried snack item
    - buffet or bento side
    - sauce or addon with nutrition truth
  required:
    - per unit, common portion, or per weight basis
    - kcal point or range
    - source refs or source-evidence lineage
    - component can be combined only when user lists it
  forbidden:
    - bare basket nutrition truth
    - hidden component inference from basket name alone
```

## Category Quotas

These category quotas are planning targets. Runtime packet roles still remain `exact_brand_item`, `generic_common_serving_anchor`, and `listed_component_anchor`.

```yaml
category_quota_targets:
  exact_brand_item:
    convenience_and_packaged_exact: 120
    chain_restaurant_and_cafe_exact: 80
    official_label_drinks_dairy_and_protein_exact: 50
    subtotal: 250

  generic_common_serving_anchor:
    taiwan_breakfast_and_staples: 80
    rice_bento_and_home_style: 120
    noodles_soup_and_hot_pot_bowls: 80
    generic_drinks_and_beverage_servings: 70
    bakery_dessert_and_snack_servings: 50
    subtotal: 400

  listed_component_anchor:
    luwei_oden_and_hot_pot_components: 120
    salty_fried_and_street_snack_components: 80
    buffet_bento_side_and_protein_components: 100
    sauces_addons_and_portion_components: 50
    subtotal: 350

  total: 1000
```

Minimum coverage examples:

- breakfast: egg pancake, rice ball, radish cake, scallion pancake, toast, sandwich, soy milk, milk tea
- rice and bento: chicken bento, pork chop bento, chicken rice, braised pork rice, curry rice, beef bowl, half rice, less rice
- noodles and soup: beef noodle, dry noodle, fried sauce noodle, wonton soup, meatball soup, pot noodles
- drinks: bubble milk tea, milk tea, latte, black tea, green tea, soy milk, sugar level and cup-size variants
- baskets: luwei, oden, hot pot, salty fried chicken, buffet, bento sides
- exact items: convenience-store meals, packaged snacks, dairy, protein drinks, chain menu items

## Modifier And Portion Rules

Modifier and portion rules improve estimate quality, but they are not counted as packet-ready records unless they carry an approved nutrition truth as a component.

```yaml
modifier_targets:
  target_rule_count: 100-150
  p0_rules:
    - rice_portion: half, less, normal, extra
    - drink_size: medium, large, extra_large
    - sugar_level: unsweetened, less, half, normal
    - ice_level: no_ice, less_ice, normal
    - toppings: boba, pudding, grass_jelly, taro_ball
    - cooking_method: fried, pan_fried, steamed, braised
    - sauce_level: no_sauce, less_sauce, normal
  rules_must_report:
    - affected_anchor_family
    - adjustment_basis
    - confidence
    - source_or_policy_ref
    - whether_user_clarification_is_required
```

## Promotion Standard

```yaml
promotion_standard:
  required_for_every_packet_ready_record:
    - approved_packet_id
    - runtime_role
    - canonical_name
    - aliases
    - serving_basis
    - portion_basis
    - kcal_point_or_range
    - protein_g
    - carbs_g
    - fat_g
    - macro_visibility_status
    - macro_source_basis
    - macro_confidence
    - source_refs
    - source_class
    - source_quality
    - validation_policy_version
    - promotion_policy_version
    - promotion_batch_id
    - derived_from_source_ids

  disallowed_as_packet_ready:
    - raw_source_rows
    - source_evidence_only_records
    - validator_only_candidates
    - dogfood_feedback
    - WebSearch_snippets
    - Open_Food_Facts_rows_without_review
    - basket_family_records
    - alias_only_records
    - modifier_only_rules
```

Promotion is batch-gated. A batch may be large, but the output must still be reviewable by lane counts, source classes, validation warnings, and sample audit groups.

## Macro Policy

```yaml
macro_policy:
  exact_brand_item:
    macro_expected: true
    exact_macro_complete_minimum: 200
    missing_macro_allowed: only_when_source_explicitly_lacks_macro_fields
    visibility: visible_only_when_packet_has_source_backed_values

  generic_common_serving_anchor:
    macro_expected: optional
    missing_macro_allowed: true
    visibility: hidden_missing_source_or_partial
    kcal_logging_blocked_by_missing_macro: false

  listed_component_anchor:
    macro_expected: optional
    missing_macro_allowed: true
    visibility: hidden_missing_source_or_partial
    kcal_logging_blocked_by_missing_macro: false

  forbidden:
    - LLM_invented_protein_carbs_fat
    - kcal_to_macro_backsolve
    - food_name_to_macro_guess
    - frontend_macro_sum_from_text
    - macro_visible_when_show_macro_false
```

## Runtime Handoff Gates

ManagerRuntime may consume the 1000-record target only through the approved packet-ready artifact.

```yaml
runtime_handoff_gates:
  artifact_gate:
    required:
      - artifact_type: accurate_intake_approved_packet_ready_fooddb_artifact
      - fixture_or_real: real
      - packet_ready_item_count >= 1000
      - packet_ready_lane_counts.exact_item_card >= 250
      - packet_ready_lane_counts.generic_common_serving >= 400
      - packet_ready_lane_counts.listed_component >= 350
      - macro_contract present
      - source_quality present
      - non_claims present

  manager_packet_gate:
    required:
      - exact macro-present packet case
      - exact macro-missing rejected or hidden case
      - generic macro-hidden kcal range case
      - listed component basket case
      - bare basket no-commit case
      - WebSearch candidate not truth case
      - no raw source rows in Manager packet

  synthesis_quality_gate:
    required:
      - exact item estimate matches source
      - generic estimate uses honest range
      - listed basket estimate sums approved components only
      - modifier/refinement changes estimate in plausible direction
      - final response basis cites allowed packet/read-model facts only
```

## Fixed 18-Case Live LLM Acceptance

The fixed 18-case matrix remains the primary ManagerRuntime live diagnostic acceptance set. It must not be regenerated ad hoc at live time.

```yaml
fixed_18_case_live_llm_acceptance:
  manifest: docs/quality/accurate_intake_mvp_live_diagnostic_case_manifest.json
  fixed_18_case_live_llm_required: true
  provider_calls_required: true
  generated_cases_at_runtime_allowed: false
  per_case_artifact_required: true
  full_suite_artifact_required: true
  one_request_at_a_time: true
  retry_dependent_pass_allowed: false
  timeout_pass_allowed: false
  trace_layers_required:
    - provider_profile_and_prompt_versions
    - current_turn_context_packet
    - manager_pass_1_decision
    - requested_tools
    - filtered_tool_plan
    - executed_tools
    - compact_packets
    - manager_pass_2_synthesis
    - guard_result
    - mutation_result
    - renderer_input_basis
    - final_response_basis
    - latency_cost_cache_usage
  pass_threshold:
    all_18_cases_have_trace_layer_grade: true
    all_blocking_trace_layers_green: true
    no_invented_kcal_macro_or_source_exactness: true
    no_deterministic_semantic_override: true
    no_websearch_snippet_as_truth: true
```

The live matrix is diagnostic evidence. It does not select a production model, approve private self-use, or approve mutation rollout.

## Edge-Case Live Matrix Acceptance

Edge cases should be fixed before live execution and should test failure families not fully represented by the 18-case matrix.

```yaml
edge_live_matrix:
  edge_live_matrix_min_cases: 36
  provider_calls_required: true
  deterministic_holdouts_may_be_larger: true
  live_case_generation_at_runtime_allowed: false
  edge_families:
    exact_identity_and_near_match:
      min_cases: 4
      purpose: prevent wrong-brand or near-match exact promotion
    generic_portion_extremes:
      min_cases: 4
      purpose: test small/large/ambiguous portion estimates
    modifier_composition:
      min_cases: 5
      purpose: test sugar, size, rice, sauce, topping changes
    bare_vs_listed_basket:
      min_cases: 6
      purpose: preserve ask-followup for bare baskets and commit path for listed components
    macro_visibility:
      min_cases: 4
      purpose: test visible, hidden, partial, and missing macro behavior
    websearch_candidate_boundary:
      min_cases: 4
      purpose: keep WebSearch as candidate evidence only
    multi_turn_context_correction:
      min_cases: 5
      purpose: test target candidates, pending followup, supersede, remove, and ledger delta
    no_plan_query_and_unsupported:
      min_cases: 4
      purpose: test no-plan degraded, query-only no mutation, and unsupported target updates
```

Edge live failures may create attribution records, holdouts, and product-rule review tasks. They must not directly harden prompt, schema, or runtime semantics without a product-approved rule.

## Build Milestones

```yaml
milestones:
  m1_contract_and_batch_pipeline:
    target_packet_ready_records: 0
    exit_gate:
      - this target spec is merged
      - source registry, candidate, validation, auto-eligible, and rebuild gates are aligned to the 1000 target

  m2_first_runtime_scale:
    target_packet_ready_records: 300
    lane_minimums:
      exact_brand_item: 75
      generic_common_serving_anchor: 125
      listed_component_anchor: 100
    exit_gate:
      - ManagerRuntime packet smoke passes exact/generic/listed cases
      - no broad live claim

  m3_daily_use_scale:
    target_packet_ready_records: 600
    lane_minimums:
      exact_brand_item: 150
      generic_common_serving_anchor: 250
      listed_component_anchor: 200
    exit_gate:
      - common self-use categories covered
      - macro visible/hidden cases pass
      - batch rebuild drill passes

  m4_self_use_v1_fooddb_target:
    target_packet_ready_records: 1000
    lane_minimums:
      exact_brand_item: 250
      generic_common_serving_anchor: 400
      listed_component_anchor: 350
    exit_gate:
      - 18-case live LLM matrix passes
      - edge-case live matrix passes
      - latency/cost/cache summary produced
      - dogfood feedback can create review-only FoodDB gaps
```

## PR Train Estimate

This is a working estimate, not a task tracker. Each PR should advance a data batch, runtime gate, live eval gate, or rebuild capability. Wrapper-only or status-only PRs are not part of this count.

```yaml
estimated_pr_train:
  total_estimate: 46-62
  contract_and_source_pipeline: 5-7
  data_expansion_to_300_packet_ready: 8-10
  data_expansion_to_600_packet_ready: 8-10
  data_expansion_to_1000_packet_ready: 8-12
  runtime_packet_and_synthesis_gates: 6-8
  fixed_18_live_llm_matrix: 5-6
  edge_case_live_matrix: 6-8
  final_dogfood_fooddb_closeout: 2-3
```

After each merged PR, the remaining estimate must be updated. If the train exceeds 62 PRs, the next PR description must explain whether the extra work is data quality, runtime correctness, live eval failure repair, or avoidable overengineering.

## Completion Criteria

```yaml
self_use_fooddb_v1_complete_when:
  packet_ready_item_count >= 1000
  exact_brand_item_count >= 250
  generic_common_serving_anchor_count >= 400
  listed_component_anchor_count >= 350
  exact_macro_complete_count >= 200
  every_packet_ready_record_has_source_refs: true
  every_packet_ready_record_has_macro_visibility_status: true
  raw_source_rows_excluded_from_manager_packets: true
  websearch_snippets_excluded_from_runtime_truth: true
  fixed_18_case_live_llm_matrix_green: true
  edge_live_matrix_min_36_cases_green: true
  trace_layer_grading_green_for_blocking_layers: true
  latency_cost_cache_summary_present: true
  rebuild_drill_green_after_policy_version_bump: true
```

## Non-Claims

```yaml
non_claims:
  - no product readiness claim
  - no private self-use approval
  - no production DB approval
  - no production model selection
  - no mutation rollout approval
  - no WebSearch runtime truth
  - no automatic dogfood feedback promotion
  - no AppShell nutrition truth math
```
