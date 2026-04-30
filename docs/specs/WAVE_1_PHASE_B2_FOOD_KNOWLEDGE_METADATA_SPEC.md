# Wave 1 Phase B-2 Food Knowledge Metadata Spec

## Purpose

This child spec defines the Wave 1 Phase B-2 food knowledge metadata contract.

It exists because the B2 evidence stack cannot treat the food database as only:

```text
food_name + kcal
```

Food knowledge metadata may describe generic food anchors, exact item card seed data, meal templates, food mention semantics, portion cues, alias semantics, evidence posture hints, uncertainty hints, and follow-up hints.

This spec does not make the food DB a product truth owner. Final product decisions still belong downstream to Manager Pass 2 synthesis, B2 final mapping, guard, mutation boundary, ledger, and same-truth layers.

## Ownership Boundaries

This spec owns:

- food knowledge metadata asset families
- food mention and sense resolution metadata
- metadata-to-packet mapping guidance
- seed knowledge asset boundaries for Wave 1 Phase B-2

It does not own:

- B2 packet truth levels, source quality labels, exactness guard, or packet invariants
- route policy between generic lookup, exact DB, web candidate, listed-item lookup, or ask-first
- approved product-semantic decisions
- L2 canonical objects or L2A enum values
- Manager schema, runtime tool schema, mutation, ledger writes, or same-truth projection

Owner relationships:

- `WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md` owns packet-level invariants and synthesis gate behavior.
- `WAVE_1_EVIDENCE_PATH_SELECTION_MATRIX.md` owns evidence path route policy.
- `WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER.md` owns approved and pending product-semantic decisions.
- `L2_DATA_STATE_SPEC.md` and `L2A_DATA_DICTIONARY_SPEC.md` own committed canonical product state and enum legality.

## Food Semantics DB Decision

```yaml
food_semantics_db_decision:
  db_is_not_just_nutrition_values: true
  db_may_contain_food_semantics: true
  db_may_contain_evidence_posture_hints: true
  db_may_contain_uncertainty_and_followup_hints: true
  db_must_not_own_product_truth: true
  db_must_not_decide_logged_draft_unresolved: true
  db_must_not_decide_mutation: true
```

## Non-Goals

This spec is not:

- a full production nutrition DB
- a production ingestion pipeline
- a memory, recommendation, rescue, proactive, or UI spec
- a canonical L2 data model
- a Manager schema
- a mutation or ledger spec
- a web runtime activation spec
- a DB loader, migration, or admin workflow spec
- a replacement for the B2 evidence packet contract

## Knowledge Asset Types

Wave 1 Phase B-2 may define seed read-only assets in these families:

```yaml
knowledge_asset_types:
  - generic_food_anchors
  - exact_item_cards_seed
  - meal_templates
  - food_mention_semantics
  - portion_anchors
  - alias_map
```

These assets may support B2 packetization, but they must remain upstream evidence metadata.

## Generic Food Anchor Metadata

Generic food anchors describe common stable foods or stable-enough food families.

Allowed shape:

```yaml
generic_food_anchor:
  food_id: string
  display_name: string
  aliases:
    - string
  food_family: string
  composition_type: stable_single_item | stable_base_variable_modifiers | known_structure_meal
  default_portion:
    label: string
    grams: number | null
  kcal:
    likely: number | null
    range: [number, number] | null
  macro_candidate:
    protein_g: number | null
    carbs_g: number | null
    fat_g: number | null
  uncertainty_drivers:
    - string
  clarification_policy_hint:
    posture: optional_refinement | recommended_refinement | ask_first
    followup_type: portion | modifier | composition | brand | none
    suggested_question: string | null
```

Generic anchors may become generic DB candidate evidence when they carry nutrition anchor payload. They must not claim exact match posture.

## Meal Template Metadata

Meal templates describe combination meals, known meal structures, vendor/category shorthand, or self-selected baskets.

Allowed shape:

```yaml
meal_template:
  template_id: string
  display_name: string
  composition_type: known_structure_meal | self_selected_basket | vendor_category_shorthand
  requires_listed_items: boolean
  typical_components:
    - string
  estimation_policy_hint:
    posture: estimable_with_uncertainty | itemize_listed_components | ask_first_unresolved
    reason: string
  suggested_followup: string | null
```

Example:

```yaml
template_id: taiwan_fried_snack_basket
display_name: 鹽酥雞攤 / 炸物自選籃
composition_type: self_selected_basket
requires_listed_items: true
typical_components:
  - 鹽酥雞
  - 甜不辣
  - 米血
  - 四季豆
  - 地瓜
  - 魷魚
  - 百頁豆腐
  - 雞排
estimation_policy_hint:
  posture: ask_first_unresolved
  reason: composition_unknown
suggested_followup: 你這份鹽酥雞裡面有哪些品項？大概各多少？
```

## Food Mention And Sense Resolution

Food mention semantics resolve a surface food term into possible evidence targets. They are not a one-way alias map.

Allowed shape:

```yaml
food_mention_semantics:
  surface: string
  locale_context: string
  possible_senses:
    - sense_id: string
      target_type: generic_food_anchor | meal_template | exact_item_card | listed_basket_itemization
      target_id: string
      cues:
        prefer_when:
          - string
      evidence_posture_hint: estimable_with_optional_refinement | ask_first_unresolved | estimable_itemized
  cue_examples:
    status: illustrative_not_exhaustive
```

Example:

```yaml
surface: 鹽酥雞
locale_context: Taiwan
possible_senses:
  - sense_id: fried_chicken_bites_item
    target_type: generic_food_anchor
    target_id: fried_chicken_bites_taiwan
    cues:
      prefer_when:
        - portion_cue_present
        - user_says_一份
        - user_says_一包
        - user_says_小份_or_大份
    evidence_posture_hint: estimable_with_optional_refinement

  - sense_id: fried_snack_vendor_basket
    target_type: meal_template
    target_id: taiwan_fried_snack_basket
    cues:
      prefer_when:
        - vendor_context_present
        - meal_context_without_item_list
        - user_says_買鹽酥雞
        - user_says_晚餐吃鹽酥雞
        - user_says_宵夜吃鹽酥雞
    evidence_posture_hint: ask_first_unresolved

  - sense_id: listed_fried_snack_basket
    target_type: listed_basket_itemization
    target_id: taiwan_fried_snack_basket
    cues:
      prefer_when:
        - listed_items_present
    evidence_posture_hint: estimable_itemized
cue_examples:
  status: illustrative_not_exhaustive
```

## Exact Item Card Seed Metadata

Exact item cards describe known brand or menu items. In Wave 1 Phase B-2, real exact DB seeds may remain empty unless separately approved.

Allowed shape:

```yaml
exact_item_card_seed:
  brand: string
  item_name: string
  variant: string | null
  serving: string
  kcal: number | null
  macro:
    protein_g: number | null
    carbs_g: number | null
    fat_g: number | null
  source:
    source_id: string
    source_quality: internal_exact | official | brand_menu | trusted_database
    last_verified_at: string | null
  sibling_variants:
    - string
  disambiguation_notes:
    - string
```

Exact cards must support sibling, variant, size, and serving rejection. A brand page or official-looking source is not enough by itself.

## Packetizer Mapping

This spec does not redefine the B2 packet contract. It only describes how metadata may map into existing packet fields.

```yaml
metadata_field_to_packet:
  target_type: source_type_or_match_type_hint
  evidence_posture_hint: truth_level_hint_or_rule_hint
  kcal_or_range: candidate_evidence_fields
  uncertainty_drivers: uncertainty_reason
  typical_components: followup_context
```

Allowed packet truth levels remain:

- `candidate`
- `hint`
- `rule_hint`

Metadata may influence B2 packetizer inputs and Manager Pass 2 synthesis inputs. B2 final mapping may observe the downstream synthesized result, but this spec does not change final mapping behavior.

## Forbidden Drift Rules

- Food knowledge DB must not output `logged`, `draft`, or `unresolved`.
- Food knowledge DB must not output `canonical_write_allowed`.
- Food knowledge DB must not output `ledger_mutation_allowed`.
- Generic DB must not claim exact.
- Meal template must not estimate a self-selected basket without listed items.
- Food mention semantics must not be reduced to a one-way alias map.
- Taiwan semantic skill must not become a standalone runtime packet source unless explicitly approved.
- Clarify-only semantic support must not be emitted as `GenericDbCandidatePacket`.
- Web candidate must not become exact truth.
- Tavily snippet must not be used directly as nutrition truth.
- Packetizer must not output `final` truth.
- Packetizer must not output `mutation_result`.
- Manager-visible tool schema must not be changed by this metadata spec.

## Seed And Future Fixture Cases

These cases should be represented either in seed metadata, future fixture lists, or both:

- `我吃了一顆茶葉蛋`
- `我喝了一杯珍珠奶茶`
- `我吃了一個便當`
- `我吃了滷味`
- `我吃了豆干、海帶、貢丸的滷味`
- `我吃了一份鹽酥雞`
- `我買了鹽酥雞`
- `我晚餐吃鹽酥雞`
- `我吃了鹽酥雞，有甜不辣、米血、四季豆`
- `珍珠奶茶多少熱量？`
- `迷客夏珍珠紅茶拿鐵`
- `松屋特盛牛丼`

Salt crispy chicken contrast:

```yaml
salt_crispy_chicken_contrast:
  single_item:
    input: 我吃了一份鹽酥雞
    expected_resolution: generic_food_anchor
    expected_posture: estimable_with_optional_refinement

  vendor_basket:
    input: 我晚餐吃鹽酥雞
    expected_resolution: meal_template_self_selected_basket
    expected_posture: ask_first_unresolved

  listed_basket:
    input: 我吃了鹽酥雞，有甜不辣、米血、四季豆
    expected_resolution: listed_basket
    expected_posture: item_level_generic_lookup
```
