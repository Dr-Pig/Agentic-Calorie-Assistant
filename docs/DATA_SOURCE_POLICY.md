# Text Meal Canary 資料來源政策

## Summary

這份文件定義資料庫建置時，哪些來源可用、如何分級、怎麼驗證，以及哪些來源不能直接升格成正式 truth source。

## Source tiers

### P0: 權威 / 第一方

優先順序最高。

適用：

- Base Nutrition DB
- Exact Item DB

可接受來源：

- 政府營養資料
- 官方品牌商品頁
- 官方菜單 / nutrition page
- 產品包裝標示

要求：

- 可追溯來源 URL 或人工錄入來源描述
- 有清楚 serving basis
- 有明確 variant / 規格時不可省略

### P1: 高可信公開結構化來源

只在沒有 P0 時使用。

適用：

- Exact Item DB 補洞
- Base Nutrition DB 次級補充

可接受來源：

- 品牌公開商品規格頁
- 可信零售平台上的官方商品頁
- 高可信連鎖 FAQ / menu page

要求：

- 必須保留來源與驗證日期
- 不可把 P1 標成官方 truth
- 若 variant 或 serving 不清，不能直接進 exact item canonical DB

### P2: 內部整理 pattern knowledge

只用於 Meal Pattern DB。

適用：

- 高模糊餐型
- 在地料理結構知識
- uncertainty priors

可接受來源：

- 人工整理的餐型結構
- 高頻在地料理 pattern
- 內部 curated notes

要求：

- 必須標 `source_type=internal_pattern`
- 不可偽裝成 exact nutrition truth
- 僅能作 baseline / prior / checklist / driver hints

## 不可直接升格成正式 DB 的來源

以下現有檔案只能當參考素材：

- `app/knowledge/exact_item_cards_tw.json`
- `app/knowledge/meal_templates_tw.json`
- `app/knowledge/risk_gate_packets_tw.json`
- `../line-liff-calorie-helper-main/knowledge/*.json`

可用方式：

- 題目清單參考
- alias 靈感
- bootstrap 對照
- gap discovery

不可用方式：

- 直接視為正式 truth source
- 不經 provenance 補齊就進 canonical DB
- 不經 schema / source / variant 驗證就成為 runtime DB

## Verification rules

每筆正式 DB record 至少要有：

- `source_type`
- `source_name`
- `source_url` 或明確來源說明
- `confidence`
- `last_verified_at`

驗證要求：

- serving basis 清楚
- exact item 的 variant 不模糊
- nutrition 與 kcal 不明顯矛盾
- alias 不與 sibling variant 混淆

## Refresh policy

- P0 / P1 exact item 資料可定期 refresh
- P2 meal patterns 以人工 review 為主
- 若來源失效或品牌改版，不可 silent overwrite
- 需保留 stale / re-verified 記錄能力
