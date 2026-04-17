# L0A Onboarding Flow Spec

## 1. 目的

這份 spec 定義使用者第一次進入產品時的 onboarding flow。

它回答：

- 使用者需要提供哪些最小資訊才能開始使用
- 這些資訊如何 bootstrap `BodyPlan` 與 `DayBudgetLedger`
- onboarding 是否可以分步驟完成
- 使用者跳過 onboarding 時的 fallback posture
- onboarding 完成後系統的初始狀態是什麼

它暫時不回答：

- onboarding UI 的視覺設計細節
- prompt wording
- onboarding 的 A/B testing 策略

---

## 2. 核心原則

### 2.1 最低摩擦優先

onboarding 應只收集讓系統可以安全運作的最小資訊集合。

不應在 onboarding 階段要求：

- 詳細飲食偏好
- 過去飲食歷史
- 精確活動量記錄

### 2.2 漸進式補全

使用者可以在 onboarding 後繼續補充資訊。

系統應在資訊不足時降級運作，而不是拒絕服務。

### 2.3 Proposal-First 的 plan 初始化

onboarding 收集到足夠資訊後，系統應先產生一個初始 `BodyPlan` proposal，讓使用者確認後才正式生效。

不應在使用者未確認的情況下直接寫入 active `BodyPlan`。

---

## 3. 最小必要資訊集合

### 3.1 必填資訊（無法跳過）

以下資訊是系統計算 `recommended_target_kcal` 與 `safety_floor_kcal` 的最低需求：

| 欄位 | 用途 | 備註 |
|------|------|------|
| `sex` | 決定 `safety_floor_kcal` baseline | `male` / `female` / `prefer_not_to_say` |
| `current_weight_kg` | BMR 計算 | 允許粗略值 |
| `height_cm` | BMR 計算 | 允許粗略值 |
| `age_years` | BMR 計算 | 允許粗略值 |
| `goal_type` | 決定 deficit 方向 | `lose_weight` / `maintain` / `gain_weight` |

#### `goal_type` v1 scope 說明

v1 的產品核心是熱量赤字管理（calorie-deficit product core）。

正式規則：

- `lose_weight`：v1 完整支援，所有 rescue / calibration / recommendation 功能均可用
- `maintain`：v1 部分支援，intake logging 與 budget tracking 可用，但 rescue / calibration 的 proposal 邏輯以 `lose_weight` 為設計基準，`maintain` 使用者可能收到不完全適合的建議
- `gain_weight`：**v1 不完整支援**。intake logging 可用，但 rescue / calibration / recommendation 的邏輯均以赤字管理為前提，對 `gain_weight` 使用者可能產生不適當的建議。v1 應在 onboarding 時對 `gain_weight` 使用者顯示提示，說明目前功能以減重為主。

v1 不應因 `gain_weight` 而拒絕 onboarding，但應：

- 在 `BodyPlan` 中標記 `goal_type: gain_weight`
- 在 rescue / calibration trigger 評估時，若 `goal_type = gain_weight`，跳過 rescue trigger（不適用）
- 在 recommendation 中不強制套用 caloric deficit posture

### 3.2 強烈建議填寫（可跳過，但影響品質）

| 欄位 | 用途 | 跳過時的 fallback |
|------|------|-----------------|
| `activity_level` | TDEE 估算 | 預設採 `sedentary`（久坐） |
| `target_weight_kg` | 計算目標 deficit | 跳過時不顯示預計達標時間 |
| `weekly_target_rate_kg` | 決定每日 deficit 幅度 | 預設採 `0.5 kg/week` |

### 3.3 可選資訊（後續補充）

| 欄位 | 用途 |
|------|------|
| `preferred_name` | 個人化稱呼 |
| `dietary_restrictions` | 推薦過濾 |
| `quiet_hours` | proactive suppression |

---

## 4. `sex` 欄位的特殊處理

### 4.1 為什麼必填

`sex` 是決定 `safety_floor_kcal` 的唯一 canonical source。

根據 L3.4 與 L3.3B 的規定：

- 女性 baseline safety floor：`1200 kcal/day`
- 男性 baseline safety floor：`1500 kcal/day`

runtime 不可在 `BodyPlan.safety_floor_kcal` 缺值時自行推斷。

### 4.2 `prefer_not_to_say` 的處理

若使用者選擇 `prefer_not_to_say`：

- 系統採用較保守的 safety floor：`1500 kcal/day`
- 在 `BodyPlan` 中標記 `safety_floor_source: conservative_default`
- 不影響其他計算

---

## 5. 初始 `BodyPlan` Bootstrap 流程

### 5.1 計算順序

onboarding 資訊收集完成後，系統依以下順序計算初始值：

1. 計算 BMR（使用 Mifflin-St Jeor）：
   - 男性：`10 × weight_kg + 6.25 × height_cm - 5 × age + 5`
   - 女性：`10 × weight_kg + 6.25 × height_cm - 5 × age - 161`

2. 計算 TDEE（BMR × activity multiplier）：
   - `sedentary`：× 1.2
   - `lightly_active`：× 1.375
   - `moderately_active`：× 1.55
   - `very_active`：× 1.725

3. 計算每日 deficit：
   - `weekly_target_rate_kg × 7700 / 7`（每日 kcal deficit）

4. 計算 `raw_target_kcal`：
   - `TDEE - daily_deficit`

5. 套用 safety floor：
   - `recommended_target_kcal = max(safety_floor_kcal, raw_target_kcal)`

### 5.2 初始 `BodyPlan` proposal

計算完成後，系統產生一個 `BodyPlan` proposal，包含：

- `estimated_tdee`：步驟 2 的結果
- `safety_floor_kcal`：依 sex 決定
- `recommended_target_kcal`：步驟 5 的結果
- `target_rate`：使用者設定的 `weekly_target_rate_kg`
- `target_weight`：使用者設定的 `target_weight_kg`（若有）
- `plan_source`：`onboarding_bootstrap`
- `calibration_confidence`：`initial_estimate`

使用者確認後，才正式寫入 active `BodyPlan`。

### 5.3 初始 `DayBudgetLedger` 建立

`BodyPlan` 被接受後，系統為當日建立初始 `DayBudgetLedger`：

- `base_budget_kcal`：`recommended_target_kcal`
- `base_budget_source`：`body_plan_initial`
- `consumed_kcal`：`0`
- `effective_budget_kcal`：`recommended_target_kcal`

---

## 6. 分步驟 Onboarding

### 6.1 最小可用狀態

使用者只要完成 Section 3.1 的必填資訊，系統即可進入可用狀態。

### 6.2 步驟設計建議

v1 建議採兩步驟：

**Step 1（必填）**：
- `sex`
- `current_weight_kg`
- `height_cm`
- `age_years`
- `goal_type`

**Step 2（建議填，可跳過）**：
- `activity_level`
- `target_weight_kg`
- `weekly_target_rate_kg`

Step 2 跳過時，系統使用 Section 3.2 的 fallback 值繼續計算。

### 6.3 後續補充入口

使用者可在以下時機補充 onboarding 資訊：

- 在 chat 中直接說「我想更新我的目標」
- 在 UI 的設定頁面修改
- 系統在 calibration 流程中提示補充

### 6.4 Chat 與 UI 的同步規則

onboarding 的主要互動面是 UI 表單。Chat 是補充和確認的管道。

正式規則：

- UI 表單填完後，系統直接建立 `BodyPlan`，不需要 chat 確認步驟
- 若使用者在 chat 中說「我想改目標」「我的體重不對」，系統透過 `general_chat` workflow 引導使用者到 UI 設定頁修改，或直接在 chat 中收集新資訊並更新 `BodyPlan`
- UI 和 chat 的修改都走同一個 `BodyPlan` 更新路徑，不是兩套系統
- `BodyPlan` 更新後，`DayBudgetLedger` 的 `base_budget_kcal` 應同步更新（依 11:00 規則決定今日或明日生效）

---

## 7. Fallback Posture（跳過 Onboarding）

若使用者完全跳過 onboarding，系統應：

- 不建立 `BodyPlan`
- 不建立 `DayBudgetLedger`
- 仍允許 intake logging（meal thread 可建立）
- 在 Today UI 顯示「尚未設定目標」提示
- 在 intake response 中不顯示剩餘預算
- 不觸發 rescue / calibration flow
- 在使用者第一次問「我今天還能吃多少」時，引導進入 onboarding

---

## 8. Onboarding 完成後的系統狀態

onboarding 完成且使用者確認 `BodyPlan` proposal 後，系統應達到以下狀態：

- active `BodyPlan` 存在，`status: active`
- 當日 `DayBudgetLedger` 存在
- `CurrentBudgetView` 可正確回傳
- `ActiveBodyPlanView` 可正確回傳
- intake flow 可正常運作並顯示剩餘預算
- rescue trigger 可正常評估（有 safety floor 可用）

---

## 9. 與其他 specs 的對齊

### 對 L2

- onboarding 建立的 `BodyPlan` 必須符合 L2 Section 3.8 的最小欄位
- `safety_floor_kcal` 必須在 `BodyPlan` 建立時就設定，不可為 null

### 對 L3.3A

- onboarding bootstrap 的 `estimated_tdee` 是 `initial_estimate`，不是 `calibrated_operating_estimate`
- calibration 在 14 天觀察窗口後才可能升級為 `calibrated_operating_estimate`

### 對 L3.4

- rescue flow 依賴 `BodyPlan.safety_floor_kcal`，onboarding 未完成時不應觸發 rescue

### 對 L3.3B

- onboarding 的 `BodyPlan` proposal 走 proposal-first 流程，但不走 calibration proposal gate
- 這是 `plan_source: onboarding_bootstrap` 的特殊路徑

---

## 10. 測試情境

後續至少應覆蓋：

- 完整填寫必填資訊後，正確計算 `recommended_target_kcal`
- `sex: prefer_not_to_say` 時，`safety_floor_kcal` 採 `1500`
- 跳過 `activity_level` 時，TDEE 採 `sedentary` multiplier
- `raw_target_kcal` 低於 `safety_floor_kcal` 時，`recommended_target_kcal` 被 floor 截斷
- 使用者確認 proposal 後，`BodyPlan` 正確寫入 active state
- 使用者跳過 onboarding，intake 仍可運作但不顯示預算
- 跳過 onboarding 後問「我今天還能吃多少」，系統引導進入 onboarding

---

## 11. v1 Default Decisions

1. `activity_level` 跳過時預設 `sedentary`（× 1.2）
2. `weekly_target_rate_kg` 跳過時預設 `0.5 kg/week`
3. `sex: prefer_not_to_say` 時 `safety_floor_kcal` 採 `1500 kcal/day`
4. onboarding proposal 不走 calibration proposal gate，直接走 `plan_source: onboarding_bootstrap` 路徑
5. onboarding 完成後，當日 `DayBudgetLedger` 立即建立，不等到隔日
