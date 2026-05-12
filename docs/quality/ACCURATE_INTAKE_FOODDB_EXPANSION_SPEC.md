# Accurate Intake FoodDB Expansion Spec

This document is the Current Shell FoodDB expansion spec for the local self-use Accurate Intake foundation.

It defines how FoodDB may expand source coverage, macro-aware candidate records, packet-ready evidence, and rebuild/migration posture without letting unapproved data become ManagerRuntime truth.

It complements:

- [ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md](ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md)
- [ACCURATE_INTAKE_RAKE_EVIDENCE_TRACK_SCOPE.md](ACCURATE_INTAKE_RAKE_EVIDENCE_TRACK_SCOPE.md)
- [ACCURATE_INTAKE_FOODDB_WEBSEARCH_LLM_ACTIVATION_PLAN.md](ACCURATE_INTAKE_FOODDB_WEBSEARCH_LLM_ACTIVATION_PLAN.md)
- [ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md](ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md)
- [FOODDB_SELF_USE_V1_1000_PACKET_READY_COVERAGE_PLAN.md](FOODDB_SELF_USE_V1_1000_PACKET_READY_COVERAGE_PLAN.md)

## Scope

```yaml
current_mainline: Calorie Deficit Logging MVP local self-use foundation
track: FoodDB
owner_lane: not_applicable
direction_challenge_subagent: not_available
direction_challenge_skip_reason: agent_thread_limit_reached; inline direction challenge applied
capability_layer: L4-L6 retrieval_intent_to_evidence_packet_to_nutrition_synthesis_seam
slice_mode:
  - contract_guard
  - product_capability
  - offline_runtime
user_facing_behavior_changed: false
runtime_truth_changed: false
mutation_changed: false
safe_to_proceed_now: true
why_not_local_next_step_trap: broad source capture can begin now, but runtime promotion must stay batch-gated and rebuildable
```

This spec authorizes FoodDB expansion work in source, candidate, validation, and approved packet-ready lanes. It does not authorize ManagerRuntime, AppShell, ledger, mutation, production DB, or private self-use approval changes.

## Boundary Rules

FoodDB may own:

- raw nutrition source inventories and adapters
- macro-aware `FoodEvidenceCandidate` records
- source quality and provenance validators
- auto-eligible review batches
- approved packet-ready evidence artifacts
- FoodDB rebuild and migration drills

FoodDB must not own:

- Manager intent, workflow effect, target attachment, or final response decisions
- ManagerContextPacket shape
- ledger mutation legality
- frontend truth math
- AppShell rendering semantics
- WebSearch snippets as runtime nutrition truth
- dogfood feedback as automatic FoodDB truth

## Best-Practice Basis

- [Taiwan FDA open-data food nutrition records](https://data.nat.gov.tw/dataset/8543?feature=featurea09&kv=default) provide local per-100g and per-unit nutrient source evidence.
- [USDA FoodData Central](https://fdc.nal.usda.gov/api-guide) provides public-domain API/download data and separates data types such as generic, survey, foundation, and branded food records.
- [FAO/INFOODS data-quality guidance](https://www.fao.org/infoods/infoods/standards-guidelines/data-quality/en/) requires food matching, source provenance, units, denominator, component identifiers, and compilation quality to remain visible.
- [Open Food Facts](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/) provides open packaged-food product data, but it is user-contributed and must be candidate/review evidence unless separately approved.
- Current repo retrieval policy keeps source classes explicit, metadata/lexical retrieval before open-ended semantic recall, and retrieved candidates separate from answer or runtime truth.

## Source Tiers

```yaml
source_tiers:
  tier_0_existing_seed:
    examples:
      - existing small anchor store
      - existing exact item card seed
    allowed_role:
      - baseline comparison
      - small packet-ready seed

  tier_1_taiwan_official_generic:
    examples:
      - TFDA/Taiwan food nutrition open data
    default_role: source_evidence_only
    promotion_role:
      - generic_common_serving_anchor after serving mapping and approval
      - listed_component_anchor after unit/portion mapping and approval

  tier_2_official_label_or_menu:
    examples:
      - packaged nutrition label
      - brand official page
      - chain menu nutrition page
    default_role: exact_item_candidate
    promotion_role:
      - exact_brand_item after identity, serving, macro, and source audit

  tier_3_usda_fdc:
    examples:
      - FoodData Central Foundation Foods
      - FNDDS
      - SR Legacy
      - Global Branded Foods
    default_role: fallback_candidate
    promotion_role:
      - generic_fallback_anchor only when Taiwan-local source is unavailable and source class is explicit

  tier_4_open_food_facts:
    examples:
      - barcode product lookup
      - user-contributed package nutrition
    default_role: candidate_only
    promotion_role:
      - exact_item_candidate only after manual/source audit

  tier_5_websearch:
    examples:
      - official page discovery
      - menu or product label candidate discovery
    default_role: candidate_discovery_only
    promotion_role:
      - none without extract review and explicit FoodDB approval
```

## Data Lanes

```yaml
data_lanes:
  raw_source_vault:
    purpose: store original rows/files/pages and source metadata
    runtime_truth_allowed: false
    required_fields:
      - source_id
      - source_class
      - source_name
      - source_url_or_file_ref
      - source_license
      - source_accessed_at
      - original_record_id
      - original_name
      - original_unit
      - original_denominator
      - original_nutrient_fields

  food_evidence_candidate:
    purpose: normalized candidate row generated from raw source
    runtime_truth_allowed: false
    required_fields:
      - candidate_id
      - source_id
      - source_class
      - canonical_name
      - aliases
      - locale
      - food_family
      - runtime_role_candidate
      - serving_basis
      - portion_basis
      - kcal_point
      - kcal_range
      - protein_g_point
      - protein_g_range
      - carbs_g_point
      - carbs_g_range
      - fat_g_point
      - fat_g_range
      - macro_basis
      - macro_confidence
      - macro_source_strength
      - macro_visibility_candidate
      - source_provenance
      - validation_status
      - schema_version
      - source_adapter_version
      - mapping_policy_version

  validated_candidate:
    purpose: candidate passed mechanical source, unit, and sanity checks
    runtime_truth_allowed: false
    required_fields:
      - validator_version
      - validation_reasons
      - validation_warnings
      - duplicate_or_alias_collision_status
      - macro_null_reason

  auto_eligible_packet_candidate:
    purpose: batch-review surface, not runtime truth
    runtime_truth_allowed: false
    required_fields:
      - batch_id
      - eligibility_policy_version
      - sample_audit_group
      - approval_needed

  approved_packet_ready:
    purpose: compact evidence consumable by ManagerRuntime
    runtime_truth_allowed: true
    allowed_runtime_roles:
      - exact_brand_item
      - generic_common_serving_anchor
      - listed_component_anchor
    required_fields:
      - approved_packet_id
      - runtime_role
      - runtime_truth_allowed
      - source_refs
      - serving_basis
      - portion_basis
      - kcal_point
      - kcal_range
      - protein_g
      - carbs_g
      - fat_g
      - macro_visibility_status
      - macro_source_basis
      - macro_confidence
      - missing_macro_policy
      - approval_metadata
```

## Runtime Role Policy

### Exact Brand Item

Use for packaged foods, convenience-store items, chain menu items, and products with stable identity.

Requirements:

- official label, official menu, or audited package source
- serving size and denominator preserved
- kcal and macro fields copied from source, not inferred
- source identity strong enough to avoid near-match promotion
- exact source freshness recorded

### Generic Common Serving Anchor

Use for common self-use food entries such as rice, chicken rice, beef noodle, egg pancake, bento components, or common drinks.

Requirements:

- raw source may be per 100g, but runtime anchor must include serving/portion mapping
- kcal may be point/range
- macro values may be point/range or null
- uncertainty and portion basis preserved
- generic food must not pretend to be an exact brand item

### Listed Component Anchor

Use for componentized baskets such as luwei, salty chicken, oden, hot pot items, and buffet components.

Requirements:

- approved per-unit, common-portion, or per-weight basis
- component can be combined only when user lists the item
- bare basket family remains clarify-only
- macro may be null if source is missing

### Basket, Alias, Modifier, And Source Evidence

These records must not directly carry runtime nutrition truth.

```yaml
no_truth_roles:
  basket_family:
    examples: luwei, salty_chicken, buffet
    allowed_use: ask_followup_and_candidate_framing
  alias:
    allowed_use: retrieval_match_only
  modifier:
    examples: half_sugar, less_rice, large_cup
    allowed_use: query_or_portion_adjustment_rule_only
  source_evidence_only:
    examples: TFDA per100g rows, USDA generic rows
    allowed_use: derivation_source_for_approved_anchor
```

## Macro Policy

FoodDB is macro-aware but calorie-first.

```yaml
macro_policy:
  exact_brand_item:
    expected: complete_macro_when_label_provides_it
    missing_macro_allowed: false unless source explicitly lacks field

  generic_common_serving_anchor:
    expected: macro_optional
    missing_macro_allowed: true
    missing_macro_behavior: preserve_null_do_not_invent

  listed_component_anchor:
    expected: macro_optional
    missing_macro_allowed: true
    missing_macro_behavior: preserve_null_do_not_invent

  basket_family_alias_modifier:
    expected: no_macro_truth
    missing_macro_behavior: not_applicable
```

Forbidden macro behavior:

- infer protein, carbs, or fat from food name alone
- infer macro values from kcal alone
- use LLM guesses as macro truth
- show macro as visible when `macro_visibility_status` is hidden or unknown
- let AppShell sum or parse macros from assistant text

## Validation Gates

```yaml
validation_gates:
  source_gate:
    checks:
      - source_class_present
      - source_license_or_usage_present
      - source_record_id_present
      - accessed_at_or_release_version_present

  unit_denominator_gate:
    checks:
      - per_100g_vs_per_serving_explicit
      - grams_ml_unit_explicit
      - serving_size_present_for_exact_items
      - unit_conversion_trace_present_when_converted

  identity_gate:
    checks:
      - exact_brand_requires_strong_identity
      - generic_name_must_not_be_promoted_as_exact
      - alias_collision_reported

  nutrition_sanity_gate:
    checks:
      - kcal_non_negative
      - macro_non_negative_or_null
      - kcal_macro_coherence_warning_when_macro_present
      - extreme_values_require_review

  runtime_role_gate:
    checks:
      - source_evidence_only_not_runtime_truth
      - basket_family_not_runtime_truth
      - websearch_candidate_not_runtime_truth
      - off_candidate_not_runtime_truth_without_review

  packet_contract_gate:
    checks:
      - manager_packet_allowed_fields_only
      - macro_contract_present
      - source_refs_present
      - approval_metadata_present
```

## Retrieval And Ranking Policy

FoodDB retrieval should use explicit source classes and role-aware ranking.

```yaml
ranking_priority:
  exact_lookup:
    - approved exact_brand_item with strong identity
    - exact_item_candidate for review display only

  generic_lookup:
    - approved generic_common_serving_anchor
    - validated source_evidence_only for candidate context only
    - external fallback candidate when local source missing

  listed_basket_lookup:
    - approved listed_component_anchor for each listed component
    - ask follow-up when components are missing

  bare_basket_lookup:
    - no nutrition packet
    - ask composition follow-up
```

Ranking must not let source popularity, fuzzy name match, or WebSearch snippet confidence override runtime role approval.

## Batch Promotion Policy

Promotion is a batch operation, not a side effect of ingestion.

```yaml
promotion_batch:
  input:
    - validated_candidate
    - auto_eligible_packet_candidate
    - sample_audit_report
  required_metadata:
    - promotion_batch_id
    - promotion_policy_version
    - reviewer_or_approval_rule
    - source_refs
    - non_claims
  output:
    - approved_packet_ready evidence
  forbidden:
    - promote_all_rows
    - promote_raw_source
    - promote_websearch_snippet
    - promote_off_user_contributed_data_without_review
    - promote_macro_guess
```

Before ManagerRuntime consumes a new batch, the batch must produce an approved packet-ready artifact with:

- `fixture_or_real=real`
- `source_quality`
- `macro_contract`
- lane counts for exact, generic, and listed component records
- non-claims for product readiness and production DB

## Contract-Change And Rebuild Strategy

The expansion design assumes FoodDB contracts may still change during self-use.

Hard rule: every approved packet-ready record must be rebuildable from raw source plus mapper/validator/promotion versions.

```yaml
version_fields:
  - fooddb_schema_version
  - source_adapter_version
  - mapping_policy_version
  - validation_policy_version
  - promotion_policy_version
  - promotion_batch_id
  - derived_from_source_ids
```

When a contract changes:

1. Freeze new runtime promotion.
2. Keep raw source vault unchanged.
3. Update mapper or validator behind a new version.
4. Rebuild candidates from raw source.
5. Re-run validation and compare old/new candidate diffs.
6. Rebuild packet-ready artifact for approved lanes only.
7. Re-run ManagerRuntime FoodDB packet E2E and AppShell macro same-truth checks.
8. For local self-use only, wipe or recompute derived intake logs if the old runtime truth shape is incompatible.

Self-use tolerance allows local data reset, but the source/candidate pipeline must still be rebuildable so contract changes do not require manual one-off row surgery.

## First Expansion Families

```yaml
first_expansion_families:
  taiwan_breakfast:
    examples: egg_pancake, rice_ball, soy_milk, scallion_pancake
    target_roles:
      - generic_common_serving_anchor
      - exact_brand_item where official label exists

  bentos_and_rice_modifiers:
    examples: chicken_bento, pork_chop_bento, rice_half, rice_less
    target_roles:
      - generic_common_serving_anchor
      - modifier_policy

  drinks:
    examples: bubble_tea, black_tea, latte, sugar_level, cup_size, toppings
    target_roles:
      - generic_common_serving_anchor
      - modifier_policy
      - optional_refinement_hints

  listed_basket_components:
    examples: luwei_tofu, kelp, meatball, oden_items, salty_chicken_items
    target_roles:
      - listed_component_anchor

  convenience_store_and_packaged_food:
    examples: rice_ball, lunch_box, sandwich, yogurt, protein_drink
    target_roles:
      - exact_brand_item
```

## Build Train

```yaml
fooddb_expansion_train:
  pr1_source_registry:
    goal: define tracked source registry and local raw-source inventory contract
    product_value: start broad collection without runtime truth risk

  pr2_raw_ingest:
    goal: ingest TFDA and local staged sources into raw local artifacts
    product_value: preserve source data for rebuildable expansion

  pr3_candidate_schema:
    goal: normalize macro-aware FoodEvidenceCandidate records
    product_value: make all source classes comparable before validation

  pr4_candidate_validation:
    goal: validate provenance, units, source role, kcal, macro, aliases, and collisions
    product_value: stop low-quality rows before review/promotion

  pr5_tfda_source_evidence:
    goal: bulk TFDA per100g records as source_evidence_only
    product_value: expand Taiwan local nutrition coverage without false serving truth

  pr6_common_serving_anchor_batch:
    goal: promote a small reviewed Taiwan common-serving batch
    product_value: improve real self-use generic estimates

  pr7_exact_label_lane:
    goal: add official-label exact item candidates and first approved exact macro cases
    product_value: support packaged/brand items with visible macros

  pr8_listed_component_lane:
    goal: add luwei/salty-chicken/oden component anchors
    product_value: improve listed basket logging while bare basket remains clarify-only

  pr9_packet_ready_builder:
    goal: produce approved packet-ready artifact with macro_contract and lane counts
    product_value: handoff real FoodDB evidence to ManagerRuntime safely

  pr10_retrieval_index:
    goal: index approved records and candidates by role-aware lexical/fuzzy routing
    product_value: improve recall without making retrieval own truth

  pr11_manager_e2e_with_real_fooddb:
    goal: run exact/generic/drink/listed-basket/correction macro-present and macro-missing cases
    product_value: verify runtime packet use, response honesty, and same-truth behavior

  pr12_rebuild_drill:
    goal: prove raw->candidate->validated->packet-ready rebuild after policy version bump
    product_value: reduce future contract-change cost

  pr13_dogfood_gap_review_loop:
    goal: convert reviewed self-use food gaps into candidate backlog only
    product_value: focus expansion on real usage without auto-promoting feedback
```

Data-only expansion batches may repeat after this train, but each batch must still preserve raw source, candidate, validation, approval, packet-ready, and rebuild evidence.

## Acceptance Gates

```yaml
acceptance_gates:
  source_inventory_gate:
    required:
      - source registry updated
      - raw artifact generated locally
      - source license and class present

  candidate_gate:
    required:
      - candidate schema includes macro fields
      - missing macro remains null
      - source refs preserved

  validation_gate:
    required:
      - invalid unit or missing provenance rejected
      - websearch/off candidates runtime_truth_allowed=false
      - basket families runtime_truth_allowed=false

  promotion_gate:
    required:
      - batch approval metadata
      - lane counts
      - macro_contract
      - sample audit

  e2e_gate:
    required:
      - exact macro-present case
      - generic macro-missing case
      - listed component case
      - bare basket no-commit case
      - correction/recompute case
      - no invented macro or source exactness

  rebuild_gate:
    required:
      - candidates rebuild from raw source
      - promoted artifact rebuilds from approved source refs
      - diff report explains changed records
```

## Non-Claims

```yaml
non_claims:
  - no product readiness claim
  - no private self-use approval
  - no production DB approval
  - no WebSearch runtime truth
  - no automatic promotion from dogfood feedback
  - no ManagerRuntime semantic ownership change
  - no AppShell truth math approval
```
