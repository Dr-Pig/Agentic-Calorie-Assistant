# V2 Eval Bundle 2 Cases

## 目的

這份文件定義 V2 Bundle 2 的 eval cases。

Bundle 2 覆蓋旅程 C（珍珠奶茶 clarify）、D（家常菜 clarify）、E（超標警告）、K（餐點修正）。

**前提：** Bundle 1 已通過（active BodyPlan 存在，intake commit 可用）。

**通過門檻：** 所有 P0 cases 必須通過。

---

## Eval Execution Contract

與 Bundle 1 相同：

- Codex 必須建立 `scripts/run_v2_bundle2_live_eval.py`
- 每個 case 執行後產出 trace artifact，`request_id` 貫穿整條 chain
- Bundle 2 完成 = `summary.bundle_gate == "pass"` + `p0_failed == 0` + 每個 case 有 trace artifact
- Codex 不能自己宣告通過，只有 eval runner 輸出說了算
- 輸出路徑：`.logs/bundle2_eval_{timestamp}.json` 或 `runtime/evals/v2_bundle2_live/`

---

## 兩種 Clarify 模式說明

Bundle 2 的 clarify cases 分兩種模式，來自 V1 golden test set（`founder_fit_golden_v1.json`）：

**模式 A：`estimate_with_followup`（珍珠奶茶類）**
- 系統知道食物的組成類別，但不確定影響熱量的關鍵因素（糖量、杯型）
- 正確行為：**先給估算範圍，再問細節**
- 例：「珍珠奶茶約 300–700 kcal，糖量和杯型會影響很多，你是幾分糖、大杯還是中杯？」
- 不應：不給任何數字直接問

**模式 B：`clarify_before_estimate`（家常菜、滷味、合菜類）**
- 系統完全不知道組成（不知道吃了什麼）
- 正確行為：**先問再說，不給任何數字**
- 例：「可以告訴我吃了什麼菜嗎？」
- 不應：給出任何 kcal 數字

---

## Macro 顯示規則（重要）

本文件所有 eval cases 皆需遵循以下 macro 顯示規則：

### 規則 1：Draft 狀態不顯示 macro
- 當 `canonical_commit == false`（clarify 模式尚未確認）時：
  - `show_macro == false`
  - `consumed_protein/carbs/fat` 應為 0 或 null

### 規則 2：Macro 對齊失敗不顯示
- 當 macro 計算不符合熱量公式時（誤差 > 10%）：
  - 公式：`kcal ≈ (protein × 4) + (carbs × 4) + (fat × 9)`
  - 允許誤差：±10%
  - 對齊失敗時：`show_macro == false`，但 `consumed_kcal` 仍應記錄

### 規則 3： Uncertainty Level 影響顯示
- 當 `uncertainty_level == "high"` 或 `identity_confidence == "low"` 時：
  - `show_macro == false`（不確定時不顯示 macro 誤導使用者）

### 規則 4：修正後 macro 應同步更新
- 當使用者修正餐點內容後：
  - `consumed_protein/carbs/fat` 應同步更新
  - 若更新後 macro 對齊失敗，`show_macro` 應變為 `false`

### 規則 5：Chat 回覆的 macro 顯示邏輯
- 若 `show_macro == true`：chat 可提及 macro 數字
- 若 `show_macro == false`：chat 不應提及具體 macro 數字（可說「熱量已記錄」）
- Chat 回覆的 macro 數字應與 `today.consumed_protein/carbs/fat` 一致

---

## Bundle 2 Cases

### 旅程 C：珍珠奶茶錄入（estimate_with_followup 模式）

---

#### C-001：珍珠奶茶，系統給估算範圍並問糖量/杯型

```yaml
case_id: C-001
journey: C
bundle: 2
priority: P0
case_class: golden
description: 使用者說「我喝了一杯珍珠奶茶」，系統應先給估算範圍，再問糖量和杯型（estimate_with_followup 模式）
```

**initial_state:** Bundle 1 onboarding 完成，有 active BodyPlan

**turn 1 input:**
```json
{"text": "我喝了一杯珍珠奶茶"}
```

**expected turn 1 chat_reply（estimate_with_followup）:**
- 回覆**應**包含估算範圍（例如「約 300–700 kcal」或「約 400–600 kcal」）
- 回覆**應**詢問糖量或杯型（至少其中一個）
- 回覆**不應**只問不給數字（那是 clarify_before_estimate 模式，不適用珍珠奶茶）
- `state_delta.canonical_commit` 應為 `false`（等確認細節後才 commit）

**turn 1 expected_ui_state（draft 狀態）:**
- `today.consumed_kcal == 0` 或 null（draft 尚未 commit）
- `today.consumed_protein == 0` 或 null
- `today.consumed_carbs == 0` 或 null
- `today.consumed_fat == 0` 或 null
- `today.show_macro == false`（規則 1：draft 狀態不顯示 macro）
- `today.active_meal_count == 0`

**turn 2 input:**
```json
{"text": "半糖大杯"}
```

**expected turn 2 chat_reply:**
- 回覆**應**包含更精確的估算值（例如「半糖大杯約 500 kcal，已記錄」）
- `state_delta.canonical_commit` 應為 `true`

**expected_ui_state（turn 2 後）:**
- `today.consumed_kcal > 0`
- `today.consumed_protein > 0`  # 驗證蛋白質
- `today.consumed_carbs > 0`    # 驗證碳水
- `today.consumed_fat > 0`      # 驗證脂肪
- `today.show_macro` 根據 macro 對齊結果：
  - 若對齊成功（誤差 ≤ 10%）：`show_macro == true`
  - 若對齊失敗（誤差 > 10%）：`show_macro == false`（規則 2）
- `today.active_meal_count == 1`

**hard_fail_conditions:**
- Turn 1 完全不給任何數字就問（應給範圍）
- Turn 1 直接 commit 一個精確數字（不應在未確認細節前 commit）
- Turn 2 沒有 commit
- Turn 1 說「無法估算」後停止

---

#### C-002：珍珠奶茶，一次給完糖量和杯型，直接估算不再問

```yaml
case_id: C-002
journey: C
bundle: 2
priority: P1
case_class: edge
description: 使用者一次說「全糖大杯珍珠奶茶」，系統應直接估算，不需再問
```

**initial_state:** Bundle 1 onboarding 完成

**input:**
```json
{"text": "我喝了一杯全糖大杯珍珠奶茶"}
```

**expected_chat_reply:**
- 回覆**應**包含估算熱量
- 回覆**應**確認已記錄
- 回覆**不應**再問糖量或杯型（已提供）
- `state_delta.canonical_commit` 應為 `true`

**expected_ui_state:**
- `today.consumed_kcal > 0`
- `today.consumed_protein > 0`  # 驗證蛋白質
- `today.consumed_carbs > 0`    # 驗證碳水
- `today.consumed_fat > 0`      # 驗證脂肪
- `today.show_macro` 根據 macro 對齊結果：
  - 若對齊成功（誤差 ≤ 10%）：`show_macro == true`
  - 若對齊失敗（誤差 > 10%）：`show_macro == false`（規則 2）
- `today.active_meal_count == 1`

**hard_fail_conditions:**
- 系統還是問糖量或杯型（已提供，不應再問）
- 沒有 commit

---

### 旅程 D：家常菜錄入（clarify_before_estimate 模式）

---

#### D-001：家常菜，系統先問再說，不給任何數字

```yaml
case_id: D-001
journey: D
bundle: 2
priority: P0
case_class: golden
description: 使用者說「我剛吃了我媽做的家常菜」，系統完全不知道組成，應先問再說（clarify_before_estimate 模式），不給任何 kcal 數字
```

**initial_state:** Bundle 1 onboarding 完成

**turn 1 input:**
```json
{"text": "我剛吃了我媽做的家常菜"}
```

**expected turn 1 chat_reply（clarify_before_estimate）:**
- 回覆**應**反問具體菜色（例如「可以告訴我吃了什麼菜嗎？」）
- 回覆**不應**包含任何 kcal 數字（完全不知道組成，不應給範圍）
- 回覆**不應**說「無法估算」後停止（應反問，不應停止）
- `state_delta.canonical_commit` 應為 `false`

**turn 1 expected_ui_state（draft 狀態）:**
- `today.consumed_kcal == 0` 或 null（draft 尚未 commit）
- `today.consumed_protein == 0` 或 null
- `today.consumed_carbs == 0` 或 null
- `today.consumed_fat == 0` 或 null
- `today.show_macro == false`（規則 1：draft 狀態不顯示 macro）
- `today.active_meal_count == 0`

**turn 2 input:**
```json
{"text": "炒空心菜、紅燒肉三塊、白飯一碗"}
```

**expected turn 2 chat_reply:**
- 回覆**應**逐項或整體給出估算熱量
- 回覆**應**確認已記錄
- `state_delta.canonical_commit` 應為 `true`

**expected_ui_state（turn 2 後）:**
- `today.consumed_kcal > 0`
- `today.consumed_protein > 0`  # 驗證蛋白質
- `today.consumed_carbs > 0`    # 驗證碳水
- `today.consumed_fat > 0`      # 驗證脂肪
- `today.show_macro` 根據 macro 對齊結果：
  - 若對齊成功（誤差 ≤ 10%）：`show_macro == true`
  - 若對齊失敗（誤差 > 10%）：`show_macro == false`（規則 2）
- `today.active_meal_count == 1`

**hard_fail_conditions:**
- Turn 1 說「無法估算」後停止（應反問）
- Turn 1 直接 commit（不應在未知菜色前 commit）
- Turn 2 沒有 commit

---

#### D-002：家常菜，使用者直接說出菜色，一次 commit

```yaml
case_id: D-002
journey: D
bundle: 2
priority: P1
case_class: edge
description: 使用者直接說「我吃了炒青菜和白飯」，系統應直接估算，不需再問
```

**initial_state:** Bundle 1 onboarding 完成

**input:**
```json
{"text": "我剛吃了炒青菜和白飯一碗"}
```

**expected_chat_reply:**
- 回覆**應**包含估算熱量
- 回覆**應**確認已記錄
- `state_delta.canonical_commit` 應為 `true`

**expected_ui_state:**
- `today.consumed_kcal > 0`
- `today.consumed_protein > 0`  # 驗證蛋白質
- `today.consumed_carbs > 0`    # 驗證碳水
- `today.consumed_fat > 0`      # 驗證脂肪
- `today.show_macro` 根據 macro 對齊結果：
  - 若對齊成功（誤差 ≤ 10%）：`show_macro == true`
  - 若對齊失敗（誤差 > 10%）：`show_macro == false`（規則 2）
- `today.active_meal_count == 1`

**hard_fail_conditions:**
- 系統還是問「吃了什麼菜」（已提供）
- 沒有 commit

---

### 旅程 E：超標後的 UI 警告與對話回覆

---

#### E-001：錄入後超標，chat 說明超標量，UI 顯示超標狀態

```yaml
case_id: E-001
journey: E
bundle: 2
priority: P0
case_class: golden
description: 使用者今日已接近目標，再錄入一餐後超標，chat 回覆應說明超標量，UI 應顯示超標狀態
```

**initial_state:**
```json
{
  "body_plan": {"daily_budget_kcal": 1200, "status": "active"},
  "day_budget_ledger": {
    "budget_kcal": 1200,
    "consumed_kcal": 900,
    "remaining_kcal": 300
  }
}
```

**input:**
```json
{"text": "我剛吃了一個排骨便當"}
```

**expected_chat_reply:**
- 回覆**應**包含排骨便當的估算熱量
- 回覆**應**明確說明今日已超標（例如「今天已超出目標約 X kcal」）
- 回覆**不應**只說「已記錄」而不提超標
- 回覆**不應**在同一則回覆裡附加 rescue 建議（rescue 是獨立訊息）
- `state_delta.canonical_commit` 應為 `true`

**expected_ui_state:**
- `today.remaining_kcal < 0`（超標）
- `today.consumed_kcal > 1200`
- `today.consumed_protein > 0`  # 驗證蛋白質
- `today.consumed_carbs > 0`    # 驗證碳水
- `today.consumed_fat > 0`      # 驗證脂肪
- `today.show_macro` 根據 macro 對齊結果：
  - 若對齊成功（誤差 ≤ 10%）：`show_macro == true`
  - 若對齊失敗（誤差 > 10%）：`show_macro == false`（規則 2）

**hard_fail_conditions:**
- Chat 回覆沒有提到超標
- Chat 回覆在同一則訊息裡附加 rescue 建議
- `today.remaining_kcal` 沒有變成負數

---

#### E-002：超標量在 chat 和 UI 一致

```yaml
case_id: E-002
journey: E
bundle: 2
priority: P0
case_class: golden
description: 超標後，chat 說的超標量與 UI 顯示的 remaining_kcal 一致（數字來自 ledger，不由 LLM 重算）
```

**initial_state:**
```json
{
  "body_plan": {"daily_budget_kcal": 1200, "status": "active"},
  "day_budget_ledger": {
    "budget_kcal": 1200,
    "consumed_kcal": 1000,
    "remaining_kcal": 200
  }
}
```

**input:**
```json
{"text": "我剛吃了一碗牛肉麵"}
```

**expected_chat_reply:**
- 回覆包含超標說明
- Chat 說的超標量 = `abs(today.remaining_kcal)`（差距 ≤ 20 kcal）

**expected_ui_state:**
- `today.remaining_kcal < 0`
- `today.consumed_kcal` = 1000 + 牛肉麵估算值
- `today.consumed_protein > 0`  # 驗證蛋白質
- `today.consumed_carbs > 0`    # 驗證碳水
- `today.consumed_fat > 0`      # 驗證脂肪
- `today.show_macro` 根據 macro 對齊結果：
  - 若對齊成功（誤差 ≤ 10%）：`show_macro == true`
  - 若對齊失敗（誤差 > 10%）：`show_macro == false`（規則 2）

**hard_fail_conditions:**
- Chat 說的超標量與 `abs(today.remaining_kcal)` 差距 > 20 kcal（數字不一致）
- LLM 自行計算超標量而不讀 ledger

---

#### E-003：未超標時，不顯示超標警告

```yaml
case_id: E-003
journey: E
bundle: 2
priority: P1
case_class: edge
description: 使用者錄入後仍有剩餘預算，回覆不應顯示超標警告
```

**initial_state:**
```json
{
  "body_plan": {"daily_budget_kcal": 1600, "status": "active"},
  "day_budget_ledger": {
    "budget_kcal": 1600,
    "consumed_kcal": 400,
    "remaining_kcal": 1200
  }
}
```

**input:**
```json
{"text": "我剛吃了一碗滷肉飯"}
```

**expected_chat_reply:**
- 回覆**不應**包含「超標」字樣
- 回覆**應**顯示剩餘預算（正數）

**expected_ui_state:**
- `today.remaining_kcal > 0`（未超標）
- `today.consumed_kcal > 0`
- `today.consumed_protein > 0`  # 驗證蛋白質
- `today.consumed_carbs > 0`    # 驗證碳水
- `today.consumed_fat > 0`      # 驗證脂肪
- `today.show_macro` 根據 macro 對齊結果：
  - 若對齊成功（誤差 ≤ 10%）：`show_macro == true`
  - 若對齊失敗（誤差 > 10%）：`show_macro == false`（規則 2）

**hard_fail_conditions:**
- 回覆說「超標」（沒有超標）

---

### 旅程 K：餐點修正（item-level）

---

#### K-001：chat 自然語言修正單一 item，其他 item 不變

```yaml
case_id: K-001
journey: K
bundle: 2
priority: P0
case_class: golden
description: 使用者說「剛才那杯豆漿我記錯了，應該是有糖豆漿，大概 150 kcal」，系統應只更新豆漿，牛肉麵不變，建立新 MealVersion
```

**initial_state:** 已有一筆 MealThread（牛肉麵 + 豆漿），豆漿 80 kcal，牛肉麵 600 kcal，總計 680 kcal

**setup（先錄入）:**
```json
{"text": "我剛吃了一碗牛肉麵和一杯無糖豆漿"}
```

**correction input:**
```json
{"text": "剛才那杯豆漿我記錯了，應該是有糖豆漿，大概 150 kcal"}
```

**expected_chat_reply（correction 後）:**
- 回覆**應**確認修正了豆漿（例如「已將豆漿更新為 150 kcal」）
- 回覆**應**說明這一餐的新總計
- 牛肉麵的數字**不應**改變

**expected_ui_state（correction 後）:**
- `today.consumed_kcal` 更新為新總計（牛肉麵 + 150 kcal 豆漿）
- `today.consumed_protein` 更新（蛋白質也應同步更新）  # 規則 4：修正後 macro 應同步更新
- `today.consumed_carbs` 更新（碳水也應同步更新）
- `today.consumed_fat` 更新（脂肪也應同步更新）
- `today.show_macro` 根據 macro 對齊結果：
  - 若對齊成功（誤差 ≤ 10%）：`show_macro == true`
  - 若對齊失敗（誤差 > 10%）：`show_macro == false`（規則 2、4）
- 新 MealVersion 建立（舊版本保留，不覆寫）

**expected_state_delta:**
```json
{
  "new_meal_version_created": true,
  "old_version_superseded": true,
  "ledger_updated": true
}
```

**hard_fail_conditions:**
- 牛肉麵的熱量被改變
- 沒有建立新 MealVersion（直接覆寫舊版本）
- `today.consumed_kcal` 沒有更新

---

#### K-002：使用者說「豆漿我沒喝」，item 標記為 removed

```yaml
case_id: K-002
journey: K
bundle: 2
priority: P1
case_class: golden
description: 使用者說「豆漿我沒喝」，系統應將豆漿 item 標記為 removed，不刪除整個 MealThread
```

**initial_state:** 已有一筆 MealThread（牛肉麵 + 豆漿）

**setup:**
```json
{"text": "我剛吃了一碗牛肉麵和一杯無糖豆漿"}
```

**correction input:**
```json
{"text": "豆漿我沒喝"}
```

**expected_chat_reply:**
- 回覆**應**確認豆漿已移除
- 回覆**應**說明這一餐的新總計（只有牛肉麵）

**expected_ui_state:**
- `today.consumed_kcal` 更新為只有牛肉麵的熱量
- `today.consumed_protein` 更新（蛋白質也應同步更新）  # 規則 4：修正後 macro 應同步更新
- `today.consumed_carbs` 更新（碳水也應同步更新）
- `today.consumed_fat` 更新（脂肪也應同步更新）
- `today.show_macro` 根據 macro 對齊結果：
  - 若對齊成功（誤差 ≤ 10%）：`show_macro == true`
  - 若對齊失敗（誤差 > 10%）：`show_macro == false`（規則 2、4）
- MealThread 仍存在（不應刪除整個 thread）

**hard_fail_conditions:**
- 整個 MealThread 被刪除
- `today.consumed_kcal` 沒有更新（豆漿熱量沒有被移除）

---

#### K-003：修正後 chat 查詢，數字反映修正後的狀態

```yaml
case_id: K-003
journey: K
bundle: 2
priority: P1
case_class: golden
description: 修正後使用者問「我今天吃了多少」，chat 回覆應反映修正後的數字
```

**initial_state:** 已有一筆 MealThread，已完成 K-001 的修正

**input:**
```json
{"text": "我今天吃了多少？"}
```

**expected_chat_reply:**
- 回覆的消耗熱量應反映修正後的數字（牛肉麵 + 150 kcal 豆漿）
- 回覆的蛋白質/碳水/脂肪應反映修正後的數字
- 數字應與 `today.consumed_kcal` 一致
- 數字應與 `today.consumed_protein/carbs/fat` 一致
- 如果 `today.show_macro == false`，chat 不應提及 macro 數字（因為 macro 對齊失敗）

**hard_fail_conditions:**
- Chat 回覆的數字是修正前的舊數字
- Chat 數字與 `today.consumed_kcal` 不一致
- Chat 數字與 `today.consumed_protein/carbs/fat` 不一致
- 當 `show_macro == false` 時，chat 仍提及具體 macro 數字（規則 5）

---

## Bundle 2 通過門檻

| Case | Priority | 通過條件 |
|------|---------|---------|
| C-001 | P0 | Turn 1 反問糖量/杯型不 commit；Turn 2 commit 並給估算值 |
| D-001 | P0 | Turn 1 反問菜色不 commit；Turn 2 commit |
| E-001 | P0 | Chat 說明超標量；不附加 rescue；UI remaining_kcal < 0 |
| E-002 | P0 | Chat 超標量與 UI remaining_kcal 一致（差距 ≤ 20 kcal） |
| K-001 | P0 | 只更新豆漿；牛肉麵不變；新 MealVersion 建立；ledger 更新 |
| C-002 | P1 | 一次給完不再問 |
| D-002 | P1 | 直接說菜色不再問 |
| E-003 | P1 | 未超標時不顯示超標警告 |
| K-002 | P1 | item removed；MealThread 保留；ledger 更新 |
| K-003 | P1 | 修正後查詢數字正確 |

**P0 cases（5 個）全部通過 = Bundle 2 通過的必要條件。**

---

## Eval Runner 規格

`scripts/run_v2_bundle2_live_eval.py` 必須：

1. 對每個 case 先 seed initial_state（onboarding + 必要的 setup turns）
2. 執行 test input，拿到 `request_id`
3. 讀 `/admin/trace/{request_id}` 驗證 trace artifact
4. 讀 `/today/current-budget` 驗證 UI state
5. 對照每個 case 的 expected conditions
6. 輸出 JSON report

**Multi-turn cases（C-001、D-001、K-001、K-002、K-003）的特殊處理：**
- Turn 1 的 `request_id` 和 Turn 2 的 `request_id` 都要記錄
- Turn 1 的 `state_delta.canonical_commit` 必須是 `false`（clarify cases）
- Turn 2 的 `state_delta.canonical_commit` 必須是 `true`

**Correction cases（K-001、K-002）的特殊處理：**
- 需要先跑 setup turn（錄入原始餐點）
- 再跑 correction turn
- 驗證 `new_meal_version_created` 和 `old_version_superseded`

---

## 版本記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| v1.0 | 2026-04-21 | 初始建立，Bundle 2 cases（C-001 ~ K-003），10 個 cases，5 個 P0 |
| v1.1 | 2026-04-21 | 新增 macro 驗證（protein/carbs/fat/show_macro） |
| v1.2 | 2026-04-21 | 新增 show_macro UI 顯示規則（誤差過大不顯示 macro） |
| v1.3 | 2026-04-21 | 新增 draft 狀態驗證（規則 1）、uncertainty level 影響（規則 3）、修正後同步更新（規則 4）、chat 回覆顯示邏輯（規則 5） |
