# Text Meal DB Wide Research v3: Exact Item Foundation

## Summary

`v3` opens the first exact-item wave on top of the curated source registry and the reviewed base nutrition layer.

Goal:

- build high-frequency `Exact Item DB` candidates
- preserve item identity and variant identity
- prefer official nutrition and official product/menu pages
- keep retailer pages as fallback only

## Scope

`v3` covers six exact-item shards:

1. `mcdonalds_tw`
2. `seven_eleven_tw`
3. `familymart_tw`
4. `packaged_beverages_tw`
5. `drink_chains_tw`
6. `other_fast_food_tw`

These shards are chosen because they align with current `v10.4` pain points:

- branded items
- packaged items
- chain-menu items
- variant-sensitive drink items

## Source Policy

- Prefer `P0` official nutrition/menu/product pages.
- Use `P1` retailer pages only when they are the cleanest reusable SKU-level fallback.
- Do not merge sibling variants.
- Do not produce a record when exact identity is still ambiguous.

## Runtime Skeleton

- [exact_item_v3.py](/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/data_build/wide_research/exact_item_v3.py)
- [scaffold_exact_item_v3_run.py](/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/scaffold_exact_item_v3_run.py)
- [validate_exact_item_v3_outputs.py](/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/validate_exact_item_v3_outputs.py)
- [aggregate_exact_item_v3.py](/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/aggregate_exact_item_v3.py)

## Success Criteria

- McDonald's Taiwan items should produce reusable exact records instead of only exclusions.
- 7-ELEVEN and FamilyMart should produce exact packaged or ready-meal records where identity is stable.
- Pocari and high-frequency packaged beverages should keep variant identity stable.
- Drink-chain shards should encode size or variant tokens rather than collapsing siblings.
- Validation should stay clean on schema, duplicate IDs, missing outputs, and illegal source types.
