# Text Meal Canary 資料庫建置計畫

## Summary

這份計畫定義 `text-meal-canary` 在 `v10.4` 路徑下的 **Greenfield 資料庫建置方式**。

原則固定如下：

- 不直接沿用舊 `knowledge/*.json` 當正式資料庫
- 舊檔只作參考素材，不作 truth source
- 資料庫必須服務目前主路徑：
  1. structured baseline
  2. local retrieval
  3. search fallback
  4. evidence pass / retry
  5. renderer
- 資料庫提供的是 evidence、priors、identity protection，不是規則引擎

## 資料庫分層

### 1. Base Nutrition DB

用途：

- generic/common food baseline
- quantity normalization
- macro / kcal grounding
- component-level nutrition priors

內容：

- 原型食物
- 單一食材
- 常見調味料 / 油脂
- 重量 / 容量 / piece / bowl / cup 對照

必備欄位：

- `id`
- `title`
- `aliases`
- `category`
- `serving_basis`
- `nutrition`
- `portion_equivalents`
- `source_type`
- `source_name`
- `source_url`
- `confidence`
- `last_verified_at`
- `notes`

### 2. Exact Item DB

用途：

- local retrieval 主庫
- item identity protection
- variant guard
- product-aware evidence merge

內容：

- 品牌商品
- 超商 SKU
- 連鎖固定餐點
- 連鎖飲料固定品項
- 有明確 variant 的官方 item

必備欄位：

- `id`
- `brand`
- `title`
- `aliases`
- `category`
- `variant_tokens`
- `serving_basis`
- `nutrition`
- `common_components`
- `official_serving_text`
- `source_type`
- `source_name`
- `source_url`
- `confidence`
- `last_verified_at`
- `notes`

### 3. Meal Pattern DB

用途：

- 高模糊餐型 baseline
- component priors
- uncertainty drivers priors
- structure-only grounding，不偽裝成 exact nutrition truth

內容：

- 自助餐
- 便當
- 滷味
- 火鍋
- 早餐店組合餐
- 在地常見餐型

必備欄位：

- `id`
- `title`
- `aliases`
- `category`
- `trigger_keywords`
- `trigger_patterns`
- `typical_components`
- `baseline_kcal`
- `major_uncertainty_drivers`
- `component_checklist`
- `source_type`
- `source_name`
- `source_url`
- `confidence`
- `last_verified_at`
- `notes`

## Source Policy

### P0: 權威 / 第一方

優先用於 Base Nutrition DB 與 Exact Item DB。

來源類型：

- 政府營養資料
- 官方品牌商品頁
- 官方菜單 / nutrition page
- 產品包裝標示

### P1: 高可信結構化公開來源

只在沒有 P0 時使用。

來源類型：

- 品牌公開商品規格頁
- 可信零售平台上的官方商品頁
- 高可信連鎖 FAQ / menu page

### P2: 內部整理 pattern knowledge

只用於 Meal Pattern DB。

來源類型：

- 人工整理的餐型結構
- 高頻在地料理的結構知識
- 不作 exact nutrition truth

強規則：

- Base / Exact 不可把 P2 內部估值偽裝成官方真值
- Meal Pattern 只作 prior / baseline，不作 exact nutrition claim

## Build Pipeline

### Stage 1: Source Registry

建立 source registry，記錄：

- 來源名稱
- 來源分類（P0 / P1 / P2）
- 適用 DB 層
- 驗證方式
- refresh policy

### Stage 2: Raw Ingestion

每個來源先轉成 raw records，不直接進 production DB。

輸出：

- `base_nutrition_raw`
- `exact_items_raw`
- `meal_patterns_raw`

### Stage 3: Canonicalization

把 raw records merge 成 canonical DB。

規則：

- exact item 不可因模糊相似而合併
- sibling variants 必須拆開
- alias 與 variant token 顯式存放
- source metadata 保留

### Stage 4: Validation

檢查：

- schema validity
- duplicate IDs
- alias collisions
- nutrition / kcal obvious impossible values
- variant ambiguity
- source metadata completeness

### Stage 5: Runtime Artifacts

從 canonical DB 再產出 runtime artifacts：

- local retrieval docs
- exact lookup tables
- alias maps
- variant maps
- meal pattern trigger maps

## 與 v10.4 路徑的整合

### `primary_structured_initial`

- Base Nutrition DB 提供 generic nutrition grounding
- Meal Pattern DB 提供高模糊餐型 priors
- 模型仍輸出 baseline structured answer

### `local_retrieval`

- 主吃 Exact Item DB
- 次吃 Meal Pattern DB
- Base Nutrition DB 只作 generic priors 與 quantity support

### `with_local_knowledge`

- Exact Item：更新 item-specific nutrition 與 variant info
- Meal Pattern：更新 baseline 結構與 uncertainty drivers
- Base Nutrition：補 component-level nutrition

### `search fallback`

- 只有 local retrieval 不足時才開
- search evidence 只作補強
- 不可蓋掉 exact item identity
- variant consistency 規則要保留

### `retry`

- retry 不能重新猜一套
- 只能在 current structured answer + evidence 上修補缺欄位或 driver/follow-up 問題

## 建置波次

### Wave 1: Base Nutrition Foundation

先建 base 底座。

優先內容：

- 白飯 / 紫米飯 / 麵條 / 意麵 / 義大利麵
- 雞蛋 / 茶葉蛋 / 雞胸 / 牛肉 / 豬肉 / 高麗菜 / 豆漿 / 地瓜
- 麻醬、花生醬、甜辣醬、東泉辣椒醬、橄欖油、奶蓋基底
- 單位換算與 portion anchors

成功標準：

- generic/common food baseline 更穩
- 大量靠模型常識硬猜的 component 基底減少

### Wave 2: Exact Item Foundation

先建高頻 brand / package / chain item。

優先內容：

- 麥當勞
- 7-11
- 全家
- 寶礦力
- 老賴紅茶 / 高頻手搖飲
- 八方雲集 / 高頻固定連鎖品項

成功標準：

- 商品型 query 大多能 local retrieve 命中
- sibling variant substitution 顯著下降
- search 角色退到真正 fallback

### Wave 3: Meal Pattern Foundation

先建高價值高模糊餐型。

優先內容：

- 自助餐
- 便當
- 滷味
- 火鍋
- 早餐店組合餐
- 牛肉麵
- 炒飯
- 鐵板麵
- 蚵仔煎
- 潤餅

成功標準：

- 模糊餐型 baseline 更穩
- `top_uncertainty_drivers` 更常被 pattern priors 正確引導

### Wave 4: Search-aware Evidence Layer

最後再把 search evidence 的 product-awareness 做強。

優先內容：

- item/product evidence vs generic knowledge evidence 分流
- variant match score
- source weighting

成功標準：

- search 只在真的有 product-quality evidence 時才進 evidence pass
- 不再悄悄用 generic article 影響 exact item answer

## 與現有知識資產的關係

目前 repo 與兄弟 repo 中的舊知識檔：

- 可作參考素材
- 可作 alias 靈感
- 可作題目清單與 coverage 靈感

但不能直接當正式 DB：

- `app/knowledge/exact_item_cards_tw.json`
- `app/knowledge/meal_templates_tw.json`
- `app/knowledge/risk_gate_packets_tw.json`
- `../line-liff-calorie-helper-main/knowledge/*.json`

原因：

- 它們多半是為較早期路徑設計
- 有 bootstrap estimate
- 有品質不一致與編碼歷史問題
- 不符合 greenfield canonical DB 的 provenance 要求

## 輸出位置

文件：

- [docs/DATA_BUILD_PLAN.md](C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main\docs\DATA_BUILD_PLAN.md)
- [docs/DATA_SOURCE_POLICY.md](C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main\docs\DATA_SOURCE_POLICY.md)

build workspace：

- `data_build/`
- `data_build/raw/`
- `data_build/normalized/`

runtime-ready artifacts 目標位置：

- `app/knowledge/base_nutrition_db.json`
- `app/knowledge/exact_items_db.json`
- `app/knowledge/meal_patterns_db.json`

## Test Plan

### Schema / build tests

- 三層 DB 都能通過 schema validation
- duplicate IDs / alias collisions 可被檢出
- exact item canonicalization 不合併 sibling variants
- source metadata 不可缺

### Retrieval behavior tests

- `全家鮪魚飯糰` 命中 Exact Item DB
- `寶礦力水得（580ml）` 不可被 `ION WATER` 替換
- `老賴紅茶（全糖去冰）` 可保留 variant identity
- `自助餐（一葷三素加半碗飯）` 優先走 Meal Pattern DB

### Product quality tests

- generic/common food baseline 更穩
- 商品型題目 local retrieval 命中率提升
- 模糊餐型的 baseline 與 follow-up 更合理
- search 低品質時不壓過 local DB evidence

### Refresh / provenance tests

- 每筆資料都有 source 與 `last_verified_at`
- stale sources 可被標記
- internal pattern records 不可偽裝成 official exact truth
