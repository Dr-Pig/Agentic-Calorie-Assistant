# L3.5 Prompt Contract Spec

## 1. 目的

這份 spec 定義各 runtime flow 的 prompt contract。

它回答：

- 每個 flow / pass 的 prompt 應包含哪些固定區塊
- 哪些內容屬於 stable instruction
- 哪些內容屬於 dynamic context
- 哪些 shared views 可以進 prompt
- 哪些內容必須結構化輸出
- prompt 應如何與 deterministic gate、tool contract、trace contract 對齊
- 哪些事情 prompt 不能做

它暫時不回答：

- 最終模型品牌與成本配置
- 最終 token budget 數字
- benchmark implementation
- provider-specific prompt syntax tricks

---

## 2. Prompt Contract 的定位

### 2.1 Prompt Contract 不是產品 spec

L0-L3.4 定的是產品能力、資料、runtime ownership、flow policy。

`L3.5` 定的是：

- runtime layer 最後如何被 prompt 餵進模型
- 模型應看到什麼
- 模型不能看到什麼
- 模型要回什麼格式

### 2.2 Prompt Contract 不是 prompt 文案大全

這份先定的是 contract，不是最後每個字怎麼寫。

先定：

- prompt 區塊
- context pack 結構
- output schema 類型
- forbidden behavior

之後才細化 prompt wording。

---

## 3. 共通 Prompt Shape

所有 flow 的 prompt 至少都應遵守同一個大結構：

1. `Role / Objective`
2. `Task Boundary`
3. `Allowed Inputs`
4. `Required Outputs`
5. `Rules / Guardrails`
6. `Dynamic Context`
7. `Schema Reminder`
8. `Failure / Abstain Policy`

### 3.1 `Role / Objective`

定義這一 pass 的唯一任務。

### 3.2 `Task Boundary`

明確說：

- 你只負責什麼
- 你不負責什麼

### 3.3 `Allowed Inputs`

列出這一 pass 可以讀的 views / evidence / metadata。

### 3.4 `Required Outputs`

列出它必須回的 schema 欄位。

### 3.5 `Rules / Guardrails`

寫死關鍵邊界。

### 3.6 `Dynamic Context`

真正執行當下的 context pack。

### 3.7 `Schema Reminder`

提醒模型輸出只能符合哪個 contract type。

### 3.8 `Failure / Abstain Policy`

告訴模型何時要輸出：

- `needs_clarification`
- `cannot_decide`
- `no_proposal`
- `monitor_only`

---

## 4. Prompt Layer Types

### 4.1 `System Prompt Layer`

最穩定的核心身份與全局規則。

### 4.2 `Flow Prompt Layer`

針對某條 flow 固定的任務定義。

### 4.3 `Pass Prompt Layer`

某一個 pass 的局部責任與輸出要求。

### 4.4 `Dynamic Context Layer`

本次執行的 actual runtime payload。

---

## 4A. Logical Model Role Layer

prompt contract 不應直接綁 provider model ID，而應先綁 logical model roles。

v1 統一 vocabulary：

- `fast_router_model`
- `strict_reasoner_model`
- `response_writer_model`
- `vision_parser_model`

規則：

- `L3.x` prompt 只應依賴 logical model role
- provider model IDs 與成本 / 延遲取捨留給 adapter / L6A / L6B

## 5. 共通 Guardrails

所有 prompt 都應共享至少這些 guardrails：

- 不可把 derived view 當 canonical truth 改寫
- 不可在未被授權的 flow 中產生 proposal
- 不可在未被授權的 pass 中產生 commit decision
- 不可把 recommendation 當 intake state
- 不可把 calibration confidence 不足時硬說成 high-confidence mismatch
- 不可用自由文字繞過 schema contract
- 不可省略 required output fields

---

## 6. Fragment Ordering Policy

為了提高穩定性與 prompt cache 命中率，prompt assembly 應固定遵守以下順序：

1. `system / north star fragment`
2. `global guardrail fragments`
3. `flow fragment`
4. `pass fragment`
5. `shared policy fragments`
6. `schema fragment`
7. `dynamic context`

### 6.1 原則

- 越穩定的 fragment，越應放在前面
- 越常變動的 context，越應放在後面
- 不應把高變動欄位插到前綴區破壞 cache hit

### 6.2 共享 policy fragments 範例

- `product_north_star_fragment`
- `proposal_vs_commit_fragment`
- `derived_view_boundary_fragment`
- `single_primary_option_fragment`
- `time_policy_fragment`
- `safety_floor_fragment`
- `no_intent_state_fragment`

---

## 7. Cache-Aware Prompt Assembly

`L3.5` 應明確採 cache-aware prompt assembly。

### 7.1 核心原則

- 穩定前綴優先
- 動態後綴後置
- 共用 fragment 盡量避免重排
- schema 位置盡量穩定

### 7.2 應優先穩定化的內容

- system identity
- product north star
- flow-level rules
- pass boundary
- shared policy fragments
- structured output schema

### 7.3 應後置的內容

- user message
- selected evidence
- current budget values
- current proposal values
- latest dynamic summaries

### 7.4 v1 token policy

v1 不先寫死 token budget 數值，但應保留欄位與 trace 能力，以便後續觀察：

- total prompt tokens
- cached tokens / cache hit
- latency
- pass-level token distribution

---

## 8. Structured Bias Posture Injection

`intake_estimation_bias_posture` 不應以自由文字暗示注入 prompt。

應採：

- structured bias posture injection

### 8.1 禁止形式

不建議：

- 「你最近都高估了」
- 「你之前常常低估飲料，所以這次調高一點」

這種自由文字暗示容易讓模型越權改數字。

### 8.2 建議形式

應以低自由度、可追蹤的結構化欄位注入，例如：

```json
{
  "bias_posture": "likely_underestimate",
  "scope": ["sweet_drinks", "small_snacks"],
  "confidence": 0.62,
  "allowed_effects": [
    "clarify_priority",
    "risk_tagging",
    "estimate_conservatism"
  ]
}
```

### 8.3 規則

- bias posture 不可直接作為全局數字覆寫命令
- bias posture 只能在被允許的 pass 中可見
- bias posture 必須帶 scope 與 confidence
- bias posture 應明示 `allowed_effects`

---

## 9. Intake Prompt Contract

對應 [`docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md)

### 9.1 `task_meal_link_pass`

應讀：

- `raw_user_input`
- `MessageEvent`
- `ActiveMealView`
- `RecentCommittedMealsView`
- recent message snippet
- time context

禁止：

- 不算 kcal
- 不寫 final reply
- 不產 proposal

輸出：

- `TaskMealLinkResult`

### 9.2 `decision_pass`

應讀：

- `task_meal_link_result`
- evidence summary
- retrieval state
- optional structured `intake_estimation_bias_posture`

禁止：

- 不產 nutrition numbers
- 不寫 final reply

輸出：

- `DecisionPassResult`

### 9.3 `nutrition_resolution_pass`

應讀：

- prior pass outputs
- selected evidence
- `ActiveMealView`
- `RecentCommittedMealsView`
- optional structured `intake_estimation_bias_posture`

禁止：

- 不直接 commit
- 不直接輸出 macro truth
- 不以 bias posture 全局覆寫數字

輸出：

- `NutritionResolutionResult`

### 9.4 `final_response_pass`

應讀：

- upstream pass outputs
- minimal UI hints

禁止：

- 不新增新數字
- 不重判 boundary
- 不改 commit decision

輸出：

- `FinalResponseResult`

---

## 10. Recommendation Prompt Contract

對應 [`docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md)

### 10.1 `recommendation_context_pass`

應讀：

- `CurrentBudgetView`
- `ActiveBodyPlanView`
- `PreferenceProfileSummary`
- `RecentCommittedMealsView`
- optional `location_context`

禁止：

- 不直接產生 canonical state
- 不建立 recommendation intent state

### 10.2 `candidate_generation_pass`

應讀：

- favorites
- golden orders
- nearby candidates
- safe defaults

禁止：

- 不做最終排序
- 不直接對外呈現

### 10.3 `ranking_and_selection_pass`

應讀：

- candidate set
- hard constraints
- soft preferences
- budget posture
- location posture

禁止：

- 不直接轉 intake
- 不 invent proposal

### 10.4 `recommendation_response_pass`

應讀：

- ranked candidates
- `top_pick`
- `backup_picks`
- `hint_packet`
- channel context

禁止：

- 不創建 recommendation state
- `幫我記這個` 只能作為 explicit intake action hint

---

## 11. Calibration Model Prompt Contract

對應 [`docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md)

### 11.1 任務

輸出：

- `operating_expenditure_estimate`
- `intake_estimation_bias_posture`
- `deficit_reality_status`
- `mismatch_attribution`
- `proposal_eligibility`

### 11.2 應讀

- `BodyObservation` window summary
- intake completeness summary
- `CurrentBudgetView`
- `ActiveBodyPlanView`
- rescue history summary
- adherence summary

### 11.3 禁止

- 不直接改 `BodyPlan`
- 不直接生成 proposal UI
- 不把 bias posture 當成全局數字覆寫命令

---

## 12. Calibration Proposal Prompt Contract

對應 [`docs/specs/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md)

### 12.1 `proposal_gate_pass`

應讀：

- `L3.3A` outputs
- `CurrentBudgetView`
- `ActiveBodyPlanView`

輸出：

- `ProposalGateResult`

### 12.2 `option_generation_pass`

應讀：

- gate result
- body plan posture
- budget posture

輸出：

- `CalibrationProposalOption[]`

### 12.3 `option_ranking_pass`

規則：

- 預設主推一個方案
- alternatives 可收起但不可消失
- `logging_quality_first` 應高於過早 `計畫重啟`

### 12.4 `proposal_response_pass`

規則：

- 對外命名用 `計畫重啟`
- `11:00` 生效規則需由 response / UI hint 明確表達
- 不直接 commit

---

## 13. Rescue Prompt Contract

對應 [`docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md)

### 13.1 `rescue_trigger_pass`

應讀：

- `CurrentBudgetView`
- meal history
- rescue history
- active proposals

輸出：

- `RescueTriggerResult`

### 13.2 `rescue_assessment_pass`

應讀：

- trigger result
- adherence summary
- recommendation posture

輸出：

- `rescue_horizon`
- `recovery_viability`
- `recommended_rescue_family`

### 13.3 `rescue_option_pass`

規則：

- horizon 只用合法集合
- 單日壓縮不得超過 15%
- 不可低於 safety floor heuristic
- non-viable 時允許 `rescue_stop_and_escalate`

### 13.4 `rescue_response_pass`

規則：

- 預設一個主推
- alternatives 可收起但可取得
- `11:00` 規則與 `next_meal_protection` 例外要明確
- 不責備使用者

---

## 14. Workflow Routing Pass Prompt Contract

對應 [`docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md) Section 11

### 14.1 `workflow_routing_pass`

**Logical model role**：`fast_router_model`

應讀：

- `raw_user_input`
- `active_open_rescue_proposal`（proposal_id, status, recommended_days）
- `pending_intake_followup`（meal_thread_id, pending_question）
- `active_body_plan_summary`（goal_type, recommended_target_kcal）
- `recent_message_summary`（最近 2-3 則的摘要）

禁止：

- 不做 intake boundary splitting
- 不做 nutrition resolution
- 不做 proposal shaping
- 不 commit 任何 canonical state
- 不把 tone / style / explanation density 升成 routing label

輸出（`WorkflowRoutingResult`）：

- `target_workflow_family`：`intake` / `rescue` / `calibration` / `recommendation` / `body_observation` / `general_chat`
- `disposition`：`create` / `continue` / `accept` / `reject` / `defer` / `adjust` / `answer_only` / `open_new_workflow`
- `routing_confidence`：`high` / `medium` / `low`
- `ambiguity_posture`：`none` / `allow_uncertain`

Abstain schema（無法判斷時）：

```json
{
  "target_workflow_family": "general_chat",
  "disposition": "answer_only",
  "routing_confidence": "low",
  "ambiguity_posture": "allow_uncertain"
}
```

### 14.2 `general_chat` workflow（1 pass）

**Logical model role**：`response_writer_model`

應讀：

- `WorkflowRoutingResult`（來自 routing pass）
- `CurrentBudgetView`（回答預算相關問題）
- `ActiveBodyPlanView`（回答目標相關問題）

禁止：

- 不 commit 任何 canonical state
- 不觸發 intake、rescue、calibration flow
- 不建立 proposal
- 不輸出 kcal 估算

輸出：

- `reply_text`
- `asked_follow_up`：boolean
- `ui_hints`：dict

---

## 15. Dynamic Context Packing Rules

### 14.1 prompt 不應直接塞全量歷史

應只塞：

- relevant summary
- typed views
- selected evidence
- short recent transcript

### 14.2 dynamic context 優先順序

1. current task object
2. active shared view
3. relevant summary
4. short transcript
5. raw historical retrieval fallback

### 14.3 derived views 優先於 raw tables

例如：

- recommendation 讀 `PreferenceProfileSummary`
- calibration 讀 intake completeness summary
- intake 讀 `ActiveMealView`

---

## 15. Output Schema Contract

### 15.1 schema-first 原則

- prompt 明確指定輸出型別
- 不允許自由發揮多餘欄位
- 缺欄位視為無效輸出

### 15.2 abstain / no-op 也要有 schema

每個 pass 在 abstain 情境下必須輸出合法 schema，不可回傳空值或自由文字。

#### Intake flow abstain schemas

`task_meal_link_pass` — 非 intake 輸入：
```json
{
  "intent": "non_intake",
  "scope": "none",
  "meal_link_action": "no_action",
  "target_meal_thread_id": null,
  "boundary_reason": "<說明為何判斷為非 intake>",
  "clarification_blocking": false,
  "occurred_at_interpretation": null,
  "time_reference_confidence": null,
  "intake_units": []
}
```

`decision_pass` — 無法決定下一步：
```json
{
  "next_action": "cannot_decide",
  "tool_plan": null,
  "unresolved_info": ["<說明缺少什麼>"],
  "clarify_is_blocking": true,
  "can_proceed_without_clarify": false,
  "decision_confidence": "low",
  "response_mode_hint": "needs_clarification"
}
```

`nutrition_resolution_pass` — 無法估算：
```json
{
  "resolution_mode": "cannot_estimate",
  "resolution_basis": "insufficient_evidence",
  "confidence": "none",
  "answer_payload": null,
  "meal_items_payload": [],
  "unresolved_info": ["<說明缺少什麼>"],
  "state_transition_hint": "needs_clarification",
  "commit_readiness": "not_ready"
}
```

#### Rescue flow abstain schemas

`rescue_trigger_pass` — 無 rescue 條件：
```json
{
  "triggered": false,
  "trigger_type": "no_trigger",
  "trigger_severity": "none",
  "trigger_object_ref": null,
  "overshoot_summary": null,
  "proactive_eligibility": false
}
```

`rescue_assessment_pass` — rescue 不需要：
```json
{
  "rescue_needed": false,
  "rescue_horizon": null,
  "recovery_viability": null,
  "recommended_rescue_family": "no_rescue",
  "escalation_risk": "none",
  "assessment_confidence": "high"
}
```

`rescue_option_pass` — 無合法 option：
```json
{
  "rescue_options": [],
  "top_option": null,
  "backup_options": [],
  "option_effect_summaries": [],
  "guardrail_notes": ["<說明為何無合法 option>"]
}
```

#### Calibration flow abstain schemas

`proposal_gate_pass` — 不允許提案：
```json
{
  "proposal_gate_result": "blocked",
  "allowed_option_families": [],
  "blocked_option_families": ["budget_adjustment", "plan_reset", "pace_adjustment"],
  "gate_rationale": "<說明 block 原因，例如 logging_quality_first>",
  "primary_policy_posture": "monitor_only"
}
```

#### Recommendation flow abstain schemas

`ranking_and_selection_pass` — 無合法候選：
```json
{
  "ranked_candidates": [],
  "top_pick": null,
  "backup_picks": [],
  "ranking_explanation": "no_valid_candidates",
  "presentation_policy": "fallback_to_generic"
}
```

`recommendation_context_pass` — 無法決定 recommendation goal：
```json
{
  "recommendation_goal": "cannot_determine",
  "hard_constraints": [],
  "soft_preferences": [],
  "context_window_summary": "insufficient_context",
  "recommendation_mode": "cold_start_fallback",
  "budget_posture": null,
  "preference_profile_ref": null,
  "location_posture": "unavailable"
}
```

`candidate_generation_pass` — 無任何候選來源可用：
```json
{
  "candidate_items": [],
  "candidate_source_summary": "all_sources_unavailable",
  "candidate_filter_reasons": ["no_preference_data", "no_location", "no_golden_orders"],
  "candidate_count": 0,
  "coverage_gaps": ["historical_preference", "nearby_candidates", "golden_orders"]
}
```

`recommendation_response_pass` — 無候選可呈現：
```json
{
  "reply_text": null,
  "ui_cards": [],
  "quick_actions": [],
  "asked_follow_up": false,
  "ui_hints": { "mode": "no_recommendation", "reason": "no_valid_candidates" },
  "hint_packet": null
}
```

補充規則：

- `recommendation_context_pass` 輸出 `recommendation_mode: cold_start_fallback` 時，後續 pass 應切換到 cold-start 執行模式（見 L3.2 Section 6.7）
- `candidate_generation_pass` 輸出空 `candidate_items` 時，`ranking_and_selection_pass` 應直接輸出 `no_valid_candidates` abstain schema，不嘗試排序
- `recommendation_response_pass` 輸出 `no_recommendation` 時，chat surface 應給出「目前沒有適合的建議，你可以告訴我你想吃什麼」之類的 fallback 回應，而不是空白

### 15.3 abstain schema 規則

- 所有 abstain output 必須是合法 schema，不可回傳 `null` 或空字串作為整個 output
- abstain output 的 `reason` 或 `rationale` 欄位應帶有可讀說明，供 trace 使用
- deterministic layer 收到 abstain output 後，應視為合法輸出，不觸發 self-correction round
- abstain output 不應被 response layer 包裝成「系統錯誤」；應依 flow 語意給出合適的使用者回應

---

## 16. Prompt Safety / Failure Policy

### 16.1 當資訊不足時

prompt 應鼓勵模型輸出：

- `needs_clarification`
- `insufficient_data`
- `logging_quality_first`
- `monitor_only`

### 16.2 當 output 風險很高時

prompt 應明示：

- 寧可保守
- 寧可不提案
- 寧可不顯示 derived fields
- 不可用語氣掩蓋低信心

---

## 17. Shared Prompt Fragments

後續實作時，建議做成可重用 fragment：

- `product_north_star_fragment`
- `canonical_object_boundary_fragment`
- `proposal_vs_commit_fragment`
- `derived_view_boundary_fragment`
- `safety_floor_fragment`
- `single_primary_option_fragment`
- `time_policy_fragment`
- `no_intent_state_fragment`

---

## 18. 與前面 specs 的對齊

### 對 L0

prompt 必須體現產品北極星：

- 低摩擦記錄
- 持續校準總消耗
- 有感推薦與提醒
- 穩定維持熱量赤字

### 對 L1

prompt 不可越權到 ownership 外。

### 對 L2

prompt 只能讀合法 view / summary / canonical projections。

### 對 L3.1-L3.4

每條 flow 的 prompt contract 都必須服從對應 runtime contract。

### 對 L6A / L6B

prompt contract 應依賴 logical model roles，而不是直接依賴 provider model IDs。

---

## 19. 測試情境

後續至少應覆蓋：

- intake prompt 不因 bias posture 直接全局調數
- recommendation prompt 不建立 intent state
- calibration model prompt 輸出 `operating_expenditure_estimate` 與 `intake_estimation_bias_posture`
- calibration proposal prompt 預設只主推一個方案
- rescue prompt 遵守 15% 與 safety floor guardrail
- response prompt 不重判前面 pass 的語意結論
- 各 pass 在 abstain / insufficient-data 情境下仍能輸出合法 schema

---

## 20. v1 Default Decisions

1. 每條 flow 的 stable prompt 應共用統一 opening fragment，至少包含：
   - product north star
   - canonical boundary reminder
   - no-implicit-state reminder
2. `single_primary_option_fragment` 應做成 rescue / calibration 共用 fragment
3. `11:00` 規則應做成共用 `time_policy_fragment`
4. structured bias posture 在本層先定最小 schema：
   - `bias_posture`
   - `scope[]`
   - `confidence`
   - `allowed_effects[]`
5. token policy：
   - v1 不定死每 pass 的硬 token 上限
   - 但必須保留 `cache-aware` 前綴、summary-first、與 dynamic-context 後置原則
   - pass-level token budget 留到 L6 implementation policy 才做最終硬化
