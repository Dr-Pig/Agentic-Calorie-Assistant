# Text Meal Next Phase Progress

## Status Summary
- Last updated: `2026-03-31`
- Overall phase: `Grounding build in progress`
- Current focus:
  - TFDA base nutrition enrichment into macro-complete runtime schema
  - Search guard so web evidence cannot override strong local exact truth
  - Durable handoff docs for Antigravity continuation
  - Phase 4 Follow-up Enhancement (Ramen missing slot policy) complete
  - Retrieval watchtower expansion across packaged drinks, household brands, and chain menu items

## Completed
### Stage And Trace
- Stage map documented in [TEXT_MEAL_STAGE_MAP_AND_TRACE.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TEXT_MEAL_STAGE_MAP_AND_TRACE.md)
- Trace contract includes:
  - `match_confidence`
  - `match_path`
  - `grounding_contradiction`
- Evaluator updated so strong exact truth wins are not incorrectly downgraded by weaker follow-up signals

### Exact Truth Protection
- Local exact truth dominance added for evaluator and candidate selection
- Alias and variant normalization already landed in runtime grounding
- External workspace exact-item import completed

### External Exact DB Import
- Source workspace:
  - `C:\Users\User\Desktop\減肥駐守`
- Import report:
  - [.logs/external_workspace_import_report.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/.logs/external_workspace_import_report.json)
- Runtime result:
  - initial import: `16 -> 553`
  - imported exact-item records in first pass: `537`

### Exact DB Expansion Wave 2
- Importer expanded to include:
  - `newtaipei_brand_candidates.json`
  - `starbucks_food_extracted.json`
- Updated importer:
  - [import_external_workspace_candidates.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/import_external_workspace_candidates.py)
- New import report:
  - [.logs/external_workspace_import_report_v2.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/.logs/external_workspace_import_report_v2.json)
- Runtime result:
  - `exact_item_cards_tw.json`: `553 -> 9061`
  - additional inserted or updated exact-item records: `8508`
- Notes:
  - `newtaipei_brand_candidates.json` contributed the large manufacturer and packaged-brand expansion
  - `starbucks_food_extracted.json` was imported as a rescued OCR-derived exact-item source
  - alias cleanup added:
    - corporate brand short-name aliases such as `全家`, `台酒`, `臺酒`, `星巴克`
    - packaged-title prefix stripping for exact matching

### Retrieval Sanity Wave
- Artifact:
  - [.logs/retrieval_sanity_wave_20260331.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/.logs/retrieval_sanity_wave_20260331.json)
- Scope:
  - `Starbucks food OCR` exact retrieval
  - `newtaipei brand exact` retrieval
- Result:
  - `12 / 12 passed`
  - `Starbucks food OCR`: `6 / 6 passed`
  - `newtaipei brand exact`: `6 / 6 passed`
- Meaning:
  - the `9061` exact-card expansion did not dirty the tested exact-ranking paths after alias cleanup

### Retrieval Sanity Wave Extended
- Runner:
  - [run_retrieval_sanity_wave.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/run_retrieval_sanity_wave.py)
- Fixture:
  - [retrieval_sanity_cases.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/tests/fixtures/retrieval_sanity_cases.json)
- Artifact:
  - [.logs/retrieval_sanity_wave_extended_20260331.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/.logs/retrieval_sanity_wave_extended_20260331.json)
- Scope:
  - `convenience_store_packaged_drinks`
  - `household_packaged_brands`
  - `chain_menu_food_items`
- Result:
  - `18 / 18 passed`
  - `convenience_store_packaged_drinks`: `6 / 6 passed`
  - `household_packaged_brands`: `6 / 6 passed`
  - `chain_menu_food_items`: `6 / 6 passed`
  - top-hit confidence: `14 high`, `4 medium`
- Meaning:
  - the broadened `9061` exact-card runtime still retrieves the expected exact truth cleanly across packaged retail and chain-menu buckets
  - this artifact is now the reusable retrieval watchtower baseline for future DB expansion waves

### Retrieval Sanity Wave V3
- Runner:
  - [run_retrieval_sanity_wave.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/run_retrieval_sanity_wave.py)
- Fixture:
  - [retrieval_sanity_cases.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/tests/fixtures/retrieval_sanity_cases.json)
- Artifact:
  - [.logs/retrieval_sanity_wave_v3_20260331.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/.logs/retrieval_sanity_wave_v3_20260331.json)
- Scope:
  - `convenience_store_coffee_variants` (CITY CAFE shorthand queries)
  - `packaged_snacks_desserts` (manufacturer-level brand queries)
  - `chain_beverage_customizations` (Starbucks hot/cold beverage variants)
- Result:
  - `36 / 36 passed` (18 old + 18 new)
  - `convenience_store_coffee_variants`: `6 / 6 passed`
  - `packaged_snacks_desserts`: `6 / 6 passed`
  - `chain_beverage_customizations`: `6 / 6 passed`
  - all prior buckets: `18 / 18 passed` (no regression)
  - top-hit confidence: `33 high`, `3 medium`
- Code changes:
  - `knowledge_packets.py` `_match_metadata()`: extended brand matching to detect shorthand brand tokens (e.g., `義美` matching `義美食品股份有限公司`) via substring matching against brand keys
  - `knowledge_packets.py` `_match_metadata()`: added CJK substring fallback for `brand_plus_core_token` path so query tokens like `豆花` match inside longer CJK title tokens like `義美非基因改造豆花`
- Meaning:
  - the retrieval watchtower now covers 6 buckets across the full noise spectrum
  - brand shorthand queries are reliably resolved to the correct manufacturer entity
  - hot/cold beverage disambiguation is a known limitation (single-char token `冰`/`熱` filtered by tokenizer); both variants score identically and both are correct exact-truth cards

### Eval Wave Runner (Phase 3 Complete)
- Runner:
  - `run_eval_wave.py`
  - supports `--mode eval` (real or `--mock`) and `--mode retrieval`
- Fixtures:
  - `eval_cases.json` (10 cases covering 6 buckets: common, exact branded, buffet, drink custom, ramen, home cooked)
- Tests:
  - `test_eval_runner.py` (added full unit test suite for evaluator and mock LLM)
- Result:
  - We now have an offline batch evaluator capable of running end-to-end tests without LLM calls (mock) or full tests (real) and outputting wave summaries.
  - Summaries include layer failure rates, exact truth hit rates, and follow-up precision/recall for driving Phase 4-9 metric improvements.

### TFDA Base Enrichment
- New script:
  - [build_tfda_base_from_candidates.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/build_tfda_base_from_candidates.py)
- New tests:
  - [test_build_tfda_base_from_candidates.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/tests/test_build_tfda_base_from_candidates.py)
- Inputs:
  - [.logs/tfda_base_candidates_tmp.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/.logs/tfda_base_candidates_tmp.json)
  - [.logs/FDA_food_nutrition_2024.xlsx](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/.logs/FDA_food_nutrition_2024.xlsx)
- Result:
  - `records_seen = 1000`
  - `records_enriched = 1000`
  - `records_unmatched = 0`
  - report: [.logs/tfda_base_enriched_report.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/.logs/tfda_base_enriched_report.json)
- Runtime merge result:
  - `base_nutrition_db.json`: `57 -> 1057`
- Integration:
  - `knowledge_packets.py` now parses exact `protein_g, carb_g, fat_g, sodium_mg` for `macro_completeness='complete'`
  - `_knowledge_context` in `text_meal.py` now explicitly exposes exact macros to the Layer 3 LLM (e.g. `P:Xg/C:Yg/F:Zg/Na:Wmg`) natively for estimation consistency

## In Progress
### Search Guard Tightening
- Runtime code now being tightened so:
  - local exact truth has higher tie-break priority than search evidence
  - strong local exact truth blocks search from becoming the dominant answer source
  - prompt-level evidence hierarchy explicitly says search is supplemental only
- Main file:
  - [text_meal.py](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/usecases/text_meal.py)
- Follow-up fix:
  - `best_answer_source` labeling now relabels search-assisted clarification outcomes to `clarify_user` instead of `with_search_evidence`
- Validation artifact refreshed:
  - [.logs/planner_off_branded_drink_validation_20260331.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/.logs/planner_off_branded_drink_validation_20260331.json)
- Current planner-off branded drink validation result:
  - `五十嵐四季春珍波椰` -> `reference_card`, `db_hit_type=exact_truth`, `north_star=win`
  - `五十嵐珍珠奶茶` -> `clarify_user`, `db_hit_type=reference_anchor`, `north_star=win`

## Remaining
1. Expand exact-item coverage for the still-blocked external shards only if their source quality improves.
2. Consider adding hot/cold disambiguation logic for single-char CJK tokens in the tokenizer.

## Blocked Or Deferred
- These external exact-item sources were intentionally not imported yet:
  - `city_prima_candidates.json`
  - `dominos_candidates.json`
  - `familymart_letscafe_candidates.json`
  - `starbucks_beverage_candidates.json`
  - `starbucks_food_candidates.json`
- Reason:
  - source quality or normalization readiness was not sufficient for safe runtime import
- Still blocked as of `2026-03-31`:
  - `city_prima_candidates.json`: homepage-only source
  - `dominos_candidates.json`: homepage-only source
  - `familymart_letscafe_candidates.json`: homepage-only source
  - `starbucks_beverage_candidates.json`: image-based source not yet normalized into trusted structured records
  - `starbucks_food_candidates.json`: raw image-based shard replaced by rescued OCR extract import, but the original raw shard itself remains blocked

## Current Runtime Counts
- `exact_item_cards_tw.json`: `9061`
- `base_nutrition_db.json`: `1057`
- `meal_templates_tw.json`: unchanged
- `risk_gate_packets_tw.json`: unchanged

## If The Session Ends Here
- Pick up from [TEXT_MEAL_NEXT_PHASE_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/TEXT_MEAL_NEXT_PHASE_PLAN.md)
- Re-run:
  - `.\.venv\Scripts\python.exe -m pytest .\tests\test_build_tfda_base_from_candidates.py .\tests\test_text_meal_v103.py -q`
- Then validate:
  - planner-off branded drink case with strong local exact truth
  - planner-off branded drink case with only weak brand anchor
