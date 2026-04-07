# Text Meal DB Wide Research v2.2

## Scope

`v2.2` covers **Base Nutrition shards** only.

It runs after `Source Registry v1` has been reviewed and curated. `v2.2` must only use allowed `base_nutrition` sources from the formal registry:

- `tw-tfda-food-nutrition-composition-dataset`
- `tw-tfda-food-nutrition-database-portal`

`v2.2` does not perform exact-item extraction and does not build meal-pattern records.

## Goal

Produce strict JSON candidate records for:
- generic/common food grounding
- quantity normalization
- component-level priors used by the `v10.4` structured path

The first wave should cover:

- white rice
- purple rice
- noodles
- yi noodles
- pasta
- egg
- tea egg
- chicken breast
- beef
- pork
- cabbage
- soy milk
- sweet potato
- sesame paste
- peanut butter
- sweet chili sauce
- dongquan chili sauce
- olive oil
- milk cap base

## Shards

`v2.2` uses 6 ingredient-family shards:

1. `grains_and_rice`
2. `noodles_and_pasta`
3. `proteins_eggs_and_meats`
4. `vegetables_roots_and_basic_produce`
5. `sauces_spreads_and_oils`
6. `beverages_and_liquid_basics`

## Output schema

Each child must output one strict JSON object:

```json
{
  "schema_version": "base-nutrition.v2.2",
  "shard_id": "string",
  "records": [
    {
      "id": "string",
      "title": "string",
      "aliases": ["string"],
      "category": "string",
      "serving_basis": {
        "unit_type": "g | ml | piece | bowl | cup | tbsp | tsp",
        "amount": 0,
        "label": "string"
      },
      "nutrition": {
        "protein_g": 0,
        "carb_g": 0,
        "fat_g": 0,
        "kcal": 0,
        "sodium_mg": null
      },
      "portion_equivalents": [
        {
          "label": "string",
          "grams": 0,
          "ml": null,
          "pieces": null
        }
      ],
      "source_type": "government_nutrition | verified_reference",
      "source_name": "string",
      "source_url": "string",
      "confidence": "high | medium",
      "last_verified_at": "YYYY-MM-DD",
      "notes": "string"
    }
  ],
  "excluded_candidates": [
    {
      "name": "string",
      "reason": "string"
    }
  ]
}
```

## Validation rules

- `schema_version` must be `base-nutrition.v2.2`
- no missing outputs
- no empty outputs
- JSON only
- `id` must be kebab-case
- `source_type` limited to `government_nutrition` or `verified_reference`
- `confidence` limited to `high` or `medium`
- `unit_type` limited to `g | ml | piece | bowl | cup | tbsp | tsp`
- macro fields and `kcal` must be numeric and non-negative
- `last_verified_at` must be `YYYY-MM-DD`
- duplicate `id` across shards is invalid

## Runtime artifacts

`v2.2` keeps the `v2.1` canonical row selection rule and adds one narrow exception:

- only the `sauces_spreads_and_oils` shard may use a `verified_reference` fallback
- fallback is allowed only when TFDA cannot support a defensible canonical row
- acceptable fallback sources are:
  - official brand product pages
  - official retailer product pages
  - verified packaging labels
- `notes` must explicitly disclose the fallback

Selection policy:

- prefer plain, unsauced, baseline edible states
- prefer staple rows over prepared dishes
- for generic terms with multiple varieties, choose a defensible Taiwanese default and record that choice in `notes`
- exclude only when no defensible canonical row can be selected from the allowed sources

`v2.2` should aggregate into:

- `data_build/normalized/base_nutrition_db.candidates.json`

This remains a candidate build artifact until human review confirms canonical merge decisions.
