# Benchmark V2 Exact Coverage Matrix

This matrix is the stopping gate for single-turn deep-dives before multi-turn work. It classifies the v2 exact family by mechanism root cause instead of continuing blind prompt tuning.

## Classification labels
- `data_missing`: no exact item card for the expected chain item or bundle component
- `alias_missing`: exact card exists, but common user phrasing does not map cleanly to the stored aliases
- `recall_miss`: exact card exists, but exact-only retrieval does not surface it reliably
- `gate_too_strict`: exact card exists and retrieval gets close, but identity gate rejects the candidate too aggressively
- `bundle_partial`: some exact bundle components exist, but the bundle cannot finalize exactly because one or more components are missing

## Current matrix
| Case | Target item | Current classification | Notes |
| --- | --- | --- | --- |
| `case_001_mos_pork_burger` | MOS pork burger | `recall_miss` | `摩斯豬排堡` exact card exists in [`exact_item_cards_tw.json`](C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/knowledge/exact_item_cards_tw.json), so remaining issue is exact-path surfacing and finalize policy, not generic prior quality. |
| `case_002_mos_japanese_pork_sandwich` | MOS Japanese pork sandwich | `recall_miss` | `摩斯漢堡 日式豬排三明治` exists in exact cards; the failure should be treated as exact retrieval/finalize instability, not missing knowledge. |
| `case_003_mos_breakfast_combo` | MOS pork burger + nuggets + black tea | `bundle_partial` | `摩斯豬排堡` and `摩斯雞塊 (4個)` exist, but the exact bundle is incomplete or not finalized consistently. Medium black tea coverage appears incomplete, so this is not just a prompt issue. |
| `case_004_711_tuna_riceball` | 7-11 tuna riceball | `data_missing` | No exact card title hit was found for `雙蔬鮪魚飯糰`. |
| `case_005_711_smoked_chicken_sandwich` | 7-11 smoked chicken sandwich | `data_missing` | Exact candidate pollution is fixed; the remaining problem is lack of a correct exact card for `燻雞總匯鮮蔬三明治`. |
| `case_006_711_oyakodon` | 7-11 oyakodon | `data_missing` | Only generic `雞肉親子丼` from another producer is present; the chain-specific exact item is missing. |
| `case_007_familymart_herb_chicken_riceball` | FamilyMart herb chicken riceball | `data_missing` | No exact card title hit was found for `香草雞腿排飯糰`. |
| `case_008_familymart_sausage_cutlet_bento` | FamilyMart sausage cutlet bento | `data_missing` | No exact card title hit was found for `香腸腿排雙拼便當`. |
| `case_009_familymart_fitness_g_box` | FamilyMart fitness G box | `data_missing` | No exact card title hit was found for `健身G肉餐盒`. |

## Implications
- Do not keep patching the decision or nutrition prompts for `case_004` to `case_009`. They are primarily exact coverage issues.
- `case_001` to `case_003` should be treated as exact finalize / bundle handling issues because the source data exists.
- The next exact-family iteration should prioritize:
  1. exact item card ingestion for 7-11 / FamilyMart branded convenience-store items
  2. alias coverage for common user phrasing
  3. bundle finalization for multi-item exact combos
