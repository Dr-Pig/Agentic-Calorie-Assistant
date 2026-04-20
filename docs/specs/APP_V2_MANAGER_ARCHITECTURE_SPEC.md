# App V2 Manager Architecture Spec

## 1. 目的與背景

### 1.1 為什麼需要 V2

現有架構（V1）的核心問題不是功能不對，而是**骨架不對**：

- `text_meal_orchestration_support.py` 是一個 600 行的手工 workflow machine，把 planner → boundary → grounding → decision → nutrition → finalize 全部串在一起，每一步都有大量 state 傳遞
- `decision_llm.py` 的 DECISION_PROMPT 有 200 行，在做的事情應該是 manager 自己決定的
- `schemas.py` 有 40+ 個 export，包含 `PassExecutionEnvelope`、`TaskMealLinkResult`、`DecisionPassResult` 等中間狀態的 schema——這些中間狀態不應該被 schema 化
- Trace 是 pass-centered 的，debug 單位是「哪個 pass 壞了」，而不是「這輪 run 中哪個決策 / tool / state 壞了」
- 複合式 utterance（「我跑步 30 分鐘然後吃了便當」）會卡在 router 的分類邊界上

### 1.2 V2 的目標

- 回答品質接近 ChatGPT（該估就估、該追問就追問、回答自然）
- 複合式 utterance 不再卡住
- Schema 只管 canonical state 和最終輸出，不管中間推理狀態
- Debug 單位是 run/event，不是 pass
- 新功能（運動量、推薦、proactive）可以自然地加進來，不需要新增 workflow

### 1.3 不需要開新 repo

V2 是 refactor，不是重做。保留：
- 資料層（`app/models.py`、Alembic migrations、`MealThread`、`DayBudgetLedger` 等）
- Infrastructure（DB、providers、observability）
- Eval fixtures 和 benchmark cases
- UX Journey Map（這是 eval truth）

重寫：
- `app/agent/` — pass 改成 tools
- `app/usecases/text_meal_orchestration_support.py` — 改成 manager
- `app/schemas.py` — 大幅簡化
- `app/application/` 裡的 orchestration 相關部分

---

## 2. V2 架構概覽

```
使用者輸入
  ↓
[Thin State Gate]（deterministic）
  - 讀 active meal state、pending followup、conversation state
  - 判斷是否有明確的 state-driven 路由（例如：pending followup 存在）
  - 若有：直接路由，不進 manager
  - 若無：進 manager
  ↓
[Primary Manager Agent]（LLM，one strong agent）
  - 讀 context（active meal、day budget、pending followup、goal、少量偏好）
  - 理解意圖
  - 決定 tool calls（可並行）
  - 整合 tool 結果
  - 產生 response intent
  ↓
[Tool Calls]（parallel where possible）
  - 全部是 deterministic 或 LLM-inside-tool
  - Manager 不知道 tool 內部怎麼實作
  ↓
[Renderer / Sidecar]
  - assistant_message（LLM，給使用者看）
  - ui_state（deterministic，給前端）
  - trace_event（deterministic，給 observability）
```

---

## 3. Thin State Gate

### 3.1 定位

State gate 是 manager 之前的一個薄層，只做 state-driven 的確定性路由。

它不是 router，不做語義分類。它只問一個問題：**「現在的 state 是否已經決定了這輪要做什麼？」**

### 3.2 State Gate 的合法路由條件

| 條件 | 路由 |
|------|------|
| `pending_followup` 存在且使用者回答了 | 直接進 `estimate_nutrition` tool，帶上 pending context |
| `active_meal` 存在且使用者說「沒喝」「刪掉」等明確 item removal | 直接進 `update_meal_item` tool |
| 使用者說「接受」「好」且有 open rescue proposal | 直接進 `accept_rescue_proposal` tool |
| 以上都不符合 | 進 Primary Manager Agent |

### 3.3 State Gate 不做的事

- 不做語義分類（「這是 intake 還是 exercise？」）
- 不做 meal boundary 判斷
- 不做 clarify 決策

---

## 4. Primary Manager Agent

### 4.1 定位

Manager 是這個 app 的核心 LLM。它負責：

- 理解使用者這輪說的話在做什麼
- 決定要呼叫哪些 tools
- 整合 tool 結果
- 產生 response intent（不是最終文字，是「要說什麼」的結構化意圖）

Manager 不負責：
- 估算熱量（那是 `estimate_nutrition` tool 的事）
- 計算 rescue spread（那是 `calculate_rescue_spread` tool 的事）
- 格式化 UI（那是 renderer 的事）
- 寫入資料庫（那是 action tools 的事）

### 4.2 Manager 的 System Prompt 結構

Manager 的 system prompt 應該是薄的，只包含：

```
[PRODUCT CONTEXT]
你是一個 chat-first 的減肥助手。
核心目標：幫助使用者維持熱量赤字。
主要互動：記錄餐點、追蹤預算、推薦食物、救援超標。

[CURRENT STATE]
- active_meal: {active_meal_summary}
- day_budget: {day_budget_summary}
- pending_followup: {pending_followup}
- current_goal: {current_goal}
- top_preferences: {top_3_preferences}

[AVAILABLE TOOLS]
{tool_list_with_descriptions}

[DECISION PRINCIPLES]
- 該估就估，不要過度追問
- 複合式輸入（運動 + 餐點）可以同時呼叫多個 tools
- 超標時在回答裡說明，但不要在同一則訊息裡附加 rescue
- 若有 pending followup 且使用者回答了，優先處理 followup
```

### 4.3 Manager 的輸出

Manager 輸出一個結構化的 response intent，不是最終文字：

```json
{
  "intent_type": "intake_logged | followup_needed | budget_answer | rescue_triggered | recommendation | exercise_logged | general_answer",
  "tool_calls": [...],
  "response_summary": "簡短說明這輪要回答什麼",
  "overshoot_detected": false,
  "pending_followup": null
}
```

---

## 5. Tools 清單

所有 tools 都是 function call，不是 LLM pass。

### 5.1 Data / Retrieval Tools（deterministic）

| Tool | 輸入 | 輸出 | 說明 |
|------|------|------|------|
| `read_day_budget` | user_id, local_date | CurrentBudgetView | 讀今日預算狀態 |
| `read_active_meal` | user_id | ActiveMealView | 讀當前 active meal |
| `read_body_plan` | user_id | ActiveBodyPlanView | 讀 active body plan |
| `search_recent_meals` | user_id, days | RecentCommittedMealsView | 讀最近餐點 |
| `search_memory` | user_id, query | PreferenceProfileSummary | 讀偏好記憶 |

### 5.2 Estimation Tools（LLM inside tool）

| Tool | 輸入 | 輸出 | 說明 |
|------|------|------|------|
| `estimate_nutrition` | food_description, context, evidence | NutritionEstimate | 估算熱量，內部可用 LLM |
| `lookup_nutrition_db` | query | ExactNutritionMatch[] | 查本地 DB |
| `lookup_brand_menu` | brand, item | BrandMenuMatch | 查品牌菜單 |
| `search_official_nutrition` | query | WebNutritionResult | 外部搜尋 |

### 5.3 Deterministic Calculation Tools

| Tool | 輸入 | 輸出 | 說明 |
|------|------|------|------|
| `calculate_tdee` | weight_kg, height_cm, age, sex, activity_level | TDEEResult | Mifflin-St Jeor |
| `calculate_rescue_spread` | overshoot_kcal, base_budget, safety_floor | RescueSpreadResult | 分攤計算 |
| `compute_calorie_range` | food_description | CalorieRange | 熱量範圍估算 |
| `compare_against_budget` | consumed_kcal, budget_kcal | BudgetComparison | 預算比較 |
| `calculate_exercise_bonus` | exercise_type, duration_minutes, weight_kg | ExerciseBonusResult | MET 計算 |

### 5.4 Action Tools（deterministic write）

| Tool | 輸入 | 輸出 | 說明 |
|------|------|------|------|
| `persist_meal_log` | user_id, meal_data | MealThread | 寫入餐點記錄 |
| `update_meal_item` | meal_thread_id, item_id, update | MealVersion | 更新 item |
| `persist_exercise_event` | user_id, exercise_data | ExerciseEvent + LedgerEntry | 寫入運動記錄 |
| `persist_body_observation` | user_id, weight_kg, occurred_at | BodyObservation | 寫入體重 |
| `create_rescue_proposal` | overshoot_kcal, spread_result | ProposalContainer | 建立 rescue proposal |
| `accept_rescue_proposal` | proposal_id, commit_source | RescueCommitEffect | 接受 rescue |
| `write_memory` | user_id, preference_data | ConfirmedMemory | 寫入偏好記憶 |
| `append_trace_event` | run_id, event_data | void | 寫入 trace |

### 5.5 Complex Sub-flow Tools（封裝複雜邏輯）

這些 tools 內部有複雜邏輯，但對 manager 來說是黑盒：

| Tool | 輸入 | 輸出 | 說明 |
|------|------|------|------|
| `run_calibration_check` | user_id | CalibrationPosture | L3.3A 的 5-step gate |
| `run_recommendation` | user_id, context, candidate_spec | RecommendationResult | L3.2 的 5-node flow |
| `run_rescue_assessment` | user_id, overshoot_kcal | RescueAssessment | L3.4 的 trigger + viability |

---

## 6. Renderer / Sidecar

### 6.1 定位

Renderer 把 manager 的 response intent 轉成兩個分離的輸出：

- `assistant_message`：給使用者看的自然語言（LLM 生成）
- `sidecar_state`：給 UI / trace / app 讀的結構化狀態（deterministic）

### 6.2 assistant_message 生成

Renderer 的 LLM 只負責把 response intent 轉成自然語言。它的 system prompt 很薄：

```
你是一個友善的減肥助手。
把以下 response intent 轉成自然、簡短的中文回覆。
規則：
- 先說數字（熱量）
- 1-2 句話，不要用 bullet list
- 超標時說明超標量，但不要附加 rescue 建議
- 最多一個 follow-up 問題
```

### 6.3 sidecar_state 結構

```json
{
  "ui_state": {
    "today_consumed_kcal": 630,
    "today_remaining_kcal": 820,
    "active_meal_id": "...",
    "overshoot": false,
    "overshoot_kcal": 0
  },
  "estimate_payload": {
    "meal_thread_id": "...",
    "estimated_kcal": 630,
    "meal_items": [...]
  },
  "pending_followup": null,
  "state_mutations": ["meal_logged", "ledger_updated"]
}
```

sidecar_state 是薄結構，不要過度肥大。

---

## 7. Run/Event-Based Trace

### 7.1 取代 Pass-Centered Trace

V2 的 trace 單位是 **run**，不是 pass。每輪 request 產生一個 run，run 裡有多個 events。

### 7.2 Run 結構

```json
{
  "run_id": "...",
  "user_id": "...",
  "request_text": "我剛吃了一碗滷肉飯",
  "state_before": {
    "active_meal": null,
    "day_consumed_kcal": 0,
    "pending_followup": null
  },
  "state_gate_result": "pass_to_manager",
  "manager_decision": {
    "intent_type": "intake_logged",
    "tool_calls": ["estimate_nutrition", "read_day_budget"],
    "response_summary": "記錄滷肉飯，回報熱量和剩餘預算"
  },
  "tool_events": [
    {
      "tool": "estimate_nutrition",
      "input": {"food_description": "滷肉飯"},
      "output": {"estimated_kcal": 550},
      "duration_ms": 1200
    },
    {
      "tool": "read_day_budget",
      "input": {"user_id": "..."},
      "output": {"remaining_kcal": 1450},
      "duration_ms": 50
    }
  ],
  "renderer_output": {
    "assistant_message": "滷肉飯約 550 kcal，已記錄。今天還剩約 900 kcal。",
    "sidecar_state": {...}
  },
  "state_after": {
    "active_meal": "meal_thread_xxx",
    "day_consumed_kcal": 550,
    "pending_followup": null
  },
  "failure_reason": null,
  "duration_ms": 1800
}
```

### 7.3 Debug 單位

Debug 時問的問題從「哪個 pass 壞了」改成：
- `state_gate_result` 是否正確？
- `manager_decision.intent_type` 是否正確？
- 哪個 `tool_event` 的 output 不對？
- `renderer_output.assistant_message` 是否符合 UX Journey 的驗證點？

---

## 8. Memory 分層

### 8.1 進 Manager System Prompt 的 Memory（Core Context）

每輪都注入，必須薄：

- `active_meal_summary`：當前 active meal 的標題和熱量
- `day_budget_summary`：今日目標、已消耗、剩餘
- `pending_followup`：上輪未解決的追問
- `current_goal`：每日目標熱量、weekly target rate
- `top_3_preferences`：最高信度的 3 個偏好（例如「不喝含糖飲料」）

### 8.2 透過 Tool 讀的 Memory（On-Demand）

只在需要時讀，不預先注入：

- `search_memory(query)`：長期偏好、golden orders、negative preferences
- `search_recent_meals(days=7)`：最近 7 天的餐點模式
- `read_body_plan()`：TDEE、safety floor、calibration state

### 8.3 只做 Summary 的 Memory

不直接進 context，只在 calibration / weekly insight 時用：

- `IntakeCompletenessSummary`
- `AdherenceSummary`
- `RescueHistorySummary`
- `CalibrationHistorySummary`

### 8.4 Archive（不進 Context）

- 超過 30 天的 MealThread
- 已 supersede 的 MealVersion
- 已 expired 的 ProposalContainer

---

## 9. 現有 Spec 的修改清單

### 9.1 需要更新的 Spec

| Spec | 需要改什麼 |
|------|-----------|
| `L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md` | 把 4-pass 改成 manager + tools 的描述；保留 MealThread / MealVersion / MealItem 的 commit contract |
| `L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md` | 已更新為 5-node，但需要確認 `run_recommendation` tool 的 interface |
| `L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md` | 已更新為 4-node，但需要確認 `run_rescue_assessment` 和 `calculate_rescue_spread` tool 的 interface |
| `L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md` | 已是 thin workflow，對齊 `persist_body_observation` 和 `persist_exercise_event` tools |
| `L3_6_PROACTIVE_SCHEDULER_SPEC.md` | 對齊 event-driven trigger + LLM content generation 的設計 |
| `L6E_LLM_PASS_DESIGN_POLICY_SPEC.md` | 需要更新：pass-centered 的設計原則改成 manager + tool 的設計原則 |
| `L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md` | Router 的概念改成 State Gate + Manager 的概念 |
| `L6G_MULTI_DISPATCH_SEQUENTIAL_CHAINING_SPEC.md` | 複合式 utterance 的處理改成 manager 並行 tool calls |

### 9.2 可以保留不動的 Spec

| Spec | 原因 |
|------|------|
| `L0A_ONBOARDING_FLOW_SPEC.md` | Onboarding 邏輯不變 |
| `L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md` | Ledger 邏輯不變，只是寫入方式改成 tool |
| `L2_DATA_STATE_SPEC.md` | 資料模型不變 |
| `L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md` | Calibration 邏輯不變，封裝成 `run_calibration_check` tool |
| `L4A_MEMORY_MODEL_SPEC.md` | Memory 模型不變，只是讀取方式改成 tool |
| `L4B_RETRIEVAL_POLICY_SPEC.md` | Retrieval 邏輯不變 |

---

## 10. Migration Plan

### Phase 1：建立 Tools Layer（不動 Manager）

1. 把現有的 `nutrition_engine.py`、`nutrition_estimation_support.py` 包成 `estimate_nutrition` tool
2. 把 `calculate_tdee`、`calculate_rescue_spread` 等 deterministic 邏輯包成 tools
3. 把 `persist_text_meal_payload` 包成 `persist_meal_log` tool
4. 確保每個 tool 有清楚的 input/output schema

### Phase 2：建立 Manager（取代 Orchestration）

1. 寫新的 `app/agent/manager.py`
2. Manager 的 system prompt 參考 Section 4.2
3. Manager 呼叫 Phase 1 建立的 tools
4. 用 UX Journey Map 的旅程 A–E 做 eval

### Phase 3：建立 Renderer / Sidecar

1. 把 `final_response_llm.py` 改成 renderer
2. 分離 `assistant_message`（LLM）和 `sidecar_state`（deterministic）
3. 確保 UI 同步走 sidecar_state

### Phase 4：建立 Run/Event Trace

1. 把 `payload_builders.py` 的 pass-centered trace 改成 run/event trace
2. 每輪 request 產生一個 run record
3. 確保 debug 可以用 run_id 查到完整的 state_before → decisions → tool_calls → state_after

### Phase 5：簡化 Schema

1. 刪除 `TaskMealLinkResult`、`DecisionPassResult`、`NutritionResolutionResult`、`PassExecutionEnvelope` 等中間狀態 schema
2. 保留 canonical state schema（`MealThread`、`MealVersion`、`MealItem`、`DayBudgetLedger` 等）
3. 保留最終輸出 schema（`EstimatePayload`、`FinalResponseResult` 等）

### Phase 6：Eval 驗證

1. 用 UX Journey Map 的所有旅程做 eval
2. 確保 P0 旅程（A、B、E）全部通過
3. 確保複合式 utterance（運動 + 餐點）正確處理

---

## 11. V2 最小可行架構圖

```
Request
  │
  ▼
┌─────────────────────────────┐
│     Thin State Gate         │  deterministic
│  - pending_followup?        │
│  - explicit item removal?   │
│  - open proposal accept?    │
└──────────┬──────────────────┘
           │ pass_to_manager
           ▼
┌─────────────────────────────┐
│    Primary Manager Agent    │  LLM (one strong agent)
│  System Prompt:             │
│  - active meal state        │
│  - day budget summary       │
│  - pending followup         │
│  - current goal             │
│  - top preferences          │
│  - available tools          │
│                             │
│  Output: response_intent    │
└──────────┬──────────────────┘
           │ tool_calls (parallel)
           ▼
┌─────────────────────────────┐
│         Tools               │
│  Data:                      │
│  - read_day_budget          │
│  - read_active_meal         │
│  - search_memory            │
│                             │
│  Estimation:                │
│  - estimate_nutrition       │  LLM inside
│  - lookup_nutrition_db      │  deterministic
│  - search_official_nutrition│  external
│                             │
│  Calculation:               │
│  - calculate_tdee           │  deterministic
│  - calculate_rescue_spread  │  deterministic
│  - calculate_exercise_bonus │  deterministic
│                             │
│  Action:                    │
│  - persist_meal_log         │  deterministic write
│  - persist_exercise_event   │  deterministic write
│  - create_rescue_proposal   │  deterministic write
│                             │
│  Sub-flows:                 │
│  - run_recommendation       │  5-node flow
│  - run_calibration_check    │  deterministic gate
└──────────┬──────────────────┘
           │ tool_results
           ▼
┌─────────────────────────────┐
│    Renderer / Sidecar       │
│                             │
│  assistant_message  ──────► │  LLM (thin prompt)
│  sidecar_state      ──────► │  deterministic
│  trace_event        ──────► │  deterministic
└─────────────────────────────┘
```

---

## 12. 與 UX Journey Map 的對應

| 旅程 | V2 處理方式 |
|------|-----------|
| A Onboarding | UI form → deterministic TDEE calc → `persist_body_plan` tool |
| B 單回合錄入 | Manager → `estimate_nutrition` + `persist_meal_log` + `read_day_budget` |
| C 珍珠奶茶 | Manager → `estimate_nutrition`（clarify needed）→ pending_followup |
| D 家常菜 | Manager → `estimate_nutrition`（clarify needed）→ pending_followup |
| E 超標警告 | Manager → `persist_meal_log` → renderer 讀 sidecar_state.overshoot |
| F 救援 | Manager → `run_rescue_assessment` + `calculate_rescue_spread` + `create_rescue_proposal` |
| G/H 體重更新 | State gate 或 Manager → `persist_body_observation` → deterministic TDEE recalc |
| K 餐點修正 | Manager → `update_meal_item` |
| L 食物推薦 | Manager → `run_recommendation`（5-node sub-flow）|
| U 運動量 | Manager → `calculate_exercise_bonus` + `persist_exercise_event` |
| 複合式（運動+餐點）| Manager 並行呼叫 `calculate_exercise_bonus` + `estimate_nutrition` |

---

## 13. V2 Default Decisions

1. Manager 是 one strong agent，不是 router + multiple specialists
2. Tools 是 function calls，不是 LLM passes
3. Renderer 分離 assistant_message（LLM）和 sidecar_state（deterministic）
4. Trace 是 run/event-based，debug 單位是 run，不是 pass
5. Schema 只管 canonical state 和最終輸出，不管中間推理狀態
6. Memory 分層：core context 進 prompt，long-term memory 靠 tool 讀
7. 複合式 utterance 靠 manager 並行 tool calls 處理，不靠 router 分類
8. State gate 只做 state-driven 路由，不做語義分類
