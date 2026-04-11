# Base Nutrition Review 2026-03-30

## Summary

This review converts `base-nutrition-v2-2-20260330-094105` into the first formal curated runtime file:

- [base_nutrition_db.json](/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/knowledge/base_nutrition_db.json)

Result:

- `18` accepted runtime records
- `1` deferred candidate: `milk cap base`
- `39` TFDA increment records merged after the first runtime cut
- `57` total runtime records after the TFDA increment merge

## Review Principles

- Keep only reusable baseline foods that fit the `Base Nutrition DB` role.
- Normalize noisy candidate IDs into stable runtime IDs.
- Replace garbled aliases with clean English and common Traditional Chinese labels.
- Preserve provenance exactly:
  - government rows stay `government_nutrition`
  - Dongquan stays `verified_reference`
- Do not force records that still lack a clean reusable baseline.

## Accepted Groups

### Grains and starches

- `white-rice-cooked`
- `purple-rice-dry`
- `noodles-dry-plain`
- `yi-noodles-dry`
- `pasta-dried-plain`

### Proteins

- `egg-whole`
- `tea-egg`
- `chicken-breast-skinless`
- `beef-lean-baseline`
- `pork-lean-baseline`

### Produce and beverages

- `cabbage-raw`
- `sweet-potato-yellow-flesh`
- `soy-milk`

### Sauces, spreads, and oils

- `sesame-paste`
- `peanut-butter`
- `sweet-chili-sauce`
- `dongquan-chili-sauce`
- `olive-oil`

## Deferred

### `milk cap base`

Reason:

- `v2.2` still did not find a clean enough, reusable, officially verifiable baseline.
- This is a real gap, not a formatting omission.
- It should be revisited later through either a stronger official beverage-chain source or a clearly scoped verified-reference policy.

## TFDA Increment Merge

This follow-up review pulled a narrow, reusable subset from:

- `raw_data/staging/tfda_base_review_candidates.json`

Only common base-food anchors were merged. The goal was to improve generic grounding for staples, ingredients, vegetables, mushrooms, nuts, and fruit without dumping the full `1000` TFDA staging rows into runtime.

### Accepted TFDA groups

- Grains and flours:
  - `barley-kernels`
  - `barley-flakes`
  - `millet-dry`
  - `cake-flour`
  - `all-purpose-flour`
  - `bread-flour`
  - `whole-wheat-flour`
  - `sweet-corn`
- Starches and legumes:
  - `yam`
  - `potato`
  - `red-bean-dry`
  - `mung-bean-dry`
  - `edamame-kernels`
  - `soybeans-dry`
- Nuts and seeds:
  - `walnut`
  - `pistachio`
  - `cashew`
  - `chia-seeds`
  - `white-sesame`
  - `black-sesame`
- Mushrooms:
  - `wood-ear-mushroom`
  - `white-fungus`
  - `shiitake-mushroom`
  - `king-oyster-mushroom`
  - `enoki-mushroom`
- Vegetables:
  - `burdock-root`
  - `carrot`
  - `daikon`
  - `white-onion`
  - `cauliflower`
  - `cucumber`
  - `napa-cabbage`
  - `tomato`
- Fruits:
  - `papaya`
  - `kiwi`
  - `banana`
  - `guava`
  - `apple`
  - `avocado`

### Merge policy

- Preserve the runtime `base_nutrition_db.json` shape instead of introducing a second TFDA-only schema.
- Mark `protein_g`, `carb_g`, `fat_g`, and `sodium_mg` as `null` when this review only verified `kcal`.
- Normalize all TFDA increment records to `100 g edible portion` anchors for runtime consistency.
- Keep provenance explicit:
  - `source_type = government_nutrition`
  - `source_name = TFDA Food Nutrition 2024 Workbook (reviewed extract)`
  - `source_url = https://data.gov.tw/dataset/102756`

### Explicit non-goals

- Do not treat the full TFDA staging export as runtime-ready.
- Do not fabricate missing macro values.
- Do not overwrite stronger existing runtime records such as `soy-milk` or other fully populated anchors.
