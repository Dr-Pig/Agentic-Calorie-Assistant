# L4A Memory Model Spec

## 1. 目的

這份 spec 定義 agent 的 memory model。

它回答：

- 系統應保留哪些類型的記憶
- 這些記憶層彼此如何分工
- 哪些屬於 canonical state，哪些屬於 derived memory
- 哪些記憶可以被直接讀取，哪些只能作為 summary view
- 哪些記憶可被確認、修正、衰減或失效

**關於 Promotion 與 Demotion 規則**：詳細的升級/降級邏輯、Entity Normalization 流程，請參閱 [L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md](./L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md)。

它暫時不回答：

- retrieval ranking（見 L4B）
- context packing token 順序（見 L4C）
- prompt wording

---

## 2. 核心原則

### 2.1 Memory 不是單一資料池

本系統的 memory 應至少分成多層，而不是把：

- raw history
- pattern inference
- confirmed preference
- proactive suppression

全部混成一個 blob。

### 2.2 Canonical 與 Memory 要分離

canonical product objects 仍以 `L2` 為準。  
memory 不是用來取代 canonical state，而是讓 runtime 更有效率、更連續。

### 2.3 Memory 要允許時間性

不是所有記憶都永久有效。

memory model 必須支持：

- recency weighting
- preference aging
- suppression expiry
- pattern invalidation
- temporal validity windows for durable facts or preferences that can become stale or superseded
- provenance back to the typed-history source that caused a durable memory to be created or invalidated

### 2.4 記憶要有 freshness

memory 不只需要 decay，還需要 freshness / staleness 訊號。

derived memory 與 pattern memory 應至少可帶：

- `last_observed_at`
- `freshness_posture`
- optional `staleness_note`

---

## 3. Memory Layers

### 3.1 L1 `Typed History`

最底層的歷史記憶。

包含：

- `MessageEvent`
- `MealThread / MealVersion / MealItem`
- `BodyObservation`
- `ProposalContainer / ProposalOption`
- `ProactiveTrigger`
- rescue / calibration outcome history

角色：

- audit source
- retrieval base layer
- pattern layer 的原始來源

### 3.2 L2 `Pattern Memory`

從 typed history 聚合出的穩定模式。

**L2 分兩個子層，責任不同：**

#### L2a `Statistical Pattern`（deterministic）

純統計聚合，由 nightly consolidation 的 deterministic 部分產出。

包含：

- 常見 `MealItem` 分類分布（`item_kind`、`staple_type`）
- 飲料偏好強度（`drink_preference_strength`）
- store / chain pattern
- time-of-day patterns（幾點吃什麼類型，純統計）
- location patterns
- intake logging completeness pattern
- rescue viability pattern

角色：

- recommendation 的 hard constraint filtering 與 deterministic ranking basis
- calibration 的 logging-quality / adherence basis
- proactive 的 timing basis

#### L2b `Semantic Pattern`（LLM extraction）

由 LLM 從 raw MealItem 時間序列中提取的語意性、情境性、趨勢性 pattern。

包含：

- 時段性條件偏好（例如「下午茶時段偏好甜飲，晚餐後選無糖」）
- 情境性偏好（例如「工作日選便當，週末選麵食」）
- 趨勢性變化（例如「最近開始避免油炸食物，但之前很常吃」）
- 飲食情緒 pattern（例如「壓力大時傾向高熱量食物」）

角色：

- recommendation 的 soft preference ranking basis（比 L2a 更豐富）
- NightlyInsight 的輸入來源
- confirmed memory 升級的候選依據

#### L2b Semantic Pattern Extraction 規則

**觸發條件**（兩個條件都要滿足）：

- 累積 **21 筆新 committed MealItem** 尚未被納入 semantic extraction
- 距離上次 semantic extraction 超過 **7 天**

**Input**：最近 21 筆 MealItem，每筆包含：

- `occurred_at`（時間戳，用於判斷時段、星期幾）
- `item_name`（原始食物名稱）
- `item_kind`、`staple_type`、`cuisine_family`
- `consumption_note`（使用者補充的描述，例如「半糖少冰」）
- `preference_tags`（已有的標籤）

**LLM 任務**：從這批資料的時間序列中找出時段性、情境性、趨勢性的 pattern，輸出結構化的 semantic pattern items。

**Output schema**（每個 semantic pattern item）：

```json
{
  "pattern_type": "contextual_preference | temporal_preference | trend_shift | situational_avoidance",
  "description": "<自然語言描述，例如「下午茶時段偏好甜飲，晚餐後傾向無糖」>",
  "evidence_window_days": 7,
  "evidence_meal_count": 21,
  "confidence": 0.75,
  "time_condition": "<若有時段條件，例如 afternoon_vs_evening>",
  "food_category": "<若有食物類別，例如 飲料>",
  "trend_direction": "increasing | decreasing | stable | null",
  "content_hash": "<用於去重>",
  "extracted_at": "<ISO 8601>"
}
```

**規則**：

- LLM 只負責提取 pattern，不負責判斷是否升級為 confirmed memory
- 若 pattern 的 `confidence < 0.5`，不寫入 L2b，只記錄在 trace
- 同一 `content_hash` 的 pattern 再次出現時，更新 `reinforcement_count`，不重複建立
- L2b 的 pattern 不直接取代 L2a 的統計，兩者並存

角色：

- recommendation 的 soft preference basis
- calibration 的 logging-quality / adherence basis
- proactive 的 timing basis

### 3.2A Pattern Reinforcement Identity

Pattern memory 不應靠自由文字重複堆疊。

至少應支持：

- `content_hash`
- `reinforcement_count`
- `last_reinforced_at`

目的：

- 對同一 pattern 做去重，而不是持續建立語意重複的記憶項
- 區分單次觀察與反覆被強化的模式
- 讓 freshness 與 reinforcement 可以一起被讀取，而不是只看最近一次出現

這個 reinforcement identity 只適用於 pattern / derived memory；
不應拿來取代 canonical event history。

### 3.3 L3 `Confirmed Memory`

經使用者明確確認，或高信度長期穩定成立的記憶。

包含：

- confirmed dislikes / preferences
- confirmed schedule constraints
- confirmed target / pace preference
- confirmed suppression preference
- high-confidence stable preference

角色：

- 高權重 preference source
- 比 pattern memory 更穩定
- 但仍需可撤回、可過期、可更新

### 3.4 `Negative Preference Memory`

負面記憶應是一級記憶，不應只當成偏好系統的附帶欄位。

至少分成：

- `confirmed_negative_preference`
- `inferred_avoidance_pattern`

適用於：

- recommendation 避雷
- proactive suppression
- 避免重複推薦使用者明確反感的食物 / 類型 / 時段

### 3.5 `Temporary Preference`

 временный 偏好是一種獨立的記憶類型，適用於「不是一次性，但也不是長期」的偏好。

**與 Confirmed Memory 的區別**：
- Confirmed Memory：長期穩定，預設不 decay
- Temporary Preference：有明確過期時間，到期自動失效

**結構**：
- `valid_from` / `valid_until`：有效時間範圍
- `context_scope`：什麼情境有效（午餐/晚餐/工作日）
- `expires_in_days`：或用天數計算

**範例**：
- 「這週在減醣」
- 「這兩天不想吃辣」
- 「今天不要推薦太油的」

詳細規則見 [L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md](./L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md) Section 3.6。

### 3.6 `Golden Orders`（Derived View）

**重要澄清**：Golden Order 不是從 Pattern Memory「升級」來的，而是從 canonical history 直接派生的 materialized view。

```
Golden Order = 從 L1 Canonical History materialized 的 derived view
             ≠ Pattern Memory 的 promotion 結果
```

Golden Order 的核心是：
- 特定店家 + 特定 item bundle
- 在短期窗口內穩定重複
- 是「事實層」，不是「推論層」

詳細規則見 [L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md](./L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md) Section 3.3。

### 3.6A `Reusable Personal Meal / Personal Meal Template`

這是一種**使用者範圍內、可重用、結構化**的餐點記憶物件。

適用於：

- 重複出現的自煮菜
- 不在 FoodDB 內但常常重複吃的固定餐
- 固定組合的外食套餐
- 有明確個人做法的飲料或配料組合

核心定位：

- 屬於 long-term memory family
- 不是 transcript memory
- 不是 FoodDB truth
- 不是 global food alias
- 不是一次估完就自動升級的 cache

它應該至少帶：

- `user_scope`
- `template_id`
- `template_label`
- `source_meal_refs`
- `estimate_profile`
- `last_confirmed_at`
- `superseded_by`
- `freshness_posture`

規則：

- `Reusable Personal Meal` 必須 reference canonical meal history 或已確認的 estimate 來源，不能憑 LLM 常識建立。
- 它的 truth posture 是「user-scoped reusable meal memory」，不是 nutrition evidence store。
- 若使用者說法明顯是在指同一份餐，可以拿來做 reuse / confirm / re-estimate 的候選。
- 若 recipe、配料、份量、糖冰、烹調方式已改變，應產生 supersede 或 re-estimate，而不是靜默覆蓋舊模板。
- 它可以提升重複餐點記錄效率，但不得取代 canonical meal thread、budget ledger、FoodDB evidence 或 shared runtime truth。

和 `Golden Order` 的差別：

- `Golden Order`：從 canonical history materialize 出來的重複店家+套餐視圖
- `Reusable Personal Meal`：可被使用者明確重用、修正、版本化的個人餐點模板

前者偏 observation / ranking basis，後者偏 reuse / confirmation / correction basis。

### 3.7 `Archive`

不再參與即時 retrieval 的記憶會被移至 Archive。

- Pattern Memory 60 天無新觀察
- Golden Order 90 天無重複
- 被 demote 的記憶

Archive 中的記憶仍可被查詢（用於歷史分析），但不參與即時推薦。

---

## 4. Memory Domains

memory model 應至少覆蓋以下 domain：

### 4.1 Intake Memory

- active meal continuity
- historical meal recall
- common item bundles
- intake estimation bias history

### 4.2 Recommendation Memory

- `PreferenceProfileSummary`
- golden orders
- store familiarity
- accepted / ignored recommendation patterns

### 4.3 Calibration Memory

- body-weight observation history
- operating expenditure history
- logging quality history
- mismatch attribution history

### 4.4 Rescue Memory

- rescue history
- rescue horizon outcomes
- recovery viability history
- repeated overshoot pattern

### 4.5 Proactive Memory

- suppression state
- quiet hour preference
- ignored nudges
- accepted nudge patterns

---

## 5. Memory Objects vs Derived Memory Views

### 5.1 canonical objects

仍由 `L2` 定義，例如：

- `MealThread`
- `MealVersion`
- `MealItem`
- `BodyPlan`
- `ProposalContainer`

### 5.2 derived memory views

memory 層應提供至少這些 derived views：

- `PreferenceProfileSummary`
- `IntakeCompletenessSummary`
- `RescueHistorySummary`
- `AdherenceSummary`
- `CalibrationHistorySummary`
- `SuppressionSummary`
- `GoldenOrderSummary`

### 5.3 Memory Inspectability And Change History

durable memory 不應是不可檢查的黑盒。

至少對 confirmed memory 與高權重 pattern memory，系統應允許：

- inspect current memory object
- correct / invalidate it through explicit product flow
- read change history when memory meaning materially changes

目的：

- 避免 durable memory 悄悄漂移而無法追查
- 讓使用者修正與系統自動更新可以被區分
- 讓 runtime 能分辨「目前有效內容」與「過去曾成立但已被覆寫的內容」

### 5.4 Minimal `MemoryRecord` Envelope

V1 記憶應以 `MemoryRecordStore` 作為 runtime truth，human-readable markdown surfaces 只是 review、projection、或 debug view。

最小 record envelope：

```yaml
MemoryRecord:
  id: string
  record_type:
    - confirmed_preference
    - pattern_memory
    - temporary_preference
    - negative_preference
    - suppression_rule
    - golden_order
    - recall_summary
  family: diet_product | app_interaction | proactive_control | conversation_recall
  status: candidate | pending_review | confirmed | rejected | archived | superseded
  summary: natural_language
  polarity: positive | negative | neutral
  strength: boost | downrank | block
  scope_keys:
    user_id: string
    workspace_id: string
    project_id: string
    surface: string
  source_refs: list
  consumers: list
  validity: optional window
  history: change refs
```

`summary` 是可讀描述，不是唯一可查欄位。`record_type`、`family`、`polarity`、`strength`、`scope_keys`、`source_refs`、`validity`、`status` 必須能被 deterministic validators 檢查。

---

## 6. Preference Memory

### 6.1 最小 preference fields

- `item_kind_distribution`
- `staple_type_distribution`
- `drink_preference_strength`
- `store_affinity`
- `time_of_day_patterns`
- `location_patterns`
- `accepted_recommendation_patterns`
- `ignored_recommendation_patterns`

### 6.1A Preference Polarity And Negative Priority

正向與負向偏好共用 `MemoryRecord` envelope，不建立兩套無法比較的偏好機制。

必要欄位語義：

- `polarity=positive`：可作為 recommendation / rescue / proactive 的 boost 或 explanation context。
- `polarity=negative`：優先作為 blocker 或 downranker。
- `strength=block`：使用者明確表示不吃、不要推薦、禁忌、過敏、或等價硬限制。
- `strength=downrank`：使用者表示不喜歡、不太偏好、太清淡、太麻煩、或只有在沒有更好選項時才接受。
- `strength=boost`：偏好、常用、喜歡、折扣敏感、飽足感偏好等正向排序訊號。

Confirmed negative 的處理優先於 positive boost：

- `block` 必須先排除候選，除非使用者在同一 turn 明確要求破例且不違反安全 / 健康限制。
- `downrank` 必須降低排序或要求 explanation，不得被一般 positive preference 直接抵消。
- positive preference 只能在 remaining allowed pool 內排序，不能覆蓋 negative blocker。
- 使用者要求「不要記」或語意自我矛盾時，不建立 confirmed memory；可建立 review item 或忽略。

### 6.2 preference aging

preference memory 應支持：

- 新近行為提權
- 舊偏好衰減
- confirmed preference 的較慢衰減

### 6.3 Golden Orders

`golden orders` 應視為高信度 item bundle memory。

它不是只有店家偏好，而是：

- 特定店家
- 特定 item 組合
- 特定時段 / 地點情境

共同構成的高執行性記憶。

### 6.4 Preference Transparency

`PreferenceProfileSummary` 應允許對使用者透明。

也就是：

- UI 可顯示 AI 提取出的偏好側寫
- 使用者可確認、修正、刪除或否定某些偏好
- 被使用者明確否定的偏好應優先影響 confirmed / negative memory

### 6.5 Conversation Style Profile Extension Note

目前 repo 尚未定義 canonical `conversation_style_profile`。

也就是說，系統目前沒有 `sour.md` 等價的正式 memory object 來承載：

- communication tone preference
- explanation density preference
- blunt vs gentle framing
- user-specific response-style adaptation

這一層目前只作為後續 `2.7` memory/context extension point。

v1 規則：

- 不把 style profile 寫成 active runtime contract
- 不把 style preference 當成 `2.7a` / `2.7b` semantic routing 的前置依賴
- 先證明 semantic routing foundation，再決定 style-profile materialization 與 retrieval policy

---

## 7. Logging / Adherence Memory

### 7.1 logging quality memory

應保留：

- 近 7 / 14 天 intake coverage
- late logging pattern
- low-confidence meal density
- weight logging consistency

### 7.2 adherence memory

應保留：

- budget adherence pattern
- rescue completion pattern
- proposal acceptance / rejection tendency

這些記憶不是 moral judgment，而是 runtime quality signal。

---

## 8. Suppression / Preference Memory

### 8.1 suppression memory

至少應保留：

- muted trigger categories
- recently ignored proactive classes
- quiet hours
- recent fire frequency

### 8.2 confirmed preference override

若使用者明確確認：

- 不想被提醒某類事情
- 不想被推薦某類食物

應進 confirmed memory，而不是只留在短期 suppression state。

---

## 8A. What Not To Save

memory 系統不應變成 canonical state 或 transcript 的重複副本。

不應保存：

- 已可由 `L2` canonical objects 直接推回的事實副本
- 純暫時性的當前 turn 任務細節
- 可直接由 current UI / current ledger state 得知的瞬時值
- 沒有未來價值的重複描述

應優先保存：

- 會影響未來互動的偏好
- 會影響 retrieval / recommendation / proactive 的模式
- 會影響 logging quality / adherence / rescue / calibration 判斷的長期訊號

---

## 9. Memory Lifecycle

> **詳細的 Promotion 與 Demotion 規則**：請參閱 [L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md](./L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md)。

### 9.1 Create

記憶可由以下路徑生成。詳細規則見 L4D Section 3。

#### 路徑 1：使用者直接聲明（最快，最高優先）

使用者在 chat 中明確說「記住我不喝含糖飲料」、「我對花生過敏」等。

- 直接寫入 **Confirmed Memory** 或 **Negative Preference Memory**
- 不需要等 consolidation
- 不需要 reinforcement_count 門檻
- 由 intake Pass 1 的 `task_meal_link_pass` 或 general chat routing 識別後，交由 application layer 寫入

#### 路徑 2：行為累積 → Pattern Memory（中速）

同一行為反覆出現時，建立 Pattern Memory。

- 同一 store + item bundle 出現 3 次
- 或同一 item_kind 出現 5 次

#### 路徑 3：Canonical History → Golden Order（Materialization）

Golden Order 是從 canonical history 直接派生的 derived view，不是「升級」來的。

- 30 天內同一 store + bundle 出現 ≥ 3 次
- 最近 60 天仍有新觀察

#### 路徑 4：Pattern → Confirmed（需使用者確認）

**重要**：只能由以下兩條合法路徑觸發，LLM 不能自己完成升級：

- **路徑 4a**：系統建議 + 使用者確認
- **路徑 4b**：使用者口頭確認

詳細規則見 L4D Section 3.4。

#### 路徑 5：修正 → Canonical Truth

使用者修正餐點估算時，只更新 Canonical MealItem，不寫入 Pattern Memory。

#### 路徑 6：一次性 / Temporary 偏好

- 一次性實驗 → 不寫入
- Temporary Preference → 寫入（帶 valid_until）
- 長期偏好 → 寫入 Pattern Memory
- Confirmed Negative → 寫入 Confirmed Memory

詳細規則見 L4D Section 3.6。

#### 路徑 7：nightly deterministic consolidation（持續更新）

每日 23:00 由 `ProactiveScheduler` 觸發。

- deterministic 統計更新 **L2a Statistical Pattern**
- 更新 `PreferenceProfileSummary`、`IntakeCompletenessSummary` 等 derived views
- 不需要 LLM

### 9.2 Update

記憶可因：

- 新歷史資料
- 使用者修正
- 長期新模式

更新。

### 9.3 Decay & Demotion

pattern 與偏好記憶應隨時間衰減或降級。

**詳細的 Demotion 規則**：請參閱 [L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md](./L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md) Section 4。

**最小原則**：
- Pattern Memory：30 天無新觀察 → 降權，60 天 → archive
- Golden Order：60 天無重複 → inactive，90 天 → archive
- Behavior-upgraded Confirmed：30 天無相關行為 → needs_validation，60 天 → 降級為 Pattern
- Confirmed Negative（user_verbal）：不自動 demote，除非使用者明講取消

### 9.3A Consolidation

memory consolidation 應被視為正常 lifecycle，而不是緊急清理。

v1 可採：

- 7 天或 21 筆餐點作為滾動 consolidation window

目標是把瑣碎歷史壓縮成：

- 穩定偏好標籤
- rescue / adherence pattern
- logging quality summary

### 9.3A-1 WeeklyInsightReport（週報洞察）

`WeeklyInsightReport` 是每週產生一次的使用者行為洞察報告，屬於 derived view，不是 canonical object。

**定位：**
- 不是 calibration（那是系統內部的數學調整）
- 是給使用者看得懂的行為洞察，幫助他們理解自己的模式
- 由 `ProactiveScheduler` 的 weekly run 觸發（例如每週一早上）

**最小欄位：**

- `report_id`
- `user_id`
- `week_start_date`
- `week_end_date`
- `generated_at`
- `deficit_achievement_rate`：本週赤字達成率（例如 71%）
- `overshoot_days`：超標天數
- `overshoot_pattern`：超標集中在哪些時段 / 星期幾（例如「週三晚上」）
- `top_calorie_sources[]`：熱量來源前三名（例如「飲料佔 18%」）
- `logging_coverage`：本週 intake logging 覆蓋率
- `weight_trend_summary`：體重趨勢摘要（若有足夠觀測）
- `swap_opportunities[]`：具體可執行的替換建議（來自 L3.2 swap suggestion）
- `positive_highlights[]`：正向行為亮點（例如「你這週有 4 天達標」）
- `narrative_summary`：LLM 生成的自然語言摘要（1-3 句）

**規則：**
- `WeeklyInsightReport` 是 read-only derived view，不直接改寫任何 canonical state
- `narrative_summary` 由 LLM 生成，但數字來源必須是 deterministic 計算結果
- 若本週資料不足（例如 logging coverage < 50%），應降級輸出，不強行生成洞察
- 報告透過 chat 主動推送（proactive），也可在 UI 歷史頁面查看

### 9.3B Consolidation 觸發機制

#### 觸發者

memory consolidation 由 `ProactiveScheduler` 的 `pattern_insight_check` 負責觸發。

它不是獨立的 background job，而是 nightly run 的一部分。

觸發時機：

- 每日凌晨（預設 `23:00`，與 `ProactiveScheduler.nightly_run_time` 對齊）
- 若當日有超過 `5` 筆新 committed meal，可提前觸發一次 partial consolidation

#### 執行條件

consolidation 應在以下條件都滿足時才執行：

- 距離上次 consolidation 超過 `24` 小時
- 有新的 `MealItem` 或 `BodyObservation` 尚未被納入 pattern summary

若條件不滿足，跳過本次 consolidation，不報錯。

#### `PreferenceProfileSummary` 的 materialization policy

`PreferenceProfileSummary` 採 **pre-materialized** 策略：

- 每次 consolidation 完成後，重新計算並寫入 `PreferenceProfileSummary`
- runtime 讀取時直接讀 pre-materialized 版本，不 on-demand 計算
- `PreferenceProfileSummary` 應帶有 `generated_at` 與 `freshness_posture` 欄位
- 若 `generated_at` 超過 `48` 小時，`freshness_posture` 標記為 `stale`
- `stale` 狀態下，recommendation flow 仍可使用，但應降低對 pattern memory 的信心權重

#### 失敗處理

consolidation 失敗時：

- 記錄 error 到 trace / observability layer
- 不影響 canonical state（`MealThread`、`BodyPlan` 等不受影響）
- 不重試（等待下一個 nightly run）
- `PreferenceProfileSummary` 保留上一次成功的版本，`freshness_posture` 標記為 `stale`
- 若連續 `3` 天 consolidation 失敗，應觸發 system alert（不對使用者顯示）

#### Consolidation 的輸出

每次 consolidation 至少更新：

- `PreferenceProfileSummary`
- `IntakeCompletenessSummary`
- `AdherenceSummary`
- `RescueHistorySummary`（若有新 rescue 事件）
- `CalibrationHistorySummary`（若有新 calibration 事件）

### 9.4 Invalidate

若新證據強烈衝突，舊 pattern 應可失效。

當 durable memory 被失效或覆寫時，應保留最小可追溯資訊：

- previous semantic content or summary
- invalidated_at / superseded_at
- invalidation reason or source posture

### 9.5 Confirm

某些 pattern 可升級為 confirmed memory。

**重要**：Pattern → Confirmed 只能由以下兩條合法路徑觸發：
- 系統建議 + 使用者明確確認
- 使用者口頭確認

LLM 可以「提議」升級，但不能自己完成升級。

詳細規則見 [L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md](./L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md) Section 3.4。

### 9.6 Pre-Compaction Memory Flush

在 transcript compaction 前，系統應允許先做一次 memory flush。

目的：

- 避免重要偏好、近期決策、或新出現的負面記憶在 compaction 中遺失
- 讓 durable memory 比 transcript summary 更可重用

---

## 10. 與前面 specs 的對齊

### 對 L2

memory 建立在 canonical objects 之上，不取代 canonical objects。

### 對 L3.2

recommendation 主要讀：

- `PreferenceProfileSummary`
- `GoldenOrderSummary`
- location / time patterns

### 對 L3.3A

calibration 主要讀：

- `IntakeCompletenessSummary`
- `AdherenceSummary`
- `CalibrationHistorySummary`

### 對 L3.4

rescue 主要讀：

- `RescueHistorySummary`
- `AdherenceSummary`

---

## 11. 測試情境

後續至少應覆蓋：

- 新 intake 歷史能更新 preference pattern
- confirmed dislike 可壓過一般 pattern
- 長期不再出現的偏好應衰減
- rescue repeated failure 會形成 rescue history signal
- ignored proactive 不只存在 trigger table，也能形成 suppression memory

---

## 12. v1 Default Decisions

> **詳細的閾值和決策**：請參閱 [L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md](./L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md) Section 7。

1. confirmed memory：
   - 需滿足「使用者明確口頭確認」或「高一致性行為重複出現」
   - 若無明確確認，至少需 `3` 次一致觀察才可升為 confirmed memory
   - **重要**：Pattern → Confirmed 只能由使用者確認觸發，LLM 不能自己完成升級

2. preference aging：
   - pattern memory 預設使用 `7` 天 / `21` 筆 intake 的滾動窗口做 consolidation
   - 超過 `30` 天未再出現的 pattern 應顯著降權
   - 60 天無新觀察 → 移至 archive

3. suppression memory expiry：
   - 一般 suppression 預設 `14` 天後重新評估
   - confirmed negative preference 不自動 expiry，除非被當下口頭聲明或後續穩定行為覆寫

4. golden orders：
   - **重要**：Golden Order 是 materialized view，不是 promotion 結果
   - 30 天內同一 store + bundle 出現 ≥ 3 次
   - 最近 60 天仍有新觀察（保持 freshness）
   - 不需要「接受推薦並實際消費」作為必要條件

5. L2b semantic pattern extraction 觸發門檻：
   - 累積 `21` 筆新 committed MealItem 且距離上次 extraction 超過 `7` 天，兩個條件都要滿足
   - confidence < `0.5` 的 pattern 不寫入 L2b
   - 同一 `content_hash` 的 pattern 再次出現時更新 `reinforcement_count`，不重複建立

6. L2b semantic pattern → confirmed memory 升級門檻：
   - **已更新**：只能由以下兩條合法路徑觸發：
     - 路徑 1：系統建議 + 使用者明確確認
     - 路徑 2：使用者口頭確認
   - LLM 可以提議升級，但不能自己完成升級

7. Temporary Preference：
   - 新增記憶類型，適用於「不是一次性，但也不是長期」的偏好
   - 預設最大有效天數：14 天
   - 需帶 valid_until 或 expires_in_days

8. Demotion 規則：
   - Pattern：30 天無新觀察 → 降權，60 天 → archive
   - Golden Order：60 天無重複 → inactive，90 天 → archive
   - Behavior-upgraded Confirmed：30 天無相關行為 → needs_validation，60 天 → 降級
   - Confirmed Negative（user_verbal）：不自動 demote

9. NightlyInsight（v1 先不做）：
   - v1 不實作 NightlyInsight
   - L2b semantic extraction 已覆蓋基本的趨勢判斷需求
   - NightlyInsight 等 2.7 memory deepening 有足夠資料後再加

10. Entity Normalization：
    - Golden Order 建立時需進行實體正規化
    - 先嘗試 deterministic 匹配（alias table），失敗則用 LLM fallback
    - 詳細規則見 L4D Section 5

---

## 13. V1 Memory Substrate And Reference Adoption

本產品的 long-term memory 不採用單一外部 framework 作為 canonical runtime。Hermes、OpenClaw、Mem0、Hindsight、Graphiti、Letta、memU，以及本地 reference corpus `C:\Users\User\Desktop\agent runtime\memory`，只能作為機制參考，不是產品 truth owner、runtime dependency、或自動 activation 授權。

V1 memory substrate 應採最小可審計形狀：

| Surface | 角色 | 內容 | 不是什麼 |
|---|---|---|---|
| `user.md` | human-readable user profile | 使用者如何使用 app、溝通風格、主動訊息偏好、穩定飲食偏好摘要 | raw transcript、MealThread truth、FoodDB truth |
| `memory.md` | human-readable promoted memory summary | 已確認或通過 promotion gate 的產品記憶，如穩定禁忌、常用餐序、救援模式 | 未審核候選、一次性偏好、推測性 reasoning |
| `sources.jsonl` / `source.md` | provenance and audit surface | 每條記憶的 source refs、scope、confidence、created/updated、validity window、supersession chain | 可直接注入 prompt 的長篇原文 |
| `daily/YYYY-MM-DD.md` | short-term evidence summary | 當日 session summary、候選線索、短期觀察 | durable memory、confirmed preference |
| `review.md` | promotion/rejection queue | stale、contradiction、delete、correction、promotion review items | 自動通過的 approval surface |
| `conversation_archive` | recall source | 對話留存與 searchable summaries | long-term memory 本身 |

Current memory plan:

- Runtime truth is `MemoryRecordStore`.
- Required human-readable surfaces are `user.md`, `review.md`, and `sources.jsonl` / `source.md`.
- `memory.md` is optional/reporting and may summarize promoted memory, but it is not the primary runtime truth.
- `sources.jsonl` stores provenance and bounded source refs; it is not a raw transcript dump and is not directly injected into Manager context.

Reference adoption rule:

- 採用 Hermes / Letta 的 bounded, human-readable memory surfaces：`user.md` 類 user profile、core memory blocks、read-only block guard。
- 採用 memU 的 scope-first record discipline：`user_id`、`workspace_id`、`project_id`、`surface`、`session_id/run_id` 必須在 record 層存在，不可靠 LLM 推斷。
- 採用 Hindsight 的 retain / recall / reflect 語義，但 retain 只建立 candidate，reflect 只能輔助判斷，不能完成 promotion。
- 採用 Graphiti 的 temporal provenance 壓力：memory 應能表示 validity window、superseded facts、source episode refs。
- 採用 Mem0 / OpenClaw 的 tool vocabulary：search、get、add/propose、update/review、delete/forget，但產品實作必須套用本 spec 的 promotion guardrails。
- 採用 OpenClaw 的 daily notes、review lane、backfill 概念，但不直接採用 auto flush 或 dreaming 來寫 durable product memory。

Explicit non-adoption:

- 不在 V1 直接啟動外部 memory framework server。
- 不因 reference 支援 graph/vector/provider plugin，就引入 Neo4j/Falkor/Kuzu、provider matrix、或 generic memory daemon。
- 不允許 raw conversation 自動成為 durable memory。
- 不允許 agent tool call 直接覆蓋 MealThread、FoodDB、BodyBudget、ledger、或 proposal canonical truth。

Branch boundary:

- 在 `codex/advanced-product-lab` 內，memory substrate、tool calls、retrieval、context injection、recommendation/rescue/proactive 使用可以完整啟用，以完成產品閉環和 E2E。
- 合回 main/self-use V1 時，仍需 activation wall；lab-enabled evidence 不能等同 mainline runtime activation。
