# App V2 Implementation Plan

> **文件類型：Repo-Aware Implementation Plan（實作計畫）**
>
> 這份文件嚴格對齊 repo reality。它回答：現在哪些模組存在、哪些要重寫、哪些要 adapter、implementation packages 怎麼切。
>
> **前置閱讀：** 先讀 `app_v2_ideal_architecture_final.md`（canonical architecture truth），再讀這份。
>
> **Baseline-first rule:** 高影響 agent runtime / retrieval / tool orchestration work，先用最佳實務建立高能力 baseline，再由 eval / latency / cost 收斂，不要在沒有 baseline 的情況下過早限縮能力。
>
> **Product-truth-first rule:** user-visible product behavior is higher-order than eval fixture shape. Evals validate product truth; they do not define product architecture.

---

## 1. Repo Evidence Appendix

以下所有「已存在」的聲明都有對應的 repo 證據。

### 1.1 資料模型（app/models.py 直接驗證）

| 模型 | Table | 檔案 | 狀態 |
|------|-------|------|------|
| `MealLog` | `meal_logs` | `app/models.py:MealLog` | ✅ 存在 |
| `MessageBuffer` | `message_buffer` | `app/models.py:MessageBuffer` | ✅ 存在 |
| `MealThreadRecord` | `meal_threads` | `app/models.py:MealThreadRecord` | ✅ 存在 |
| `MealVersionRecord` | `meal_versions` | `app/models.py:MealVersionRecord` | ✅ 存在 |
| `MealItemRecord` | `meal_items` | `app/models.py:MealItemRecord` | ✅ 存在 |
| `LegacyMealLogMapRecord` | `legacy_meal_log_map` | `app/models.py:LegacyMealLogMapRecord` | ✅ 存在（MealLog → MealThread 橋接） |
| `DayBudgetLedgerRecord` | `day_budget_ledger` | `app/models.py:DayBudgetLedgerRecord` | ✅ 存在 |
| `LedgerEntryRecord` | `ledger_entries` | `app/models.py:LedgerEntryRecord` | ✅ 存在 |
| `BodyObservationRecord` | `body_observations` | `app/models.py:BodyObservationRecord` | ✅ 存在 |
| `BodyProfileRecord` | `body_profiles` | `app/models.py:BodyProfileRecord` | ✅ 存在 |
| `BodyPlanRecord` | `body_plans` | `app/models.py:BodyPlanRecord` | ✅ 存在 |
| `ProposalContainerRecord` | `proposal_containers` | `app/models.py:ProposalContainerRecord` | ✅ 存在 |
| `ProposalOptionRecord` | `proposal_options` | `app/models.py:ProposalOptionRecord` | ✅ 存在 |
| `ProactiveTriggerRecord` | `proactive_triggers` | `app/models.py:ProactiveTriggerRecord` | ✅ 存在 |
| `ExerciseEventRecord` | — | — | ❌ 不存在，需要新建 |

### 1.2 Runtime 模組（直接驗證）

| 模組 | 檔案路徑 | 狀態 |
|------|---------|------|
| Single manager entrypoint | `app/runtime/application/manager_service.py` | ✅ 存在，唯一語義控制面 |
| Intake application services | `app/intake/application/` | ✅ 存在，擁有 meal-thread lifecycle / correction / followup / commit semantics |
| Nutrition evidence and estimation | `app/nutrition/application/`, `app/nutrition/agent/`, `app/nutrition/infrastructure/` | ✅ 存在，擁有 lookup / evidence / exactness / estimate output |
| Budget read and sync | `app/budget/application/`, `app/budget/interface/` | ✅ 存在，擁有 consumed / remaining / overshoot / aggregate truth |
| Runtime trace and sidecar | `app/runtime/application/`, `app/runtime/infrastructure/trace/` | ✅ 存在，擁有 orchestration mechanics / trace / guard / sidecar |
| Provider adapters | `app/providers/` | ✅ 存在，single-manager structured output contract |

---

## 2. Module Migration Matrix

目前 active V2 模組的 domain ownership：

| Ownership | Domain path | 說明 |
|---------|---------|------|
| Intake | `app/intake/` | meal-thread lifecycle, pending followup, item correction/removal, commit semantics |
| Nutrition | `app/nutrition/` | nutrition lookup, evidence eligibility, exactness posture, estimate contract |
| Budget | `app/budget/` | day-level budget, remaining kcal, overshoot, aggregate truth |
| Runtime | `app/runtime/` | manager orchestration, bounded rounds, execution guard, sidecar, trace |
| Providers | `app/providers/` | model/provider adapters only |

---

## 3. Schema Migration Policy

### 3.1 V2 Core Schema (已清理完成)

以下 schema / envelopes 曾在 legacy orchestration 裡深度使用，在 V2 single-manager cutover 完成後應只保留 neutral canonical objects：


- legacy intermediate routing result
- legacy nutrition estimate result
- legacy execution envelope


- `ToolDecisionTrace`
- `EvidenceResolutionTrace`

**規則：** Schema cleanup 不是切流量前的硬門檻。先讓 V2 在 shadow mode 穩定，切流量後再做 tombstone。

### 3.2 永久保留（V2 也需要）

- `EstimatePayload`（最終輸出）
- `FinalResponseResult`（最終輸出）
- `MealItemPayload`（commit contract）
- `CommitRequestCandidate`（commit contract）
- `EstimateRequest`（API input）
- `EvidenceBundle`、`EvidenceCandidate`（evidence contract）

---

## 4. V2 Core Scope Freeze

### 4.1 V2 Core 覆蓋的旅程（第一包）

| 旅程 | 說明 |
|------|------|
| A Onboarding | TDEE 計算 + body plan 建立 |
| B 單回合錄入 | 估算 + 記錄 + 預算同步 |
| C 珍珠奶茶 | clarify lane |
| D 家常菜 | clarify lane |
| E 超標警告 | 超標後 chat + UI 同時顯示 |
| K 餐點修正 | item-level correction |

### 4.2 Future Scope（不進 V2 core）

| 旅程 | 依賴 Slice |
|------|-----------|
| F, F2, T | 2.5 Rescue |
| G, H, U | 2.4 Weight / Exercise |
| I | 2.6 Calibration |
| L, Q, R, S | 2.8 Recommendation |
| M | 2.7 Memory |
| N, V | 2.9 Proactive |
| O, P | Multimodal / Voice |

---

## 5. Implementation Packages

> **注意：** Build order 改成 journey bundle，不是按 spec 類別推進。每個 bundle 完成後立即驗，沒過 eval 不准繼續擴。架構 owner truth 以 `app_v2_ideal_architecture_final.md` 為準。

### 5.0 Eval-Driven 規則

V2 從這一輪起採：

- `E2E eval 定義目標`
- `spec 定義 owner truth / contract / guardrails`
- `中層測試提供 debug leverage`

正式規則：

- 不再先把 spec 細節做滿再驗證
- 每個 bundle 都必須先有 journey-level E2E gate，才允許實作
- tool / state / renderer-sidecar 測試是必要輔助，但不得反過來主導 build order
- 若 E2E case 與細部 spec 衝突，先修 owner truth，再繼續 build

### 5.0A Single-Manager Guardrail Frame

在任何 intake EDD 開始前，先固定 single-manager build frame：

1. `state_resolver`
2. `single_manager_loop`
3. `domain-owned tool batch`
4. `execution_guard`
5. `sidecar_truth`
6. `trace`

Hard rules：

- manager 是唯一語義控制面
- tools 只提供 evidence / mutation result
- guard 只 validate / block / downgrade / request one repair round
- sidecar 只 mirror truth，不做產品決策
- 不得重新長出 bundle-specific fixed step pipeline
- 不得用 benchmark / replay pack / runner payload shape 反向主導 architecture

Pre-EDD readiness 至少必須輸出：

- `single_manager_contract_status`
- `domain_tool_surface_status`
- `guard_invariant_status`
- `fat_service_status`
- `latency_trace_status`
- `product_truth_alignment_status`
- `anti_overfit_status`

若任一欄位不是 `pass`，狀態只能是 `not_ready_for_edd`。

### Stage 0：Truth Cleanup（開工前必做）

**目標：** 確認 V2 docs 正確，可以開始 build。

**工作：**
1. 確認 `app_v2_ideal_architecture_final.md` 的 single-manager + Execution Guard 設計正確
2. 確認 L4 integration 已寫進 target spec
3. 確認 schema reduction policy 已寫進本文件
4. 確認 Manager-style capability gates 可作為 intake-entry acceptance evidence
5. 同步 active execution truth 到 current Manager-style stage plan

**Stage 0 不做：**
- intake-entry runtime widening
- rescue / recommendation / calibration / proactive 遷移
- 任何以 truth cleanup 名義偷渡的 manager/tool/renderer scope 擴張

### Stage 1：Core Manager Trunk

**目標：** 打通 onboarding、single-turn intake、`/today`、`/body-plan`、remaining-budget answer。

**工作：**
1. `State Resolver`（deterministic context assembler）
2. `Primary Manager Agent`（`app/runtime/application/manager_service.py`）
3. V2 Core Tools（`read_day_budget`、`read_active_meal`、`read_body_plan`、`search_recent_meals`、`estimate_nutrition`、`lookup_nutrition_db`、`search_official_nutrition`、`calculate_tdee`、`compare_against_budget`、`persist_meal_log`、`update_meal_item`、`mark_item_removed`、`remove_meal_thread`、`persist_body_plan`、`create_initial_day_budget`、`append_trace_event`）
4. `Execution Guard`（safety floor + legality）
5. `Renderer`（thin LLM prompt）
6. `Deterministic Sidecar`（no LLM）
7. **Response Policy**（Section 4.2A in target spec）
8. **Evidence Policy / Eligibility Gate**（Section 5.2B, 5.5.1 in target spec）
9. **Manager-style diagnostic runner** — 必須使用 active runtime trace，不得復用 legacy Bundle oracle

**驗證旅程：** A, B, J

**Intake-entry completion must be proven by current Manager-style diagnostics（三個條件全部成立）：**
1. Manager-style diagnostic runner reports pass
2. `summary.p0_failed == 0`（4 個 P0 cases 全過）
3. 每個 case 的 `request_id` 都有對應的 trace artifact（`audit.request_trace_exists == true`）

**不接受的「通過」：**
- Codex 自己說「我測過了」
- Unit tests 通過但沒有 eval runner 輸出
- Eval runner 輸出但沒有 trace artifact

**Diagnostic runner 輸出格式：** use current artifacts under `artifacts/` or `runtime/evals/`, with case-level trace refs.

**中層測試：**
- tool contract tests
- onboarding / ledger / remaining-budget state tests
- renderer / deterministic sidecar contract tests

### Stage 2：Intake Depth

**目標：** clarify lane、item-level correction、overshoot sync、macro sync。

**工作：**
1. `estimate_nutrition` tool 的 clarify path（pending_followup）
2. `update_meal_item` tool（修正熱量）
3. `update_meal_macro` tool（修正蛋白質/碳水/脂肪）
4. `mark_item_removed` tool（標記餐點項目為未喝/未吃）
5. `remove_meal_thread` tool（刪除整個餐點記錄）
6. Sidecar 的 overshoot 欄位
7. Sidecar 的 macro 欄位（protein, carbs, fat）
8. **Manager-style intake-depth diagnostic runner** — 必須使用 manager structured output and active runtime traces

**Macro 計算機制**：
- 由於 Grok 4 Fast 有 2M token context，模型可以直接一次估出 kcal + macro
- 不需要分開的 deterministic macro 計算
- `estimate_nutrition` tool 內部一次回傳所有數值

**Macro 對齊檢查（Execution Guard）**：
- 每次 estimate/persist 回傳 macro 時，驗證 kcal 與 macro 總和是否一致
- 公式：`kcal ≈ (protein × 4) + (carbs × 4) + (fat × 9)`
- 允許 ±10% 誤差
- 失敗時：
  - 記錄 warning 到 trace
  - `show_macro = false`（UI 不顯示 macro）
  - 仍允許通過（不攔截）

**驗證旅程：** C, D, E, K

**Intake-depth completion must be proven by current Manager-style diagnostics（三個條件全部成立）：**
1. Manager-style intake-depth diagnostic runner reports pass
2. `summary.p0_failed == 0`（5 個 P0 cases 全過）
3. 每個 case 的 `request_id` 都有對應的 trace artifact

**Eval cases：** current Wave 1 micro-suites and Founder E2E diagnostics

### Bundle 3：Body + Calibration

**目標：** body observation、exercise event、calibration check。

**工作：**
1. `persist_body_observation` tool（體重記錄）
2. `persist_exercise_event` tool（運動記錄）
3. `read_body_observation_history` tool（讀取體重趨勢 14/21 天）
4. `run_calibration_check` tool（Calibration 5-step gate）

**驗證旅程：** G, H, I

### Bundle 4：Rescue

**目標：** 救援計畫、預期大餐規劃。

**工作：**
1. `read_open_proposals` tool（讀取 open rescue/calibration proposals）
2. `dismiss_proposal` tool（關閉/拒絕 proposal）
3. `calculate_rescue_spread` tool（Rescue 分攤計算）
4. `create_rescue_proposal` tool（建立 rescue proposal）
5. `accept_rescue_proposal` tool（接受 rescue）

**驗證旅程：** F, F2

### Bundle 5：Recommendation + Memory

**目標：** 食物推薦、偏好記憶、位置推薦。

**工作：**
1. `run_recommendation` tool（5-node recommendation flow）
2. `search_nearby_food_options` tool（位置推薦 nearby）
3. `read_location_context` tool（讀取位置資訊）
4. `search_memory` tool（長期偏好記憶）
5. `write_memory` tool（寫入偏好記憶）
6. `write_temporary_preference` tool（寫入暫時性偏好）
7. `read_preference_summary` tool（讀取偏好摘要）
8. `read_app_info` tool（讀取 app 說明/FAQ）

**驗證旅程：** L, M, Q, R, S

### Bundle 5.5：Location-Triggered Recommendation

**目標：** 位置觸發推薦，走到哪裡推薦到哪裡。

**工作：**
1. **iOS Geofencing 整合**
   - `CLRegion` monitoring（最多 20 區域）
   - 背景位置更新處理
   - 進入/離開區域事件觸發
2. **Android Geofencing 整合**
   - `GeofencingClient` API
   - 背景位置更新處理
3. **Google Places API 整合**
   - `searchNearby` endpoint
   - 餐廳類型篩選（restaurant, cafe, meal_takeaway）
   - 半徑與結果數限制
4. **LLM Matching Engine**
   - 根據使用者偏好评分餐廳/餐點
   - 飲食類型匹配（低醣、高蛋白等）
   - 候選排序
5. **Push Notification 整合**
   - 推薦卡片通知
   - 點擊後進入 chat 或 UI
6. **觸發條件引擎**
   - 熱量窗口檢查
   - 時間 context（午餐/晚餐時段）
   - 偏好匹配度閾值

**新 Tools：**
- `register_geofence_region` tool（註冊感興趣區域）
- `remove_geofence_region` tool（移除區域）
- `search_nearby_with_preferences` tool（用偏好搜尋附近餐廳）
- `score_restaurant_match` tool（用 LLM 評分餐廳匹配度）
- `trigger_location_recommendation` tool（觸發位置推薦）

**驗證旅程：** L5（Location-triggered recommendation journey）

**技術限制：**
- iOS 18 背景事件可能延遲到使用者打開 app 才收到
- Google Places API 有 quota 限制
- 需要使用者授權背景位置權限

### Bundle 6：Proactive

**目標：** 主動提醒、週報洞察。

**工作：**
1. `set_notification_suppression` tool（設定通知靜音）
2. `read_quiet_hours` tool（讀取靜音時段）
3. `set_quiet_hours` tool（設定靜音時段）
4. Proactive trigger logic（定時主動發送）

**驗證旅程：** N, V

### Bundle 7+：Schema Cleanup（切流量後）

**目標：** 刪除中間狀態 schema。

**工作：**
1. 刪除 Section 3.1 列出的中間狀態 schema
2. 確認 V1 orchestration 已完全停用

**注意：** Schema cleanup 不是切流量前的硬門檻。先讓 V2 在 shadow mode 穩定，切流量後再做。

---

## 6. 現有 Spec 的修改清單

### 需要更新的 Spec（在 implementation 時更新）

| Spec | 需要改什麼 | 狀態 |
|------|-----------|------|
| `L3_1_INTAKE_RUNTIME_CONTRACT_SPEC.md` | 把 legacy multi-stage 改成 manager + tools 的描述 | ✅ 已更新（標記為 V1 棄用） |
| `L4B_RETRIEVAL_POLICY_SPEC.md` | 新增 Section 13 Web Search Retrieval Policy | ✅ 已更新 |
| `L6E_LLM_PASS_DESIGN_POLICY_SPEC.md` | pass-centered 設計原則改成 manager + tool | ⚠️ 已在 archive，跳過 |
| `L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md` | Router 概念改成 State Gate + Manager | ⚠️ 已在 archive，跳過 |
| `L6G_MULTI_DISPATCH_SEQUENTIAL_CHAINING_SPEC.md` | 複合式 utterance 改成 manager 並行 tool calls | ⚠️ 已在 archive，跳過 |

### 可以保留不動的 Spec

| Spec | 原因 |
|------|------|
| `L0A_ONBOARDING_FLOW_SPEC.md` | Onboarding 邏輯不變 |
| `L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md` | Ledger 邏輯不變 |
| `L2_DATA_STATE_SPEC.md` | 資料模型不變 |
| `L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md` | Calibration 邏輯不變 |
| `L4A_MEMORY_MODEL_SPEC.md` | Memory 模型不變 |
| `app_v2_ideal_architecture_final.md` | 這是 canonical architecture truth，不是 implementation |

### 已更新的 Spec

| Spec | 更新內容 |
|------|---------|
| `app_v2_ideal_architecture_final.md` | 對齊 business-domain-first、single-manager、bounded tool contract |
| `L4B_RETRIEVAL_POLICY_SPEC.md` | 新增 Section 13 Web Search Retrieval Policy |
| `APP_V2_IMPLEMENTATION_PLAN.md` | 更新所有 Bundle 的 tools 列表、新增 policy layers |

### 新增的 Policy Layers（需在 implementation 時實作）

| Policy Layer | 說明 |
|--------------|------|
| Response Policy | 什麼直接答、什麼要搜、什麼拒答（Section 4.2A） |
| Evidence Policy / Eligibility Gate | exact/near-exact/generic 分層（Section 5.2B, 5.5.1） |
| Entity Normalization Layer | 品牌名稱變體、alias 處理（Section 5.5.2） |
| Uncertainty Contract | uncertainty_level, estimate_range（Section 5.5.3） |
| Conflict Resolution Policy | 多來源衝突時的優先序（Section 5.5.4） |
| Temporary Preference Memory | 暫時性偏好（Section 5.5.5） |
---

## 7. EDD Stage Architecture Readiness

> **重要：** 這是 EDD 執行的核心流程，確保每個 stage 開始前都有明確的架構邊界，防止肥大檔案、假通過、效能問題。

### 7.1 核心理念

**只靠測試集黑箱讓 agent 自己補檔案，不是 AI-assisted / EDD 的最佳作法。**

每個 EDD 階段開始前，必須先做 **Architecture Impact Pass**，把會用到的 domain、檔案邊界、責任歸屬、latency budget、anti-overfit 機制定好，再讓 agent 進 Red → Green。

### 7.2 EDD Stage Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  Stage Intake                                                       │
│  - 讀 owner truth、bundle spec、相關 founder/benchmark case        │
│  - 不寫 code，只判斷這個 stage 會動到哪些 business domain           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Architecture Impact Pass (必做)                                    │
│  - 判定責任歸屬：intake / nutrition / budget / runtime / providers │
│  - 若現有檔案不該承接新責任，先規劃新檔案                           │
│  - 明確禁止把 correction、retrieval、budget sync、rendering 混進   │
│    同一個胖 service                                                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Harness Contract Pass                                              │
│  - 先補或確認 semantic invariant tests                             │
│  - 每個 case 至少要有：行為 correctness、same-turn sync、           │
│    non-target preservation、evidence honesty、macro semantics      │
│  - 每個 stage 必須有 latency acceptance，不允許「功能綠但 60 秒」   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  EDD Red → Green                                                    │
│  - 先跑會紅的 target tests                                          │
│  - 實作只能在 allowed write surface 內                              │
│  - 不允許針對單一 case 硬寫品項、關鍵字、例外分支                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage Exit Gate (全部通過才算完成)                                 │
│  - business tests 綠                                                │
│  - architecture guard 綠                                            │
│  - fat-file guard 綠                                                │
│  - latency/timeout guard 綠                                         │
│  - no text corruption                                               │
│  - full integration mode 綠，不只 shard 綠                          │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.3 Architecture Impact Pass 產出

每個 EDD stage 都要先產出以下文件：

| 產出 | 說明 |
|------|------|
| `target behavior invariants` | 這個 stage 要守住的行為不變量 |
| `domain ownership map` | 哪些 domain 會被修改 |
| `allowed write surface` | agent 只能修改哪些檔案 |
| `new file / existing file placement decision` | 新功能要放新檔案還是現有檔案 |
| `fat-file risk budget` | 這個 stage 允許的最大檔案大小 |
| `latency budget` | 每個 lane 的最大延遲時間 |
| `anti-overfit strategy` | 如何防止針對單一 case 硬寫 |

### 7.4 Anti-Fat-File Rules

- 每個 stage 前先分配 `responsibility budget`
- `bundle*_service.py` 只能是 thin entrypoint，不得擁有 domain semantics
- 新 workflow family 不得直接加進既有 service；必須先選 domain owner
- Protected files 超過 threshold 或新增 banned responsibility token，stage fail
- 若一個檔案同時做 tool orchestration、persistence、domain policy、response rendering，stage fail

### 7.5 Anti-Overfit Rules

- 每個 benchmark failure 先歸到 behavior family，不先修單一樣本
- 每個 fix 必須能解釋為 generalized rule
- Official bundle、founder realism、promoted benchmark blocking、shadow benchmark 分開報告
- 新增 case 時要標 `behavioral_oracle`，不採逐字 ChatGPT oracle
- 若只讓單一 case 綠但 semantic invariant 沒補，視為 false pass

### 7.6 Latency Rules

- 每個 EDD stage 都要定義 lane-level latency budget
- `simple drink / branded item / followup / correction` 必須有 blocking latency lane
- Report 必須區分：
  - model latency
  - tool latency
  - total latency
  - timeout family
  - shard vs full integration
- `partial_report`、`timeout`、`connection reset` 不能被標成 pass

### 7.7 Stage Exit Gate 檢查清單

| 檢查項 | 通過條件 |
|--------|----------|
| business tests | 所有 eval cases 通過 |
| architecture guard | 修改只在 allowed write surface 內 |
| fat-file guard | 沒有檔案超過 threshold |
| latency guard | 沒有 lane 超過 latency budget |
| text integrity | 沒有 encoding 問題 |
| integration mode | full integration 測試通過 |

### 7.8 實作工具

擴充 `scripts/pre_edd_readiness.py` 為 stage-aware：

```bash
# 使用範例
python scripts/pre_edd_readiness.py \
  --stage intake-depth \
  --allowed-write-surface '{"app/intake": ["application/*"], "app/nutrition": ["application/*"]}' \
  --latency-policy '{"simple_drink": 3000, "branded_item": 5000, "followup": 8000, "correction": 10000}'
```

**Stage readiness report 欄位：**
- `architecture_impact_status`
- `write_surface_status`
- `fat_file_status`
- `semantic_harness_status`
- `latency_policy_status`
- `anti_overfit_status`
- `stage_ready_for_edd`

---

## 8. Intake-Depth Architecture Readiness

### 8.1 Stage Intake

**會動到的 business domains：**
- `app/intake/` - meal-thread lifecycle, pending followup, correction
- `app/nutrition/` - nutrition lookup, evidence, estimate
- `app/budget/` - overshoot sync, remaining budget

### 8.2 Architecture Impact Pass

**Domain ownership map：**

| 功能 | 負責 domain | 檔案 |
|------|-------------|------|
| clarify lane | `app/intake/application/` | `onboarding_service.py`, `v2_bundle3_service.py` |
| item correction | `app/intake/application/` | `v2_bundle3_service.py` |
| macro sync | `app/nutrition/application/` | `target_calculation.py` |
| overshoot sync | `app/budget/application/` | `budget_sync_service.py` |

**Allowed write surface：**
- `app/intake/application/*.py`
- `app/nutrition/application/*.py`
- `app/budget/application/*.py`
- `app/runtime/application/manager_service.py`（僅新增 tool calls）

**不允許：**
- 在 `v2_bundle3_service.py` 新增 retrieval logic
- 在 `manager_service.py` 新增 domain semantics
- 把所有邏輯塞進單一檔案

### 8.3 Fat-File Risk Budget

| 檔案 | 最大行數 |
|------|----------|
| `v2_bundle3_service.py` | 300 行 |
| `manager_service.py` | 500 行 |
| 任何新增 service 檔案 | 200 行 |

### 8.4 Latency Budget

| Lane | Max Latency |
|------|-------------|
| clarify (ask followup) | 8 秒 |
| clarify (estimate + followup) | 10 秒 |
| correction (item-level) | 5 秒 |
| overshoot sync | 3 秒 |

### 8.5 Anti-Overfit Strategy

- 每個 fix 必須是 generalized rule
- 不允許針對「珍珠奶茶」單一 case 新增分支
- 新增 brand lookup 時，必須支援整類品牌，不是單一品牌
