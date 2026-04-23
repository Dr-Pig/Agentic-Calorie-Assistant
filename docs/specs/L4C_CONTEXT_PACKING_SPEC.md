# L4C Context Packing Spec

## 1. 目的

這份 spec 定義 retrieval 後的資訊如何被組裝成 prompt context pack。

它回答：

- 哪些資訊該進 prompt
- 哪些該先摘要再進 prompt
- context block 的排序
- token 壓力下先刪什麼
- shared fragment 與 dynamic context 如何組裝

**關於 Promotion 與 Demotion 規則**：請參閱 [L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md](./L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md)。

---

## 2. 核心原則

### 2.1 Context 不是全量資料 dump

prompt context 應只包含：

- 當前任務真正需要的資訊
- 已整理好的 summary
- 最短必要 transcript

### 2.2 先放穩定，後放動態

這點需和 `L3.5` 的 cache-aware prompt assembly 對齊。

### 2.3 summary-first

能用 summary 解決，就不要塞 raw history。

### 2.4 context 要帶 freshness 與負面訊號

對 recommendation / proactive / calibration 特別重要的 context，不只要帶正向偏好，也要帶：

- freshness / staleness
- negative preference
- recent explicit user override

### 2.5 Atomic Context Blocks

context packing 不應隨意在語意或狀態依附關係中間切斷。

某些上下文必須被視為 atomic block，一起保留、一起裁切、一起壓縮。

至少包括：

- `proposal + user response`
- `tool call + tool result`
- `clarification question + clarification answer`
- `rescue proposal + acceptance/rejection`
- `correction request + target meal reference`

若只保留其中一半，模型很容易失去語意依附關係。

---

## 3. Standard Context Pack Shape

建議所有 flow 的 dynamic context pack 至少遵守：

1. current task object
2. active shared views
3. derived summaries
4. selected evidence
5. short transcript
6. fallback metadata

---

## 4. Intake Context Pack

應優先包含：

- `raw_user_input`
- `TaskMealLinkResult` 上游結果
- `ActiveMealView`
- `RecentCommittedMealsView`
- selected evidence
- optional structured `intake_estimation_bias_posture`

應避免：

- 長篇 transcript
- 無關 proposal history

---

## 5. Recommendation Context Pack

應優先包含：

- `CurrentBudgetView`
- `ActiveBodyPlanView`
- `PreferenceProfileSummary`
- `GoldenOrderSummary`
- candidate pool summary
- optional `location_context`

應避免：

- 全量 meal history
- 全量 body observation

---

## 6. Calibration Context Pack

應優先包含：

- `ActiveBodyPlanView`
- body observation window summary
- intake completeness summary
- adherence summary
- rescue history summary

應避免：

- 逐筆 meal detail
- 冗長 transcript

---

## 7. Rescue Context Pack

應優先包含：

- `CurrentBudgetView`
- recent overshoot summary
- `RescueHistorySummary`
- `AdherenceSummary`
- relevant recommendation posture

---

## 8. Token Pressure Policy

當 token 壓力上升時，應依序刪減：

1. 長 transcript
2. raw historical records
3. 低價值 explanation text
4. 非必要 fallback metadata

不應先刪：

- current task object
- active shared views
- safety-critical guardrails
- schema-binding context
- atomic context blocks

---

## 9. Structured Context Blocks

建議 dynamic context 儘量採結構化 block，而不是自由散文。

例如：

- `CURRENT_BUDGET`
- `ACTIVE_BODY_PLAN`
- `PREFERENCE_SUMMARY`
- `NEGATIVE_PREFERENCES`
- `MEMORY_FRESHNESS`
- `RECENT_RESCUE_HISTORY`
- `BIAS_POSTURE`

這樣有利於：

- prompt consistency
- model parsing stability
- cache-aware assembly

### 9.2 Atomic Block Preservation

若 context 需要壓縮或裁切：

- 優先裁掉非原子、低價值、可重建的說明文字
- 不要拆散已標記的 atomic block

必要時應把 atomic block 先摘要成更短的單一 block，再保留其語意完整性。

### 9.1 Markdown 結構化原則

context format 可使用 Markdown，但應偏向結構化 Markdown block，而不是一般敘述文。

較佳形式例如：

- `## CURRENT_BUDGET`
- `## PREFERENCE_SUMMARY`
- `## NEGATIVE_PREFERENCES`
- `## MEMORY_FRESHNESS`

而不是長段散文描述。

---

## 10. v1 Default Decisions

1. transcript block 最大長度：
   - intake / recommendation / rescue 預設最多 `6` 則 recent turns
   - calibration 預設最多 `4` 則 direct-relevant turns
   - 超出時先摘要，不直接塞長 transcript
2. candidate pool summary 最大展開量：
   - recommendation candidate summary 預設最多展開 `5` 筆
   - rescue / calibration option summary 預設最多展開 `3` 筆
3. token 壓力下的 aggressive compaction：
   - 允許，但不得破壞 atomic block
   - 優先壓縮 explanatory prose、低新鮮度 pattern、與可重建 raw transcript
   - 不得壓掉：
     - active object summary
     - current budget / current posture
     - confirmed negative preference
     - current proposal / rescue atomic block

---

## 11. Token Pressure Threshold Policy

### 11.1 觸發條件

aggressive compaction 不應在每次 prompt assembly 時都執行，應有明確觸發條件。

v1 預設採以下 threshold：

| 情境 | 觸發條件 |
|------|---------|
| 一般 compaction | 預估 prompt tokens 超過目標 context window 的 `60%` |
| aggressive compaction | 預估 prompt tokens 超過目標 context window 的 `80%` |
| 強制裁切 | 預估 prompt tokens 超過目標 context window 的 `90%`，此時允許裁掉低優先 transcript，但不得裁掉 atomic block |

### 11.2 token 估算時機

- token 估算應在 context pack assembly 完成後、送入模型前執行
- 若估算結果超過 `60%` threshold，先嘗試 summary 替換
- 若仍超過 `80%`，啟動 aggressive compaction
- 若仍超過 `90%`，執行強制裁切並在 trace 中記錄 `context_truncated: true`

### 11.3 trace 要求

每次 prompt assembly 應在 trace envelope 中記錄：

- `estimated_prompt_tokens`
- `compaction_triggered`: `none` / `summary` / `aggressive` / `forced`
- `truncated_blocks[]`：被裁掉的 block 名稱列表
- `context_window_target`：本次使用的 context window 目標值

### 11.4 `context_window_target` 定義

`context_window_target` 是 prompt assembly 時採用的 context window 上限，單位為 tokens。

它的 canonical source 是 provider adapter 層（`L6A / L6B`），由 logical model role 映射決定：

- `fast_router_model`：預設 `context_window_target = 32000`
- `strict_reasoner_model`：預設 `context_window_target = 64000`
- `response_writer_model`：預設 `context_window_target = 32000`

規則：

- `context_window_target` 不應在 L4C 層寫死為具體數字，而應由 provider adapter 在 runtime 注入
- L4C 的 threshold policy（60% / 80% / 90%）是相對比例，乘以 `context_window_target` 得到絕對 token 數
- 若 provider adapter 未提供 `context_window_target`，L4C 應使用保守 fallback：`32000`
