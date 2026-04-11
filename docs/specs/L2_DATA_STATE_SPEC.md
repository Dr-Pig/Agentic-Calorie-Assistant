# L2 Data / State Spec

## 1. 目的

本文件定義 L1 之下的資料與狀態模型。

L2 要回答：

- 每個 canonical object 的最小欄位集合
- 哪些欄位是 base truth，哪些是 derived view
- version chain 如何表示
- ledger layer 如何表示
- proposal container / option 如何表示
- proactive trigger 與 suppression state 如何表示
- runtime 與 UI 應依賴哪些 materialized / assembled views

本文件刻意不回答：

- 最終 DB migration 實作
- API endpoint 最終 shape
- LLM pass payload 最終 JSON
- UI component 細節

---

## 2. Data Modeling Principles

### 2.1 Canonical object 與 derived view 分離

L2 必須區分：

- `canonical records`
- `derived views`

canonical records 是正式持久化、可追溯、可版本化的真實資料。

derived views 是由 canonical records 聚合、投影或 materialize 後提供給 runtime / UI 消費的讀取模型。

### 2.2 Observation / interpretation / commit 分離

L2 不可把下列內容混在同一個 blob 中：

- 使用者原始觀測
- runtime 候選理解
- 正式 committed state

### 2.3 Version chain 是一級概念

version history 不是附註，而是正式資料模型的一部分。

### 2.4 `occurred_at` 與 `recorded_at` 分離

L2 必須同時支持：

- `occurred_at`
- `recorded_at`
- `occurred_at_local`
- `local_date`
- `timezone`

否則補記、跨午夜與 UI 歸帳一定會出錯。

### 2.5 `meal_thread` 的粒度是飲食事件

`meal_thread` 不等於：

- 一則訊息
- 單一食物
- 早餐 / 午餐 / 晚餐固定槽位

`meal_thread` 代表的是一次可被共同討論與修正的飲食事件。

### 2.6 `MealItem` 是 thread 內的最低必要細粒度

同一個 `meal_thread` 可以包含多個 `MealItem`。

`MealItem` 承接：

- 同一事件內的多食物記錄
- item-level correction
- item-level removal

現階段不額外引入 `ConsumptionSegment`；若未來需要處理同一份食物被分時吃的高精度場景，再新增。

---

## 3. Canonical Objects

### 3.1 `MessageEvent`

代表一筆原始互動輸入，不等於 meal event。

最小欄位：

- `message_event_id`
- `user_id`
- `channel`
- `event_type`
- `role`
- `content`
- `created_at`
- `trace_id`
- `linked_meal_thread_ids`
- `linked_proposal_ids`

規則：

- 一則訊息可關聯 0..N 個 `MealThread`
- 是否拆成多個 thread，由 runtime boundary 決定
- `MessageEvent` 是 audit source，也是 retrieval source

### 3.2 `MealThread`

代表一次可被共同討論與修正的飲食事件。

最小欄位：

- `meal_thread_id`
- `user_id`
- `status`
- `active_version_id`
- `occurred_at`
- `occurred_at_local`
- `local_date`
- `recorded_at`
- `timezone`
- `created_from_message_event_id`
- `latest_commit_source`
- `followup_status`
- `pending_question_key`
- `pending_question_text`
- `last_followup_at`

規則：

- `MealThread` 的粒度是飲食事件，不是訊息，也不是單一食物
- 一個 thread 內可以有多個 `MealItem`
- 不綁早餐 / 午餐 / 晚餐；這些是 display label，不是 primary data model

### 3.3 `MealVersion`

代表一個 `MealThread` 的正式版本快照。

最小欄位：

- `meal_version_id`
- `meal_thread_id`
- `parent_version_id`
- `version_reason`
- `meal_title`
- `estimated_kcal`
- `protein_g`
- `carb_g`
- `fat_g`
- `estimate_mode`
- `confidence`
- `evidence_ids_used`
- `evidence_summary`
- `user_asserted_overrides`
- `commit_source`
- `committed_at`
- `raw_user_input`
- `normalized_user_input`
- `is_active`
- `superseded_at`
- `superseded_reason`

規則：

- nutrition 結果必須 snapshot 化
- correction 永遠建立新 version，不覆寫舊 version
- `MealVersion` 聚合其下 `MealItem` 的當前結果

### 3.4 `MealItem`

代表 thread 內可被獨立修正的食物項目。

最小欄位：

- `meal_item_id`
- `meal_version_id`
- `item_rank`
- `item_name`
- `quantity_hint`
- `estimated_kcal`
- `protein_g`
- `carb_g`
- `fat_g`
- `item_kind`
- `staple_type`
- `item_role`
- `classification_confidence`
- `cuisine_family`
- `preference_tags`
- `item_confidence`
- `evidence_ids_used`
- `user_asserted_override`
- `consumption_note`
- `occurred_at_override`
- `is_removed`

規則：

- 同一餐中的臭豆腐、紅茶、炒飯可以是三個 `MealItem`
- 使用者修正「紅茶我沒喝」時，只需改對應 `MealItem`
- `MealItem` 是 item-level correction 的基本單位
- `item_kind / staple_type / item_role / classification_confidence` 屬於 canonical 粗分類
- `cuisine_family / preference_tags` 屬於 optional 細分類，可供 recommendation 聚合偏好，但缺失不得阻止 commit

### 3.5 `DayBudgetLedger`

代表某日有效預算狀態。

最小欄位：

- `ledger_id`
- `user_id`
- `local_date`
- `timezone`
- `base_budget_kcal`
- `base_budget_source`
- `consumed_kcal`
- `rescue_overlay_total`
- `calibration_adjustment_total`
- `effective_budget_kcal`
- `remaining_kcal`
- `recomputed_at`
- `active_policy_version`

規則：

- `DayBudgetLedger` 可作 materialized snapshot
- TodayPage 讀此物件，不直接掃全量 thread

### 3.6 `LedgerEntry`

代表一筆影響 budget 的正式 entry。

最小欄位：

- `ledger_entry_id`
- `ledger_id`
- `entry_type`
- `delta_kcal`
- `source_object_type`
- `source_object_id`
- `source_version_id`
- `entry_status`
- `effective_from`
- `effective_to`
- `created_at`

規則：

- committed meal 產生 `meal_consumption`
- rescue accept 產生 `rescue_overlay`
- calibration accept 產生 `calibration_adjustment`

### 3.7 `BodyObservation`

最小欄位：

- `body_observation_id`
- `user_id`
- `observation_type`
- `value`
- `unit`
- `occurred_at`
- `recorded_at`
- `timezone`
- `source_channel`
- `raw_input`

### 3.8 `BodyPlan`

代表當前生效的體態策略版本。

最小欄位：

- `body_plan_id`
- `user_id`
- `status`
- `active_from`
- `active_to`
- `goal_type`
- `target_rate`
- `target_weight`
- `estimated_tdee`
- `safety_floor_kcal`
- `calibration_confidence`
- `plan_source`
- `accepted_proposal_id`

規則：

- `BodyPlan` 要版本化
- active plan 與 proposed next plan 分離
- `safety_floor(user)` 的 canonical deterministic source 應來自 active `BodyPlan.safety_floor_kcal`
- 若 active `BodyPlan.safety_floor_kcal` 尚未就緒，runtime 不可隱性猜測 sex/gender 後自行決定 floor

### 3.9 `ProposalContainer`

最小欄位：

- `proposal_id`
- `user_id`
- `proposal_type`
- `source_object_type`
- `source_object_id`
- `trigger_id`
- `status`
- `presented_at`
- `accepted_option_id`
- `rejected_reason`
- `expired_at`
- `presentation_policy`
- `default_option_id`
- `display_mode`
- `created_by`
- `created_at`

### 3.10 `ProposalOption`

最小欄位：

- `proposal_option_id`
- `proposal_id`
- `option_rank`
- `option_label`
- `option_summary`
- `effect_type`
- `effect_payload`
- `guardrail_summary`
- `is_default`
- `is_user_modified`
- `accepted_at`

規則：

- 採 `typed metadata + constrained JSON payload`
- `effect_payload` 允許半結構化，但 shape 必須由 `effect_type` 約束
- 不是任意 JSON blob

補充概念：

- 後續 runtime 應定義 `MacroDerivationResult`，作為 `macro_breakdown` 是否可顯示的 deterministic 下游結果

### 3.11 `ProactiveTrigger`

最小欄位：

- `trigger_id`
- `user_id`
- `trigger_type`
- `target_object_type`
- `target_object_id`
- `eligibility_reason`
- `status`
- `cooldown_until`
- `suppression_reason`
- `preference_segment`
- `linked_proposal_id`
- `fired_at`
- `acknowledged_at`
- `dismissed_at`

---

## 4. Object Relationships

正式關係：

- `MessageEvent 0..N -> MealThread`
- `MealThread 1 -> N MealVersion`
- `MealVersion 1 -> N MealItem`
- `DayBudgetLedger 1 -> N LedgerEntry`
- `ProposalContainer 1 -> N ProposalOption`
- `ProactiveTrigger 0..1 -> 1 ProposalContainer`
- `ProposalContainer accept -> BodyPlan / LedgerEntry / MealThread`（依 type 而定）

關鍵規則：

- `MessageEvent` 不主導 thread 粒度
- `MealItem` 是 thread 內細粒度，不是獨立 thread 的預設替代品
- 是否拆多 thread，只由 temporal / semantic boundary 決定

---

## 5. 時間語意

L2 必須同時保留：

- `occurred_at`
- `recorded_at`
- `occurred_at_local`
- `local_date`
- `timezone`

規則：

- dashboard 與 ledger 一律以 `local_date` 為抓取主鍵之一
- 補記與跨午夜歸帳以 `occurred_at` / 使用者主觀時間為準
- `recorded_at` 只反映系統接收時間

---

## 6. Derived Views

至少要有：

- `ActiveMealView`
- `RecentCommittedMealsView`
- `CurrentBudgetView`
- `ActiveBodyPlanView`
- `OpenProposalsView`
- `ProactiveStatusView`

其中 `ActiveBodyPlanView` 可包含非 canonical 的 calibration summary，例如：
- `operating_expenditure_estimate`
- `intake_estimation_bias_posture`
- 這些欄位屬於 derived calibration read model，不要求直接作為新 canonical object

其中：

- `CurrentBudgetView` 建議 materialized
- `ActiveMealView` 可在 runtime assemble
- `OpenProposalsView` 應直接支援 chat / UI 共用

---

## 7. 與現有 repo 的對齊

### 現有概念對應

- 現有 `MealLog`
  - 在 L2 中應提升為 `MealThread + MealVersion` 兩層概念
- 現有 `parent_log_id`
  - 可作為 version chain 的前身
- 現有 `MessageBuffer`
  - 在 L2 中應提升為 `MessageEvent`
- 現有 `EstimatePayload`
  - 應視為 runtime trace / response envelope，不是 canonical object
- 現有 `NutritionResolutionResult`
  - 應視為產生 `MealVersion snapshot` 的上游結果，而不是 canonical data model

---

## 8. 測試情境

後續實作至少應覆蓋：

- 一則訊息記多個食物，形成一個 `MealThread` 與多個 `MealItem`
- 一則訊息同時描述不同時段飲食，形成多個 `MealThread`
- 修正單一 item 不影響同 thread 其他 item
- correction 建立新 `MealVersion`，舊版本保留
- committed meal 自動產生 `LedgerEntry(meal_consumption)`
- rescue / calibration accept 產生對應 `LedgerEntry`
- 跨午夜補記仍正確落到 `local_date`
- 主觀時間敘述覆蓋系統接收時間
- UI 危險修改通過 guard 後成為新 version
- proposal option 以 `effect_type + constrained payload` 成功映射到 canonical commit

---

## 9. 實作假設

- `MealThread` 是飲食事件層，不是訊息層，也不是單 item 層
- `MealItem` 是最低必要細粒度，暫不額外引入 `ConsumptionSegment`
- 若未來確實需要處理同一份食物分時吃的高精度場景，再新增 `ConsumptionSegment`
- `ProposalOption.effect_payload` 前期可半結構化，但必須受 `effect_type` 約束
- `CurrentBudgetView` 為了 TodayPage 體驗，前期採 materialized snapshot
