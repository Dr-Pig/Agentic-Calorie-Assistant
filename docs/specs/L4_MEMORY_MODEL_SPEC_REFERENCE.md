# L4 Memory Model Spec — CalorieDeficit Agent Specialized

> Reference-only synthesis.
>
> This document is not a canonical owner spec. It summarizes memory-model ideas
> that must remain subordinate to the active owner specs, especially
> [L1_RUNTIME_OWNERSHIP_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md),
> [L3T_TYPED_RUNTIME_CONTRACT_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md),
> [L4A_MEMORY_MODEL_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L4A_MEMORY_MODEL_SPEC.md),
> [L4B_RETRIEVAL_POLICY_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md),
> and [L4C_CONTEXT_PACKING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L4C_CONTEXT_PACKING_SPEC.md).
>
> If this reference conflicts with an owner spec, the owner spec wins.

## 1. 目的

本文件定義適用於 CalorieDeficit Agent（LINE LIFF 減肥助手）的專業記憶機制。

它回答：

- 系統應保留哪些類型的飲食記憶
- 這些記憶如何分層、如何被強化或衰減
- 偏好如何從臨時觀察升級為穩定確認
- 哪些訊號應用於 proactive 推薦
- 飲食事實如何追蹤時間有效性
- 哪些框架的概念被借用並如何適用於本產品

---

## 2. 設計起源與框架引用

本記憶機制的設計參考了以下開源框架的核心概念，並針對減肥食物推薦場景進行了調整：

| 框架 | 引用概念 | 適用於本產品的方式 |
|------|---------|------------------|
| **memU** (Nevamind-AI/memU) | MemoryItem + reinforcement_count + content_hash | 用於飲食偏好的確認追蹤；當同一食物被多次選擇，reinforcement_count 遞增，作為偏好穩定性的指標 |
| **Hindsight** (vectorize-io/hindsight) | World Facts / Experiences 分離 + reflect 操作 | 用於區分「世界知識」（奶茶熱量高）與「個人經驗」（用戶上週喝了三次奶茶）；reflect 操作可用於夜間深度分析 |
| **Graphiti** (getzep/graphiti) | Temporal Fact（valid_at / invalid_at）+ Entity Graph | 用於追蹤偏好變化：「2024 年偏好高蛋白」→「2025 年改為輕食導向」；事實有有效時間窗 |
| **Letta** (letta-ai/letta) | Core Memory Blocks 分層架構 | 用於將記憶分為 core（穩定偏好）、session（當日上下文）、working（活躍線索）三層 |
| **mem0** (mem0ai/mem0) | User/Session/Agent 三層記憶 API 設計 | 參考其簡潔的記憶檢索介面，應用於 preference retrieval |

---

## 3. 記憶分層架構

借鑒 Letta 的 Core Memory Blocks 概念，結合本產品的特性，記憶分為三層：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Lζ Memory Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Canonical Memory (L1)                                 │
│  ───────────────────────────────────────────────────────────── │
│  來源：MealThread / MealVersion / MealItem (L2 canonical)        │
│  角色：Audit source / retrieval base layer                      │
│  特性：不衰減、版本化、可追溯                                    │
│                                                                  │
│  Layer 2: Pattern Memory (L2)  ← memU-style reinforcement        │
│  ───────────────────────────────────────────────────────────── │
│  來源：L1 聚合 / 使用者明確確認                                   │
│  角色：飲食行為模式、偏好訊號                                     │
│  特性：時間衰減、reinforcement tracking、content_hash 去重       │
│                                                                  │
│  Layer 3: Confirmed Memory (L3)                                  │
│  ───────────────────────────────────────────────────────────── │
│  來源：使用者口頭確認 或 高一致性行為觀察（≥3次）                 │
│  角色：高權重穩定偏好來源                                        │
│  特性：較慢衰減、可被當下口頭聲明覆寫                              │
│                                                                  │
│  Layer 4: Active Context (L4) — Working Memory                   │
│  ───────────────────────────────────────────────────────────── │
│  來源：當前 session / 活躍 thread                                 │
│  角色：當餐決策、即时推薦                                         │
│  特性：會話結束後降級或蒸發                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Layer 1 — Canonical Memory

### 4.1 定義

Layer 1 是產品的正式真實來源（Source of Truth），等同於現有 L2 Data Model 中的 canonical objects。

### 4.2 組成

- `MealThread`：一次飲食事件的完整生命週期
- `MealVersion`：每次修正後的正式版本快照
- `MealItem`：thread 內可獨立修正的食物項目
- `BodyObservation`：體重觀測記錄
- `BodyPlan`：生效中的體態策略版本
- `ProposalContainer / ProposalOption`：待確認提案
- `ProactiveTrigger`：主動觸發記錄

### 4.3 特性

- **不衰減**：歷史記錄永久保留
- **版本化**：correction 建立新 version，舊 version 保留 lineage
- **可追溯**：每一筆記錄可回到原始輸入

### 4.4 與 L2 的對齊

L1 直接對應現有 L2 Data Model，不做任何重新解讀。記憶機制在 L1 層級不做任何 aggregation 或 inference，純粹是 canonical 資料的檢索介面。

---

## 5. Layer 2 — Pattern Memory

### 5.1 起源

借鑒 **memU** 的 MemoryItem + reinforcement_count 機制。

memU 的核心概念：
- 每個 MemoryItem 有 `reinforcement_count`（強化計數）和 `last_reinforced_at`（最後強化時間）
- 同一 content_hash 的記憶被重複觀察時，計數遞增
- 這提供了一個客觀的偏好穩定性指標

### 5.2 Pattern Memory 的組成

```
PatternMemory {
  pattern_id: str
  pattern_type: Literal["food_preference", "store_preference", "time_pattern", "location_pattern", 
                        "macronutrient_preference", "cuisine_preference", "item_kind_preference"]
  pattern_key: str              # e.g., "奶茶", "便利商店", "下午茶時段"
  content_hash: str             # SHA256 hash，用於去重（借鑒 memU）
  reinforcement_count: int      # 被觀察次數（借鑒 memU reinforcement_count）
  last_observed_at: datetime   # 最後觀察時間
  first_observed_at: datetime   # 首次觀察時間
  observation_window_days: int  # 觀察窗口（預設 14 天）
  confidence: float            # 0.0-1.0，基於 reinforcement_count 計算
  source_meal_item_ids: list[str]  # 來源 MealItem IDs
  is_active: bool              # 是否仍在活跃观察窗口
}
```

### 5.3 reinforcement_count 計算規則

借鑒 memU 的 reinforcement 追蹤概念：

1. **首次觀察**：reinforcement_count = 1
2. **同 content_hash 再次觀察**：
   - 若距離上次觀察 ≤ 14 天：reinforcement_count += 1
   - 若距離上次觀察 > 14 天：reinforcement_count = 1（重新計算窗口）
3. **confidence 等級**：
   - reinforcement_count = 1：confidence 0.3（單次觀察，低信心）
   - reinforcement_count = 2：confidence 0.5（兩次觀察，中低信心）
   - reinforcement_count ≥ 3：confidence 0.7（三次以上，高信心，可考慮升級 L3）
   - reinforcement_count ≥ 5 且時間集中：confidence 0.9（穩定模式，可升級 L3 Confirmed Memory）

### 5.4 Pattern Memory 的 decay 規則

借鑒 memU 的 preference aging 概念：

- **活躍窗口**：14 天滾動窗口（預設，可配置）
- **reinforcement_count 衰減**：
  - 14 天內無相同 content_hash 再次出現：reinforcement_count 保持，但 confidence 降至 0.5
  - 30 天內無相同 content_hash 再次出現：reinforcement_count 重置為 1，confidence 降至 0.3
  - 60 天以上：Pattern Memory 移至 archive，不參與即時 retrieval

### 5.5 Pattern Memory 的生成時機

Pattern Memory 由以下事件觸發生成（被動學習）：

- 使用者完成一筆 committed meal
- 使用者接受了 recommendation 並實際吃下
- 使用者在 chat 中明確提及飲食選擇
- 使用者拒絕了某類推薦並說明原因

### 5.6 Pattern Memory 的萃出維度

從 MealItem 萃取以下 pattern：

| Pattern Type | 萃取來源 | 例子 |
|-------------|---------|------|
| `food_preference` | meal_item.item_name / cuisine_family | 「偏好原波奶茶」「偏好雞胸肉」 |
| `store_preference` | meal_item.store_name | 「常去便利商店」 |
| `time_pattern` | meal_thread.occurred_at | 「下午3點常喝飲料」 |
| `location_pattern` | location_context | 「在公司附近午餐」 |
| `macronutrient_preference` | protein_g / carb_g / fat_g 分布 | 「偏好高蛋白飲食」 |
| `item_kind_preference` | meal_item.item_kind | 「偏主食類、不愛湯品」 |

---

## 6. Layer 3 — Confirmed Memory

### 6.1 起源

借鑒 **memU** 的 confirmed memory 概念 + **Hindsight** 的 World Facts 分離。

memU 將記憶分為：
- Pattern Memory：從行為中推斷
- Confirmed Memory：經明確確認的高信度記憶

Hindsight 將記憶分為：
- World Facts：關於世界的知識（「奶茶熱量高」）
- Experiences：個人經驗（「用戶喝了奶茶」）

### 6.2 Confirmed Memory 的來源

Confirmed Memory 只能來自兩種途徑：

1. **使用者明確口頭確認**
   - 「我不要喝奶茶」「我最近不吃沙拉」
   - 直接寫入 Confirmed Memory，不走 reinforcement 流程

2. **高一致性行為觀察升級**
   - 當 Pattern Memory 的 reinforcement_count ≥ 5
   - 且時間分佈在 30 天內
   - 且 confidence ≥ 0.9
   - 由系統自動建議升級為 Confirmed Memory
   - 使用者可在 UI 確認或拒絕

### 6.3 Confirmed Memory 的組成

```
ConfirmedMemory {
  confirmed_id: str
  memory_type: Literal["confirmed_preference", "confirmed_avoidance", "confirmed_schedule",
                      "confirmed_goal", "confirmed_negative"]
  subject: str              # "奶茶", "沙拉", "下午茶時段"
  confirmed_at: datetime     # 確認時間
  confirmed_source: Literal["user_verbal", "behavior_upgrade"]
  confidence: float         # 0.9-1.0
  expiry_policy: Literal["never", "user_override", "behavior_override"]
  last_validated_at: datetime  # 最後驗證時間
  expiry_note: str | null  # 過期原因或說明
  superseded_by: str | null # 若被新確認覆寫，記錄原 confirmed_id
}
```

### 6.4 Confirmed Memory 的優先級

Confirmed Memory 的權重高於 Pattern Memory：

1. **當下口頭聲明 > Confirmed Memory > Pattern Memory > generic**
   - 使用者說「我今天不想被提醒」：立即生效，壓過所有歷史記憶
   - Confirmed Memory：穩定高權重
   - Pattern Memory：可被 Confirmed Memory 覆寫

2. **Negative Preference 特殊處理**
   - `confirmed_negative` 和 `confirmed_avoidance` 是第一級公民（借鑒 memU 的 negative preference設計）
   - 不應只當作偏好系統的附帶欄位
   - 適用於：推薦避雷、proactive suppression、避免重複推薦使用者明確反感的食物

### 6.5 Confirmed Memory 的 decay 規則

不同於 Pattern Memory：

- `confirmed_source = user_verbal`：預設不自動 decay
  - 使用者可在 UI 修改或刪除
  - 若使用者後續穩定行為與確認內容衝突，系統提出「你的行為似乎與記錄的偏好不同，是否更新？」
- `confirmed_source = behavior_upgrade`：採用較慢 decay
  - 30 天內無相關行為再次出現，標記 `needs_validation`
  - 60 天內無相關行為，自動降級為 Pattern Memory

---

## 7. Layer 4 — Active Context (Working Memory)

### 7.1 起源

借鑒 Letta 的 Core Memory Blocks 概念。

Letta 將記憶分為：
- Core Memory：持久化的穩定資訊（persona、human）
- Working Memory：當前任務相關的動態上下文

### 7.2 Active Context 的組成

```
ActiveContext {
  context_id: str
  user_id: str
  session_id: str
  active_meal_thread_id: str | null  # 當前正在討論的 thread
  active_thread_summary: str          # thread 的簡短描述
  pending_clarifications: list[str] # 待澄清問題
  current_budget_posture: BudgetViewSnapshot
  today_intake_summary: str           # 今日已攝入摘要
  recent_recommendation_refused: list[str]  # 最近拒絕的推薦類型
  active_proposals: list[str]        # 当前有效的 proposal IDs
  proactive_suppression_state: SuppressionSnapshot
  context_freshness: datetime
}
```

### 7.3 Active Context 的生命週期

- **Session Start**：從當日 canonical state 组裝（CurrentBudgetView、ActiveMealView、OpenProposalsView）
- **Session 中**：即時更新，隨使用者操作動態變化
- **Session End**：主要上下文蒸發，關鍵訊號（如使用者拒絕推薦）寫入 Pattern Memory 或 Confirmed Memory

### 7.4 哪些資訊從 Active Context 蒸發

會話結束後，以下資訊寫入長期記憶後從 Working Memory 清除：

- 使用者明確的偏好/厭惡表達
- 使用者拒絕的推薦類型與原因
- 使用者提出的澄清需求

以下資訊蒸發，不寫入長期記憶：

- 臨時查詢意圖
- 未形成結論的對話
- 純資訊獲取行為

---

## 8. Temporal Fact Tracking（時間事實追蹤）

### 8.1 起源

借鑒 **Graphiti** 的 Temporal Fact 追蹤機制。

Graphiti 的核心概念：
- 每個事實有 `valid_at`（何時變 true）和 `invalid_at`（何時變 false）
- 可查詢「2024 年 3 月用戶的飲食偏好是什麼」

### 8.2 適用於本產品的方式

飲食偏好會隨減肥階段改變：

```
TemporalPreference {
  preference_id: str
  subject: str              # "高蛋白飲食", "輕食導向"
  valid_at: datetime       # 何時開始有效
  invalid_at: datetime | null  # 何時失效，null 表示目前仍有效
  source: str              # 來源（pattern_upgrade / user_verbal / calibration）
  superseded_by: str | null  # 若被新記錄取代，記錄新記錄 ID
  note: str | null         # 備註（如「減肥前期偏好」「春節期間放寬」）
}
```

### 8.3 使用情境

- **減肥階段追蹤**：「用戶在減肥前期偏好高蛋白，5月後轉為輕食導向」
- **季節性偏好**：「春節期間使用者偏好傳統糕點」
- **生活型態變化**：「用戶換工作後，午餐地點從公司附近變為住家附近」

### 8.4 Temporal Preference 的查詢語意

系統在 retrieval 時，預設只查詢 `invalid_at IS NULL OR invalid_at > now()` 的有效偏好。

但以下情況可查歷史偏好：
- 使用者明確問「我以前是不是...」
- Calibration 需要分析長期趨勢
- 推薦系統需要解釋「你以前偏好...但最近改變了」

---

## 9. Negative Memory（負面記憶）

### 9.1 起源

借鑒 **memU** 和 **Hindsight** 對負面偏好的一級支援。

memU 將 negative preference 作為一級記憶類型。
Hindsight 的 disposition 模型中允許模型帶有「避免負面輸出」的傾向。

### 9.2 Negative Memory 的分級

負面記憶不應只當作偏好系統的附帶欄位，應分為兩級：

```
NegativeMemory {
  negative_id: str
  subject: str              # 負面標的（食物名、類型、時段）
  negative_type: Literal["confirmed_negative", "inferred_avoidance", "situational_avoidance"]
  
  # confirmed_negative：用戶明確說「我不喝奶茶」「我對花生過敏」
  # inferred_avoidance：系統從行為推斷（「連續拒絕3次奶茶推薦」）
  # situational_avoidance：特定情境下的負面（工作日不喝甜的）

  confidence: float         # 0.0-1.0
  first_observed_at: datetime
  last_observed_at: datetime
  observation_count: int
  context_restriction: str | null  # 若為 situational，限制條件是什麼
  expiry_policy: str
}
```

### 9.3 Negative Memory 的應用場景

| 應用 | Negative Memory 類型 |
|------|-------------------|
| Recommendation Filtering | 所有三類都應被過濾 |
| Proactive Suppression | `confirmed_negative` 和 `inferred_avoidance` 應抑制對應觸發 |
| Calibration Signal | `situational_avoidance` 應被視為意圖干擾訊號 |
| UI Warning | `confirmed_negative` 應在 UI 顯示為確認的過敏/厭惡 |

### 9.4 Negative Memory 的生成時機

- 使用者明確說「我不吃...」「我對...過敏」「我最近不想...」
- 使用者連續 3 次拒絕同一類推薦 → 升級為 `inferred_avoidance`
- 使用者接受推薦但實際未消費 → `situational_avoidance`

---

## 10. Memory Retrieval 與 Consumption

### 10.1 Retrieval 的分層順序

```
┌──────────────────────────────────────────┐
│         Memory Retrieval Pipeline          │
├──────────────────────────────────────────┤
│  Step 1: Confirmed Memory Check            │
│  ────────────────────────────────────── │
│  目的：先問 Confirmed Memory              │
│  問題：「這個使用者的 confirmed preference │
│  是否涵蓋目前 context？」                  │
│  若是：直接使用 Confirmed Memory          │
│  若否：繼續 Step 2                        │
│                                          │
│  Step 2: Pattern Memory Retrieval          │
│  ────────────────────────────────────── │
│  目的：查詢高 confidence Pattern          │
│  只取 confidence ≥ 0.5 的 Pattern        │
│  按 reinforcement_count 排序              │
│  若無 → 退至 Step 4                       │
│  若有 → 繼續 Step 3                        │
│                                          │
│  Step 3: Temporal Preference Check        │
│  ────────────────────────────────────── │
│  目的：檢查是否有時間限制的偏好             │
│  「這個偏好只在減肥前期有效？」              │
│  若是：套用 valid_at / invalid_at 過濾     │
│  繼續 Step 4                              │
│                                          │
│  Step 4: Active Context Enrichment        │
│  ────────────────────────────────────── │
│  目的：用當前 session 上下文補充           │
│  加入 today_intake_summary                │
│  加入 pending_clarifications             │
│  加入 recent_refused_patterns             │
│                                          │
│  Step 5: Semantic Fallback                │
│  ────────────────────────────────────── │
│  目的：若以上都無結果，使用 semantic search │
│  向量化檢索 L1 canonical history           │
│  最大時間窗口：14 天                       │
└──────────────────────────────────────────┘
```

### 10.2 各 Flow 的 Retrieval 優先順序

借鑒現有 L4B Retrieval Policy Spec，並與本 L4 記憶模型對齊：

#### Intake Flow
1. Active Context（當前 thread 上下文）
2. RecentCommittedMealsView（近 7 天）
3. Confirmed Memory（過敏/厭惡檢查）
4. Pattern Memory（最近觀察到的偏好）
5. Semantic fallback（L1 history）

#### Recommendation Flow
1. Confirmed Memory（穩定偏好）
2. Active Body Plan（當前減肥階段偏好）
3. Pattern Memory（reinforcement_count ≥ 3 的模式）
4. Temporal Preference（檢查時間有效性）
5. Golden Orders（高執行性 item bundle）
6. Location/Time Pattern
7. Active Context
8. Semantic fallback

#### Calibration Flow
1. Active Body Plan View
2. Body Observation window summary
3. Intake Completeness Summary
4. Pattern Memory（intake bias pattern）
5. Temporal Preference（長期趨勢）

#### Rescue Flow
1. Current Budget View
2. Recent Committed Meals（近 7 天 overshoot pattern）
3. Rescue History Summary
4. Pattern Memory（爆卡觸發模式）
5. Confirmed Memory（已知厭惡）

### 10.3 當下口頭聲明的優先級

借鑒 L4B Retrieval Policy Spec 的規則：

若使用者在當前 turn 明確表示：
- 「我今天不想喝奶茶」
- 「我最近在減醣」
- 「我今天不想被提醒」

則 retrieval / ranking 應讓當下口頭聲明優先於所有歷史統計記憶，即使 Confirmed Memory 有不同內容。

實作方式：
- 當前 turn 的顯式聲明寫入 Active Context，並標記為 `utterance_override`
- `utterance_override` 在該 session 內有效
- Session 結束後，若使用者再次明確確認，才寫入 Confirmed Memory

---

## 11. Proactive Memory（主動記憶）

### 11.1 起源

借鑒 **memU** 的 Proactive Memory 概念 + **Hindsight** 的 Mental Model。

memU 的 proactive 設計：
- Bot 在背景持續監控、學習
- 預測用戶下一步需求
- 主動注入相關記憶

Hindsight 的 Mental Model：
- reflect 操作：深度分析現有記憶，生成高層次理解
- 「用戶在壓力大時的飲食決策模式」

### 11.2 Proactive Memory 的觸發條件

Proactive Memory 應在以下時機被喚醒：

```
ProactiveTrigger {
  trigger_type: Literal["meal_reminder", "snack_opportunity", "budget_alert", 
                        "calibration_suggestion", "preference_learning"]
  trigger_conditions: dict  # 觸發條件
  suppression_state: SuppressionSnapshot
  fired_at: datetime | null
  auto_fire_eligible: bool
}
```

### 11.3 Proactive Memory 的 suppression 機制

借鑒 memU 和現有 ProactiveTrigger 設計：

- **Quiet Hours**：使用者在特定時段不想被打擾
- **Ignore History**：使用者已連續忽略某類提醒 N 次
- **Recent Fire Count**：某類 proactive 最近已觸發 M 次
- **User Preference Suppression**：Confirmed Memory 中的明確偏好抑制

### 11.4 Nightly Reflect（夜間深度分析）

借鑒 Hindsight 的 `reflect` 操作：

每晚可執行一次深度分析，生成以下Insights：

```
NightlyInsight {
  insight_id: str
  user_id: str
  generated_at: datetime
  insight_type: Literal["pattern_shift", "adherence_change", "preference_evolution",
                        "budget_mismatch", "situational_trigger"]
  content: str               # 生成的 insight 文字
  confidence: float          # 0.0-1.0
  based_on_window_days: int   # 分析的時間窗口
  recommended_action: str | null  # 建議的 proactive 行動
  presented_to_user: bool    # 是否已呈現給使用者
  user_feedback: str | null  # 使用者回饋
}
```

**何時執行 Reflect**：
- 每日 `23:00`（與 `ProactiveScheduler.nightly_run_time` 對齊，見 L1 Runtime Ownership Spec Section 4.8）
- 或在 calibration proposal 產生前

**Reflect 的分析維度**：
- 過去 7 天攝入 pattern 是否有改變
- 使用者是否偏離了既定預算
- 是否有新的厭惡模式浮現
- 推薦接受率是否下降（可能需要調整策略）

---

## 12. PreferenceProfileSummary — 記憶的聚合視圖

### 12.1 定位

`PreferenceProfileSummary` 是 Recommendation Flow 可讀的偏好摘要，是記憶系統的下游消費介面。

它不是 raw memory，也不是全量歷史資料，而是由 Pattern Memory 和 Confirmed Memory 聚合出的 summary view。

### 12.2 PreferenceProfileSummary 的欄位

```
PreferenceProfileSummary {
  user_id: str
  generated_at: datetime
  freshness: Literal["current", "stale", "empty"]
  
  # Distribution Fields
  item_kind_distribution: dict[str, float]     # e.g., {"主食": 0.4, "飲料": 0.3, "湯品": 0.1}
  staple_type_distribution: dict[str, float]   # e.g., {"飯類": 0.6, "麵類": 0.4}
  cuisine_family_distribution: dict[str, float]
  protein_posture: Literal["high", "medium", "low"]
  
  # Preference Signals
  confirmed_preferences: list[ConfirmedMemory]     # 高權重
  strong_patterns: list[PatternMemory]          # reinforcement_count ≥ 3
  drink_preference_strength: float               # 0.0-1.0
  snack_avoidance_pattern: str | null            # 若有觀察到
  
  # Behavioral Signals
  acceptance_rate_by_category: dict[str, float]  # 推薦接受率
  recent_refused_patterns: list[str]            # 最近拒絕的類型
  situational_patterns: list[TemporalPreference] # 具時間限制的偏好
  
  # Negative Memory
  confirmed_negatives: list[NegativeMemory]       # 已確認厭惡
  inferred_avoidances: list[NegativeMemory]     # 推斷厭惡
  
  # Location/Time
  location_patterns: list[str]
  time_of_day_patterns: dict[str, list[str]]      # e.g., {"下午": ["飲料"], "中午": ["便當"]}
  
  # Recommendation Hints
  golden_orders: list[GoldenOrder]               # 高執行性 item bundle
  fallback_stores: list[str]                      # 備用店家
}
```

### 12.3 與 L2/L3 Spec 的對齊

- 本 spec 中的 `PreferenceProfileSummary` 直接對應 L3.2 Recommendation Spec 中的 contract
- Golden Order 概念來自 L3.2 Spec：favorite stores + item bundle 的高執行性記憶
- Cold-start / sparse-memory 規則遵從 L3.2 Spec：empty summary 時退至 safe defaults

---

## 13. 與現有架構的對齊

### 13.1 對 L2 Data Model

L4 Memory 建立在 L2 Canonical Objects 之上：
- Pattern Memory 的 source_meal_item_ids 指向 L2 MealItem
- Temporal Preference 的 valid_at / invalid_at 以 L2 occurred_at 為準
- Confirmed Memory 是 L2 之上的額外詮釋層，不取代 canonical truth

### 13.2 對 L3.x Runtime Flows

- **L3.1 Intake**：使用 Active Context + Pattern Memory 做即時偏好匹配
- **L3.2 Recommendation**：使用 PreferenceProfileSummary（已對齊本 spec）
- **L3.3A Calibration**：使用 Pattern Memory 分析 intake bias，使用 Temporal Preference 分析長期趨勢
- **L3.4 Rescue**：使用 Rescue History Pattern + Confirmed Negative Memory

### 13.3 對 L4B Retrieval Policy

本 spec 補充了 L4B Retrieval Policy 的實作細節：
- Step 1-5 的 retrieval pipeline 是 L4B 精神的具體化
- Confirmed Memory → Pattern Memory → Temporal Preference → Active Context → Semantic 的層次直接對應 L4B 的「先 summary，後 raw」原則

---

## 14. 測試情境

後續實作至少應覆蓋：

1. **Pattern Memory 生成**
   - 使用者連續 3 次選擇雞胸肉，reinforcement_count 正確遞增
   - 14 天後相同選擇，reinforcement_count 保持（未重新計算窗口）
   - 30 天後相同選擇，reinforcement_count 重置為 1

2. **Confirmed Memory 升級**
   - Pattern Memory reinforcement_count = 5 時，系統提示升級確認
   - 使用者口頭說「我不喝奶茶」，直接寫入 Confirmed Memory

3. **Negative Memory**
   - 使用者連續拒絕 3 次奶茶推薦，升級為 inferred_avoidance
   - confirmed_negative 在 Recommendation flow 中被正確過濾

4. **Temporal Preference**
   - 使用者減肥前期偏好高蛋白，後期改為輕食，時間窗正確切換
   - 查詢歷史偏好（「我以前是不是比較喜歡...」）正確返回

5. **Active Context**
   - Session 開始時正確組裝當日上下文
   - Session 結束時，關鍵訊號寫入 Pattern Memory

6. **utterance_override**
   - 使用者說「今天不想喝奶茶」，當下 override Confirmed Memory
   - Session 結束後，override 失效，回到 Confirmed Memory

7. **Proactive Memory**
   - 使用者忽略某類提醒 3 次，suppression 正確啟動
   - Nightly reflect 正確生成 pattern_shift insight

---

## 15. v1 實作預設決策

1. **Pattern Memory 窗口**：14 天滾動窗口
2. **reinforcement_count 衰減**：30 天無觀察，重置為 1
3. **Confirmed Memory 升級門檻**：reinforcement_count ≥ 5 且 confidence ≥ 0.9
4. **Negative Memory 推斷門檻**：連續 3 次拒絕同一類
5. **Temporal Preference 查詢**：預設只查有效偏好（invalid_at IS NULL）
6. **utterance_override 有效期**：單一 session
7. **Nightly Reflect 執行時間**：每日 `23:00`（與 `ProactiveScheduler.nightly_run_time` 對齊；canonical source 為 L1 Section 4.8）
8. **Semantic Fallback 窗口**：14 天（L1 canonical history）

---

## 16. 與其他 Framework 的對齊摘要

| Framework | 引用概念 | 本產品實作位置 |
|----------|---------|-------------|
| memU | reinforcement_count | Layer 2 Pattern Memory |
| memU | content_hash dedupe | PatternMemory.content_hash |
| memU | memory_type 分類 | PatternMemory.pattern_type |
| Hindsight | World/Experience 分離 | Confirmed Memory vs Pattern Memory |
| Hindsight | reflect 操作 | NightlyInsight + Proactive Memory |
| Graphiti | valid_at/invalid_at | TemporalPreference |
| Graphiti | Entity Graph linking | 食物關係圖（未來擴展） |
| Letta | Core/Working Memory 分層 | Layer 1/3 vs Layer 4 |
| Letta | block label 嵌套結構 | ActiveContext 組件設計 |
| mem0 | User/Session 分層 | ActiveContext.session_id 追蹤 |

---

## 17. 未來擴展預留

以下為本 spec 暫不實作，但預留 extension point 的方向：

1. **食物關係圖（Food Relationship Graph）**
   - Graphiti-style 的 entity linking
   - 「雞胸肉 → 高蛋白 → 適合午餐」
   - 「奶茶 → 高糖 → 應避免在減肥前期推薦」

2. **Causal Inference**
   - Hindsight-style 的 causes/caused_by linking
   - 「加班 → 跳過午餐 → 晚上暴食」
   - 預防性 proactive trigger

3. **Cross-user Pattern Mining**
   - 匿名化後的群體趨勢分析
   - 「大多數減肥使用者在週末失控」
   - 增強集體輔導模組
