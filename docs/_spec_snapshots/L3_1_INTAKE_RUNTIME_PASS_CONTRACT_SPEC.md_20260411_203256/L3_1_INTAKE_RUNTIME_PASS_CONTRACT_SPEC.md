# L3.1 Intake Runtime / Pass Contract Spec

## 1. 目的

本文件定義 intake 主流程的 canonical runtime contract。

它要回答：

- intake 主流程是否正式採 4-pass
- 每一 pass 的責任邊界
- 每一 pass 可讀哪些 objects / views
- 每一 pass 可輸出哪些 output classes
- clarify、tool round、proposal、commit request 分別在哪一層合法發生
- multi-turn correction、historical recall、occurred_at 處理如何進入主流程
- deterministic gate 在哪裡驗證，以及不能做什麼

本文件刻意不回答：

- prompt wording
- 每層 prompt section 結構
- 每層模型品牌與成本配置
- benchmark 與 eval 細節

---

## 2. Canonical Runtime Shape

### 2.1 正式 4-pass

intake 主流程正式採用：

1. `task_meal_link_pass`
2. `decision_pass`
3. `nutrition_resolution_pass`
4. `final_response_pass`

### 2.2 核心原則

- pass responsibility 不可合併
- `nutrition_resolution_pass` 是唯一可產生 kcal、item 組成、portion 評估的層
- `macro` 不是 pass 3 的 primary truth；由 deterministic layer 依 DB 下游推導
- 主流程預設 `default-commit`，但 commit 由 application layer 根據 `commit_request_candidate` 落地
- recommendation 不建立 intent state
- item-level correction 以 `MealItem` 為最小修正單位
- 單訊息多時段 intake 採 `Pass 1 先拆成多個 intake units`，每個 unit 各跑同一條 4-pass

補充治理規則：

- `task_meal_link_pass` 的 boundary / splitting responsibility 是 intake flow 的獨特守門層
- 若未來需要 simple mode collapse，必須採 `boundary-first collapse`
- 不可把 `task_meal_link_pass` 與 nutrition resolution 合併成單次黑箱推理
- `Pass 1 + Pass 2` 不可合併；唯一可壓縮的是 response 表現形式
- 關於 cross-domain pass policy，見 [`L6E LLM Pass Design Policy Spec`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md)

### 2.3 intake 主流程目標

主流程必須支援：

- 新餐點記錄
- 同 thread 補充
- correction
- multi-item meal
- 多訊息回補
- 歷史回溯修正
- occurred_at / local_date 歸帳
- default-commit
- item-level correction
- 與 ledger 的自動銜接

### 2.4 Logical Model Roles

intake 主流程的 pass 應優先對應以下 logical model roles：

- `task_meal_link_pass` -> `fast_router_model`
- `decision_pass` -> `fast_router_model`
- `nutrition_resolution_pass` -> `strict_reasoner_model`
- `final_response_pass` -> `response_writer_model`

若後續引入圖片 / 多模態 intake，應額外使用：

- `vision_parser_model`

---

## 3. 主流程輸入與最終輸出

### 3.1 主流程最小輸入

- `raw_user_input`
- `user_id`
- `message_event_id`
- `channel`
- `recorded_at`
- `timezone`
- `client_local_time`（可用時）
- `ActiveMealView`
- `RecentCommittedMealsView`
- `CurrentBudgetView`
- `ActiveBodyPlanView`
- 必要 recent messages
- selected retrieval context

其中 `ActiveBodyPlanView` 可包含 calibration-derived 的 `intake_estimation_bias_posture`，但它只應作為 intake runtime 的受控輔助訊號。

### 3.2 主流程最終輸出

主流程結束後至少應產出：

- `task_meal_link_result`
- `decision_result`
- `nutrition_result`
- `final_response_result`
- `commit_request_candidate | no_commit`
- `trace_envelope`
- `view_refresh_hints`

---

## 4. Pass 1: `task_meal_link_pass`

### 4.1 目標

判斷這一回合是否為 intake-related，並決定它與哪個 `MealThread` 有關。

### 4.2 責任

- 判斷是否為 intake-related
- 判斷是新事件、補充、修正、歷史回溯或非 intake
- 連到既有 `MealThread` 或建立新 thread candidate
- 解析 occurred-at 語意
- 若單訊息含多個不同時段 / 不同事件，先拆成多個 intake units

### 4.3 可讀

- `MessageEvent`
- `ActiveMealView`
- `RecentCommittedMealsView`
- 最近對話
- 時間上下文

### 4.4 必須輸出

- `intent`
- `scope`
- `meal_link_action`
- `target_meal_thread_id`
- `boundary_reason`
- `clarification_blocking`
- `occurred_at_interpretation`
- `time_reference_confidence`
- `intake_units[]`

### 4.5 關鍵規則

- 一則訊息內多食物但同事件：單 unit，多 `MealItem`
- 一則訊息內多時段飲食：多 unit，後續各自跑主流程
- `MealThread` 是飲食事件，不是訊息，也不是單一食物
- 此 pass 負責 splitting boundary，不負責 nutrition resolution

### 4.6 不可做的事

- 不輸出 kcal / macro
- 不建立 proposal
- 不直接 commit canonical state

---

## 5. Pass 2: `decision_pass`

### 5.1 目標

決定下一步是：

- `run_clarify`
- `run_tool_lookup`
- `run_nutrition_resolution`

### 5.2 責任

- 決定 `clarify / tool_lookup / nutrition_resolution`
- 判斷 clarify 是否 blocking
- 判斷 rough estimate 是否足夠可用

### 5.3 可讀

- `task_meal_link_result`
- selected evidence summary
- `ActiveMealView`
- retrieval state
- exact / anchor / context evidence

### 5.4 必須輸出

- `next_action`
- `tool_plan`
- `unresolved_info`
- `clarify_is_blocking`
- `can_proceed_without_clarify`
- `decision_confidence`
- `response_mode_hint`

### 5.5 關鍵規則

- 只有完全不可估或 boundary 真正不清才 blocking
- 不輸出 nutrition numbers
- 不建立 recommendation intent state
- 若存在 `intake_estimation_bias_posture`，這層可用它提高 clarify priority 或標記高風險 case，但不可直接改寫 nutrition truth
- external lookup 的合法入口在此 pass 被決定

### 5.6 不可做的事

- 不輸出 final user wording
- 不發出 commit request
- 不直接重寫上游 boundary

---

## 6. Pass 3: `nutrition_resolution_pass`

### 6.1 目標

產生 intake 主流程唯一合法的 nutrition truth，並形成 commit-ready meal snapshot。

### 6.2 責任

- 產生總熱量
- 產生 `MealItem` 級組成
- 產生 portion reasoning
- 形成 `MealVersion` 與 `MealItem[]` 映射 payload
- 判斷 `commit_readiness`

### 6.3 可讀

- `task_meal_link_result`
- `decision_result`
- selected evidence
- `ActiveMealView`
- `RecentCommittedMealsView`
- occurred-at interpretation
- optional `intake_estimation_bias_posture`
- user asserted statements

### 6.4 必須輸出

- `resolution_mode`
- `resolution_basis`
- `confidence`
- `answer_payload`
- `meal_items_payload`
- `unresolved_info`
- `state_transition_hint`
- `commit_readiness`

### 6.5 正式規則

- 只輸出 `總熱量 + MealItem 級組成 + portion reasoning`
- `macro` 不在 pass 3 作為 primary truth 輸出
- `MealVersion` 是完整 snapshot，不是 delta
- correction 產生完整新 snapshot
- `MealItem` 是 item-level correction 基本單位
- `intake_estimation_bias_posture` 第一版只可影響 clarify / risk / conservatism posture，不可作為全局數字覆寫指令

### 6.6 `MealItem` 分類規則

pass 3 可輸出 `MealItem` 分類資訊，分兩層：

- canonical 粗分類
  - `item_kind`
  - `staple_type`
  - `item_role`
  - `classification_confidence`
- optional 細分類
  - `cuisine_family`
  - `preference_tags`

細分類缺失不得阻止 commit，但可供後續 recommendation 聚合偏好。

### 6.7 不可做的事

- 不輸出 final user phrasing
- 不做 ledger mutation
- 不做 DB write
- 不建立 recommendation intent state

---

## 7. Pass 4: `final_response_pass`

### 7.1 目標

根據上游結果產生自然語言，並最多提出一個 outward follow-up。

### 7.2 責任

- 呈現最新結果
- correction 情境下讓使用者知道已更新
- 最多提出一個 outward follow-up

### 7.3 可讀

- `task_meal_link_result`
- `decision_result`
- `nutrition_result`
- minimal UI hint context

### 7.4 必須輸出

- `reply_text`
- `asked_follow_up`
- `ui_hints`

### 7.5 正式規則

- 不新增 kcal
- 不新增 boundary
- 不新增 unresolved slots
- 不建立 proposal
- 對外預設以 `MealItem` 級呈現，不做 ingredient 級細拆，除非使用者主動要求

---

## 8. Deterministic / Commit Contract

### 8.1 合法 deterministic 責任

允許：

- schema parsing
- one bounded retry / self-correction round
- exact-label truth verification
- kcal / macro arithmetic sanity check
- version chain bookkeeping
- ledger arithmetic
- trace logging
- downstream macro derivation

不允許：

- 重判 meal boundary
- 重判 clarify necessity
- 重判 exactness
- 改寫最終語意回覆

### 8.2 `macro` 規則

正式採用：

- pass 3 只輸出 `estimated_kcal + MealItem 組成 + portion reasoning`
- downstream deterministic layer 根據 DB 推導 `macro_breakdown`
- 若 macro 推導出的 kcal 無法與 pass 3 的 kcal 落在合理區間，則 `macro unavailable`
- `macro derivation fail` 屬於 `derived-view failure`，不應反向污染 meal commit truth

### 8.3 failure 分級

#### `commit-critical failure`

例：

- pass 3 核心 payload 矛盾
- 核心欄位缺失
- version payload 不可落地

處理：

- bounded self-correction
- 仍失敗則不 commit

#### `derived-view failure`

例：

- macro 對不齊
- 低優先欄位推導失敗

處理：

- 降級為 unavailable
- 不阻止 meal commit

### 8.4 `commit_request_candidate`

至少包含：

- target `MealThread`
- new `MealVersion`
- `MealItem[]`
- `commit_source`
- `version_reason`
- `reason_payload`
- `occurred_at`
- `occurred_at_local`
- `local_date`
- linked `MessageEvent`
- supersession target（若為 correction）
- linked ledger effect hint

### 8.5 application layer 落地後

- 建立或更新 `MealThread`
- 建立新 `MealVersion`
- 建立 `MealItem[]`
- supersede 舊 active version（若為 correction）
- 建立 `LedgerEntry(meal_consumption)`
- refresh `CurrentBudgetView`

---

## 9. Important Types / Interfaces

L3.1 應正式化下列 contract types：

- `IntakeUnit`
- `TaskMealLinkResult`
- `DecisionPassResult`
- `NutritionResolutionResult`
- `FinalResponseResult`
- `CommitRequestCandidate`
- `MacroDerivationResult`
- `DeterministicValidationResult`

新增或補強的重要欄位：

- `TaskMealLinkResult.intake_units[]`
- `NutritionResolutionResult.meal_items_payload`
- `NutritionResolutionResult.commit_readiness`
- `MealItem.item_kind`
- `MealItem.staple_type`
- `MealItem.item_role`
- `MealItem.classification_confidence`
- `MealItem.cuisine_family`（optional）
- `MealItem.preference_tags[]`（optional）
- `CommitRequestCandidate.version_reason`
- `CommitRequestCandidate.reason_payload`

---

## 10. 測試情境

後續實作至少應覆蓋：

- 單訊息多食物同事件，形成 1 個 intake unit、1 個 `MealThread`、多個 `MealItem`
- 單訊息多時段飲食，Pass 1 先拆成多個 intake units
- correction 僅改單一 `MealItem`，其他 item 保持不變
- correction 建立新 `MealVersion`，舊版本保留
- pass 3 輸出 kcal 與 item 組成，但不直接輸出 conversational macro truth
- deterministic 成功推導 macro，且 kcal 對齊合理區間
- deterministic macro fail 時，meal 仍 commit，但 UI macro 不顯示
- commit-critical failure 觸發 bounded self-correction，仍失敗則不 commit
- 跨午夜補記時，以 `occurred_at / local_date` 正確歸帳
- 對外回覆預設 item 級，不展開 ingredient 級
- `MealItem` 粗分類成功供後續 recommendation 聚合偏好
- 細分類缺失不阻止 commit

---

## 11. 與 L0 / L1 / L2 的對齊

### 對 L0 的補充

- recommendation 依賴歷史 `MealItem` 分類聚合出的偏好訊號，而不是 recommendation intent state

### 對 L1 的補充

- `nutrition_resolution_pass` 可輸出 `MealItem` 粗分類；細分類可選
- deterministic layer 可做 macro derivation 與 derived-view 降級，但不得改寫 nutrition commit truth

### 對 L2 的補充

- `MealItem` 欄位與型別層次：
  - `item_kind`
  - `staple_type`
  - `item_role`
  - `classification_confidence`
  - `cuisine_family`（optional）
  - `preference_tags`（optional）
- 補 `reason_payload` 與 `MacroDerivationResult` 相關欄位概念

---

## 12. 實作假設

- intake 主流程正式採 4-pass
- 單訊息多時段 intake 採 Pass 1 預拆 units，而不是 Pass 3 多 thread fan-out
- `MealItem` 是最小必要 correction 粒度
- `macro` 是 downstream derived view，不是 pass 3 的 primary truth
- recommendation 偏好學習依賴 `MealItem` 歷史分類，不引入 recommendation intent state
- prompt contract 留到 `L3.5`
- 完整 eval 留到 `L5`
- provider model IDs 不在本層定義；本層只綁 logical model roles
