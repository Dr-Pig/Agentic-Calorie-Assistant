# V2 Eval Bundle 1 Cases

## 目的

這份文件定義 V2 Bundle 1 的 eval cases。

Bundle 1 覆蓋旅程 A（Onboarding）、B（單回合錄入）、J（跳過 Onboarding 降級）。

**通過門檻：** 所有 P0 cases 必須通過，V2 通過率 ≥ V1。

**角色定位：**

- 這份文件是 Bundle 1 的主 gate，不是最後才跑的驗收附錄
- Bundle 1 runtime 只需做到通過這份 eval，不准提前擴張到其他 journey
- 若 case 與細部 spec 衝突，先修 owner truth，再繼續 build

---

## V2 Eval Case 格式

每個 case 包含：

- `case_id`：唯一識別碼
- `journey`：對應 UX Journey（A / B / J）
- `bundle`：所屬 bundle（1）
- `priority`：P0 / P1 / P2
- `case_class`：golden / edge / regression
- `description`：測試什麼
- `initial_state`：起始 canonical state
- `input`：使用者輸入
- `expected_chat_reply`：chat 回覆的驗證點（必填）
- `expected_ui_state`：UI 狀態的驗證點（必填）
- `expected_state_delta`：canonical state 的變化
- `hard_fail_conditions`：任一條件成立即 hard fail

**雙面驗證原則：** `expected_chat_reply` 和 `expected_ui_state` 都必須填，缺一不算通過。

**中層測試要求：**

這份 E2E eval 是最上層 gate；同時仍需保留：

- tool contract tests
- state transition tests
- renderer / deterministic sidecar contract tests

這些中層測試只負責 debug leverage，不反過來改寫 E2E bundle scope。

---

## Bundle 1 Cases

### 旅程 A：Onboarding 完整流程

---

#### A-001：完整 Onboarding，確認 TDEE + 每日目標數字

```yaml
case_id: A-001
journey: A
bundle: 1
priority: P0
case_class: golden
description: 使用者完整填寫 onboarding，確認 chat 和 UI 都顯示正確的 TDEE 和每日目標熱量
```

**initial_state:**
```json
{
  "body_plan": null,
  "day_budget_ledger": null,
  "body_profile": null
}
```

**input（UI onboarding 表單）:**
```json
{
  "channel": "ui_form",
  "sex": "female",
  "age_years": 28,
  "height_cm": 162,
  "current_weight_kg": 63,
  "goal_type": "lose_weight",
  "activity_level": "sedentary",
  "target_weight_kg": 55,
  "weekly_target_rate_kg": 0.5
}
```

**expected_chat_reply（使用者問「我今天的目標是多少？」後）:**
- 回覆必須包含 TDEE 數字（例如「TDEE 約 1600 kcal」）
- 回覆必須包含每日目標熱量數字（例如「每日目標 1050 kcal」）
- 不可只說「已設定」而不給數字
- 數字必須與 UI 一致

**expected_ui_state:**
- `body_plan.daily_budget_kcal` 存在且 > 0
- `body_plan.estimated_tdee` 存在且 > 0
- `day_budget_ledger.budget_kcal` = `body_plan.daily_budget_kcal`
- `day_budget_ledger.consumed_kcal` = 0
- `day_budget_ledger.remaining_kcal` = `body_plan.daily_budget_kcal`

**expected_state_delta:**
```json
{
  "body_profile_created": true,
  "body_plan_created": true,
  "body_plan_status": "active",
  "day_budget_ledger_created": true
}
```

**hard_fail_conditions:**
- chat 回覆沒有 TDEE 數字
- chat 回覆沒有每日目標熱量數字
- chat 數字與 UI 數字不一致
- `body_plan` 未建立
- `day_budget_ledger` 未建立

---

#### A-002：跳過 activity_level，採 sedentary 預設

```yaml
case_id: A-002
journey: A
bundle: 1
priority: P1
case_class: edge
description: 使用者跳過 activity_level，系統採 sedentary 預設，仍可完成 onboarding
```

**initial_state:**
```json
{
  "body_plan": null,
  "day_budget_ledger": null
}
```

**input（UI onboarding 表單，跳過 activity_level）:**
```json
{
  "channel": "ui_form",
  "sex": "male",
  "age_years": 30,
  "height_cm": 175,
  "current_weight_kg": 80,
  "goal_type": "lose_weight",
  "activity_level": null,
  "target_weight_kg": 70,
  "weekly_target_rate_kg": 0.5
}
```

**expected_chat_reply（使用者問「我今天的目標是多少？」後）:**
- 回覆必須包含每日目標熱量數字
- TDEE 應基於 sedentary multiplier（× 1.2）計算

**expected_ui_state:**
- `body_plan.daily_budget_kcal` 存在且 > 0
- TDEE 計算應使用 sedentary multiplier

**hard_fail_conditions:**
- onboarding 因缺少 activity_level 而失敗
- `body_plan` 未建立

---

#### A-003：weekly_target_rate_kg 極端時，safety floor 保護每日目標不低於底線

```yaml
case_id: A-003
journey: A
bundle: 1
priority: P1
case_class: edge
description: 使用者設定激進減重速率，系統應套用 safety floor，確保每日目標不低於底線（女性 1200 kcal，男性 1500 kcal）
```

**initial_state:**
```json
{
  "body_plan": null
}
```

**input（UI onboarding 表單，設定激進速率）:**
```json
{
  "channel": "ui_form",
  "sex": "female",
  "age_years": 25,
  "height_cm": 160,
  "current_weight_kg": 65,
  "goal_type": "lose_weight",
  "activity_level": "sedentary",
  "weekly_target_rate_kg": 1.5
}
```

**expected_chat_reply（使用者問「我今天的目標是多少？」後）:**
- 回覆必須包含每日目標熱量數字
- 每日目標熱量**不得低於** 1200 kcal（女性 safety floor）
- 系統不拒絕 onboarding，但 safety floor 生效

**expected_ui_state:**
- `body_plan.daily_budget_kcal` ≥ 1200（女性 safety floor）
- `body_plan.safety_floor_kcal` = 1200

**hard_fail_conditions:**
- `body_plan.daily_budget_kcal` < 1200（低於 safety floor）
- `body_plan` 未建立（系統不應拒絕 onboarding）

---

### 旅程 B：單回合錄入 + 預算同步

---

#### B-001：單回合錄入，chat 和 UI 數字一致

```yaml
case_id: B-001
journey: B
bundle: 1
priority: P0
case_class: golden
description: 使用者記錄一餐，確認 chat 回覆和 UI 的消耗熱量、剩餘熱量一致
```

**initial_state:**
```json
{
  "body_plan": {
    "daily_budget_kcal": 1450,
    "estimated_tdee": 1800,
    "safety_floor_kcal": 1200,
    "status": "active"
  },
  "day_budget_ledger": {
    "local_date": "2026-04-20",
    "budget_kcal": 1450,
    "consumed_kcal": 0,
    "remaining_kcal": 1450
  }
}
```

**input:**
```json
{
  "channel": "chat",
  "text": "我剛吃了一碗滷肉飯和一杯無糖豆漿"
}
```

**expected_chat_reply:**
- 回覆必須包含：食物名稱（滷肉飯、無糖豆漿）
- 回覆必須包含：估算熱量（各自 + 總計）
- 回覆必須包含：已記錄確認
- 回覆必須包含：今日剩餘熱量（例如「還剩約 820 kcal」）
- 數字必須與 UI 一致

**expected_ui_state:**
- `day_budget_ledger.consumed_kcal` 更新為估算值（約 630 kcal）
- `day_budget_ledger.remaining_kcal` = 1450 - consumed_kcal
- 餐點列表出現新記錄

**expected_state_delta:**
```json
{
  "meal_thread_created": true,
  "meal_version_created": true,
  "meal_items_created": 2,
  "ledger_entry_created": true,
  "ledger_entry_type": "meal_consumption"
}
```

**hard_fail_conditions:**
- chat 回覆沒有估算熱量
- chat 回覆沒有剩餘熱量
- chat 數字與 UI 數字不一致（差距 > 10 kcal）
- `meal_thread` 未建立
- `day_budget_ledger.consumed_kcal` 未更新

---

#### B-002：錄入後查詢剩餘預算，數字一致

```yaml
case_id: B-002
journey: B
bundle: 1
priority: P0
case_class: golden
description: 使用者錄入後問「我今天還能吃多少」，chat 回覆的數字與 UI 一致
```

**initial_state:**
```json
{
  "body_plan": {
    "daily_budget_kcal": 1450,
    "status": "active"
  },
  "day_budget_ledger": {
    "budget_kcal": 1450,
    "consumed_kcal": 630,
    "remaining_kcal": 820
  }
}
```

**input:**
```json
{
  "channel": "chat",
  "text": "我今天還能吃多少？"
}
```

**expected_chat_reply:**
- 回覆必須包含：今日目標（1450 kcal）
- 回覆必須包含：已消耗（630 kcal）
- 回覆必須包含：剩餘（820 kcal）
- 三個數字都必須與 UI 一致
- 數字來自 `CurrentBudgetView`，不由 LLM 重算

**expected_ui_state:**
- `day_budget_ledger.remaining_kcal` = 820

**hard_fail_conditions:**
- chat 回覆的剩餘熱量與 UI 不一致
- chat 回覆沒有具體數字
- LLM 自行計算數字而不讀 ledger

---

#### B-003：多食物同一餐，形成一個 MealThread 多個 MealItem

```yaml
case_id: B-003
journey: B
bundle: 1
priority: P1
case_class: golden
description: 使用者一次說多個食物，應形成一個 MealThread 含多個 MealItem
```

**initial_state:**
```json
{
  "body_plan": { "daily_budget_kcal": 1600, "status": "active" },
  "day_budget_ledger": { "budget_kcal": 1600, "consumed_kcal": 0, "remaining_kcal": 1600 }
}
```

**input:**
```json
{
  "channel": "chat",
  "text": "我剛吃了排骨便當、一杯無糖綠茶、還有一顆茶葉蛋"
}
```

**expected_chat_reply:**
- 回覆應逐項列出估算熱量
- 回覆應給出總計

**expected_state_delta:**
```json
{
  "meal_thread_created": 1,
  "meal_items_created": 3,
  "ledger_entries_created": 1
}
```

**hard_fail_conditions:**
- 建立了多個 MealThread（應該只有一個）
- MealItem 數量不是 3

---

#### B-004：無 BodyPlan 時錄入，不顯示剩餘預算

```yaml
case_id: B-004
journey: B
bundle: 1
priority: P1
case_class: edge
description: 使用者未完成 onboarding 就錄入，系統應給出估算但不顯示剩餘預算
```

**initial_state:**
```json
{
  "body_plan": null,
  "day_budget_ledger": null
}
```

**input:**
```json
{
  "channel": "chat",
  "text": "我剛吃了一碗牛肉麵"
}
```

**expected_chat_reply:**
- 回覆應給出估算熱量
- 回覆**不應**顯示「還剩 X kcal」
- 回覆**不應**顯示今日目標

**expected_ui_state:**
- `meal_thread` 建立（intake 仍可用）
- Today 頁面顯示「尚未設定目標」

**hard_fail_conditions:**
- 系統拒絕記錄（intake 應仍可用）
- 系統顯示剩餘預算（沒有 BodyPlan 不應顯示）

---

### 旅程 J：跳過 Onboarding 的降級行為

---

#### J-001：跳過 Onboarding，問剩餘預算，引導 onboarding

```yaml
case_id: J-001
journey: J
bundle: 1
priority: P0
case_class: golden
description: 使用者跳過 onboarding，問「我今天還能吃多少」，系統應說明尚未設定目標並引導
```

**initial_state:**
```json
{
  "body_plan": null,
  "day_budget_ledger": null
}
```

**input:**
```json
{
  "channel": "chat",
  "text": "我今天還能吃多少？"
}
```

**expected_chat_reply:**
- 回覆應說明尚未設定目標
- 回覆應提供 onboarding 入口（例如「請先設定你的目標」）
- 回覆**不應**給出任何熱量數字

**expected_ui_state:**
- Today 頁面顯示「尚未設定目標」提示
- 不顯示目標熱量或剩餘熱量

**hard_fail_conditions:**
- 系統給出剩餘熱量數字（沒有 BodyPlan 不應給）
- 系統沒有引導使用者完成 onboarding

---

#### J-002：跳過 Onboarding，仍可錄入餐點

```yaml
case_id: J-002
journey: J
bundle: 1
priority: P1
case_class: golden
description: 使用者跳過 onboarding，直接錄入餐點，系統應允許並給出估算（但不顯示預算）
```

**initial_state:**
```json
{
  "body_plan": null,
  "day_budget_ledger": null
}
```

**input:**
```json
{
  "channel": "chat",
  "text": "我剛吃了一碗牛肉麵"
}
```

**expected_chat_reply:**
- 回覆應給出估算熱量（例如「牛肉麵約 600 kcal」）
- 回覆**不應**顯示剩餘預算
- 回覆**不應**說「無法記錄」

**expected_state_delta:**
```json
{
  "meal_thread_created": true,
  "day_budget_ledger_created": false
}
```

**hard_fail_conditions:**
- 系統拒絕記錄
- 系統顯示剩餘預算

---

## Bundle 1 通過門檻

| Case | Priority | 通過條件 |
|------|---------|---------|
| A-001 | P0 | chat 有 TDEE + 每日目標數字，且與 UI 一致 |
| B-001 | P0 | chat 有估算熱量 + 剩餘熱量，且與 UI 一致 |
| B-002 | P0 | chat 剩餘熱量與 UI 一致，數字來自 ledger |
| J-001 | P0 | chat 說明尚未設定目標，引導 onboarding |
| A-002 | P1 | 跳過 activity_level 仍可完成 onboarding |
| A-003 | P1 | safety floor 生效，每日目標 ≥ 1200 kcal（女性），body_plan 建立 |
| B-003 | P1 | 多食物形成一個 MealThread |
| B-004 | P1 | 無 BodyPlan 時 intake 仍可用，不顯示預算 |
| J-002 | P1 | 無 BodyPlan 時 intake 仍可用 |

**P0 cases 全部通過 = Bundle 1 通過的必要條件。**

---

## 驗證方式

每個 case 的驗證分兩步：

**Step 1：Chat 回覆驗證**
- 讀 `renderer_output.assistant_message`
- 對照 `expected_chat_reply` 的每個條件
- 任一條件不符 → fail

**Step 2：UI 狀態驗證**
- 讀 `sidecar_output.domain_payload` 和 canonical state
- 對照 `expected_ui_state` 的每個條件
- 任一條件不符 → fail

**兩步都通過才算 case 通過。**

---

## 版本記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| v1.0 | 2026-04-20 | 初始建立，Bundle 1 cases（A-001 ~ J-002），9 個 cases，4 個 P0 |

---

## Eval Execution Contract

### 核心原則

**Codex 不能自己宣告 eval 通過。** 只有 eval runner 讀 trace artifact 並對照 expected conditions 後，才算通過。

「13 tests passed」不等於「9 eval cases passed」。Unit tests 是 Codex 自己寫的，eval cases 是獨立的 acceptance gate。

### Eval Runner 規格

Codex 必須建立一個 eval runner script：`scripts/run_bundle1_eval.py`

**Runner 的工作流程：**

```
for each case in V2_EVAL_BUNDLE_1_CASES:
  1. 準備 initial_state（seed DB）
  2. 呼叫 /v2/estimate（或直接呼叫 execute_bundle1_turn）
  3. 拿到 request_id
  4. 讀 /admin/trace/{request_id} 的 trace artifact
  5. 對照 expected_chat_reply 的每個條件
  6. 對照 expected_ui_state 的每個條件
  7. 輸出 pass / fail + 失敗原因
```

**Runner 輸出格式（必須是 JSON，可被另一個 agent 讀）：**

```json
{
  "bundle": 1,
  "run_timestamp": "2026-04-20T10:00:00Z",
  "cases": [
    {
      "case_id": "A-001",
      "priority": "P0",
      "status": "pass",
      "request_id": "30b7b31a60be41b395c22f1028375c93",
      "admin_trace_url": "/admin/trace/30b7b31a60be41b395c22f1028375c93",
      "chat_reply_checks": [
        {"condition": "contains TDEE number", "result": "pass", "actual": "TDEE 約 1600 kcal"},
        {"condition": "contains daily budget number", "result": "pass", "actual": "每日目標 1050 kcal"}
      ],
      "ui_state_checks": [
        {"condition": "body_plan.daily_budget_kcal > 0", "result": "pass", "actual": 1050},
        {"condition": "day_budget_ledger.consumed_kcal == 0", "result": "pass", "actual": 0}
      ],
      "hard_fail_triggered": false,
      "failure_reason": null
    }
  ],
  "summary": {
    "total": 9,
    "passed": 9,
    "failed": 0,
    "p0_passed": 4,
    "p0_failed": 0,
    "bundle_gate": "pass"
  }
}
```

**Runner 輸出檔案路徑：** `.logs/bundle1_eval_{timestamp}.json`

### Bundle 1 完成的定義

Bundle 1 完成 = 以下三個條件**全部**成立：

1. `scripts/run_bundle1_eval.py` 執行後，`summary.bundle_gate == "pass"`
2. `summary.p0_failed == 0`（4 個 P0 cases 全過）
3. 每個 case 的 `request_id` 都有對應的 trace artifact 存在（`audit.request_trace_exists == true`）

**不接受的「通過」：**
- Codex 自己說「我測過了」
- Unit tests 通過但沒有 eval runner 輸出
- Eval runner 輸出但沒有 trace artifact

### Trace Artifact 驗證欄位

每個 case 的 trace artifact（`/admin/trace/{request_id}`）必須包含以下欄位，否則視為 trace 不完整：

| 欄位 | 說明 |
|------|------|
| `state_before` | 執行前的 canonical state |
| `manager_decision.intent_type` | manager 的意圖判斷 |
| `tool_outputs` | 每個 tool 的輸入和輸出 |
| `state_after` | 執行後的 canonical state |
| `renderer_output.assistant_message` | chat 回覆的實際文字 |
| `sidecar_output` | UI state 的實際值 |
| `state_delta` | canonical state 的變化 |

### Chat Reply 驗證方式

`expected_chat_reply` 的每個條件對應 trace 的 `renderer_output.assistant_message`：

- **「包含 X 數字」**：從 `assistant_message` 中提取數字，對照 `sidecar_output` 的對應欄位，差距 ≤ 10 kcal 視為通過
- **「不應顯示 X」**：`assistant_message` 不包含特定關鍵字
- **「數字與 UI 一致」**：`assistant_message` 中的數字 = `sidecar_output` 中的對應數字

### UI State 驗證方式

`expected_ui_state` 的每個條件對應 trace 的 `sidecar_output` 和 `state_after`：

- **`body_plan.daily_budget_kcal > 0`**：讀 `state_after.active_body_plan_view.daily_budget_kcal`
- **`day_budget_ledger.consumed_kcal == X`**：讀 `state_after.current_budget_view.consumed_kcal`
- **`meal_thread_created == true`**：讀 `state_delta.meal_logged == true` 或 `state_delta.draft_saved == true`

---

## 版本記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| v1.0 | 2026-04-20 | 初始建立，Bundle 1 cases（A-001 ~ J-002），9 個 cases，4 個 P0 |
| v1.1 | 2026-04-20 | 修正 A-003：改為 safety floor 保護測試，移除 1.0 kg/week 拒絕邏輯 |
| v1.2 | 2026-04-20 | 新增 Eval Execution Contract：eval runner 規格、trace artifact 驗證、Bundle 1 完成定義 |
