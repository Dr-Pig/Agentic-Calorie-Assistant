# L3.2 Recommendation Runtime / Interface Contract Spec

## 1. 目的

本文件定義 recommendation flow 的 canonical runtime contract。

它要回答：

- recommendation flow 讀哪些 shared objects / views
- recommendation 如何使用 `MealItem` 歷史分類與偏好訊號
- recommendation 如何結合 budget、body plan、time context、location context、store context
- recommendation 如何產生 candidate set、排序、與對外呈現
- recommendation 何時只做建議，何時可直接轉 intake
- recommendation 與 proactive、proposal、chat、UI 的邊界是什麼

本文件刻意不回答：

- prompt wording
- 最終排序模型實作
- store search / map API 細節
- benchmark 與 eval 細節

---

## 2. Recommendation 的定位

### 2.1 不是單純搜尋

recommendation 不是單純的附近店家搜尋，也不是 generic 健康建議。

recommendation 必須結合：

- `CurrentBudgetView`
- `ActiveBodyPlanView`
- 歷史 `MealItem` 偏好訊號
- 當前時間情境
- optional location context
- rescue / calibration 狀態

### 2.2 recommendation 不建立 intent state

正式規則：

- recommendation 被顯示、被點開、被排序，不直接產生 canonical state
- recommendation 不建立 recommendation intent state
- 只有使用者明確表達「我吃這個 / 幫我記這個 / 加到今天」時，才轉進 intake flow

### 2.3 產品目標

recommendation 必須支援：

- chat 中給少量高信心建議
- UI 中給完整候選、篩選器與外部連結
- 對 budget / rescue / calibration 有感知
- 對歷史偏好與時段模式有感知
- 保持低摩擦，不創造中間暫存狀態

---

## 3. 主流程輸入與最終輸出

### 3.1 主流程最小輸入

- `user_id`
- `message_event_id`（若由 chat 觸發）
- `raw_user_input`（若由 chat 觸發）
- `channel`
- `recorded_at`
- `timezone`
- `CurrentBudgetView`
- `ActiveBodyPlanView`
- `RecentCommittedMealsView`
- `OpenProposalsView`
- `ProactiveStatusView`
- `PreferenceProfileSummary`
- recommendation source context
  - favorite stores
  - golden orders
  - safe defaults
  - available store / menu candidates
  - optional location context

### 3.2 主流程最終輸出

- `recommendation_runtime_packet`
- `recommendation_result`
- `hint_packet`
- `action_hints`
- `trace_envelope`

`recommendation_runtime_packet` 的定位：

- canonical path 的 graph-neutral runtime artifact
- 至少包含 context summary、candidate source summary、ranking basis、fallback posture
- expanded mode 下可拆成 `recommendation_context_result`、`candidate_generation_result`、`ranking_result`

`recommendation_result` 的定位：

- canonical path 的最終 recommendation artifact
- chat surface 可包含 `reply_text`
- UI / API surface 可只輸出 structured picks 與 explanation fields

主流程不直接輸出：

- `commit_request`
- `MealThread`
- `LedgerEntry`

`hint_packet` 的定位：

- recommendation flow 交給 intake flow 的非 canonical 線索包
- 可包含 candidate title、store metadata、estimated kcal range、source type、surface context 等
- 幫助 `L3.1 intake flow` 起跑更快，但不直接成為 canonical truth

除非使用者顯式觸發 intake action，才轉入 `L3.1`。

---

## 4. Canonical Runtime Shape

正式 recommendation flow 的 canonical default 應採 **5-node graph**：

1. `recommendation_context`（LLM）
2. `candidate_spec_generation`（LLM）
3. `candidate_retrieval`（Deterministic）
4. `ranking_and_synthesis`（LLM）
5. `recommendation_response`（LLM）

**設計原則：**

- Node 1：LLM 理解使用者當下的意圖和情境
- Node 2：LLM 把「自然語言偏好」轉成可檢索的 candidate blueprint（candidate spec）。這一層是關鍵——沒有它，Node 3 的 deterministic retrieval 只是 dumb SQL，候選集合從一開始就錯了
- Node 3：Deterministic retrieval，用 Node 2 的 candidate spec 去撈候選。這樣 deterministic retrieval 才不是機械查表
- Node 4：LLM 讀取候選 + 完整情境，真正判斷「哪個最適合現在、為什麼」
- Node 5：LLM 對話呈現，non-mutating

**Logical model roles：**

- Node 1 `recommendation_context` → `fast_router_model`
- Node 2 `candidate_spec_generation` → `fast_router_model`
- Node 3 `candidate_retrieval` → deterministic（無 LLM）
- Node 4 `ranking_and_synthesis` → `strict_reasoner_model`
- Node 5 `recommendation_response` → `response_writer_model`

### 4.1 Canonical Path Walkthrough

1. `recommendation_context`（LLM）
   - 理解使用者當下說的話：「輕的」「不要太油」「今天超標了」「想吃熱的」
   - 這些在此情境下代表什麼
   - 輸出：recommendation goal、hard constraints、soft preferences、recommendation mode

2. `candidate_spec_generation`（LLM）
   - 不直接產生最終答案
   - 把「自然語言偏好」轉成可檢索的 candidate blueprint，例如：
     - desired meal style
     - acceptable cuisine families
     - excluded item patterns
     - soft target kcal band
     - convenience-store vs restaurant posture
     - whether swaps are allowed
   - 輸出：`candidate_spec`（結構化的檢索藍圖）

3. `candidate_retrieval`（Deterministic）
   - 用 Node 2 的 `candidate_spec` 去撈候選
   - 過濾明顯不合法的選項（超出預算、已知不吃）
   - 輸出：candidate pool（未排序）

4. `ranking_and_synthesis`（LLM）
   - 讀取 candidate pool + 完整情境（今天已吃了什麼、偏好、rescue 狀態）
   - 真正判斷「哪個最適合現在、為什麼」
   - 輸出：top pick、backup picks、個人化推薦理由

5. `recommendation_response`（LLM）
   - chat-first 呈現
   - non-mutating：不建立 intent state
   - 只允許 handoff intake（使用者點「幫我記這個」才轉 L3.1）

---

## 5. Node 1: `recommendation_context`

### 5.1 目標

LLM 理解使用者當下的意圖、情境、限制，決定推薦的目標和約束。

### 5.2 責任

`decision_mode: llm`
`decision_reason: recommendation goal 與 soft preference 解讀是語義理解，必須由 LLM 執行。hard constraints 的數值來自 deterministic read，但「這些 constraints 對這個人現在意味著什麼」是 LLM 的工作。`
`logical_model_role: fast_router_model`

- 理解使用者當下說的話（「我想吃點輕的」「有什麼推薦」「我在信義區」）
- 讀取完整情境：剩餘預算、今天已吃什麼、偏好、時段、位置、rescue 狀態
- 提取 hard constraints 與 soft preferences
- 決定 recommendation mode（一般推薦 / menu scan / swap suggestion / pre-meal planning）

### 5.3 可讀

- `CurrentBudgetView`
- `ActiveBodyPlanView`
- `RecentCommittedMealsView`
- `OpenProposalsView`
- `ProactiveStatusView`
- `PreferenceProfileSummary`
- raw user ask（若由 chat 觸發）
- optional `location_context`
- optional `menu_scan_context`（若使用者上傳菜單）

### 5.4 必須輸出

- `recommendation_goal`
- `hard_constraints`
- `soft_preferences`
- `context_window_summary`
- `recommendation_mode`：`general` / `menu_scan` / `swap_suggestion` / `pre_meal_planning`
- `budget_posture`
- `preference_profile_ref`
- `location_posture`

### 5.5 不可做的事

- 不產生候選清單
- 不建立 proposal
- 不建立 intake state

---

## 5A. Node 2: `candidate_spec_generation`

### 5A.1 目標

LLM 把「自然語言偏好」轉成可檢索的 candidate blueprint（candidate spec）。

這一層是 recommendation flow 的關鍵橋樑：沒有它，Node 3 的 deterministic retrieval 只是 dumb SQL，候選集合從一開始就錯了。

### 5A.2 責任

`decision_mode: llm`
`decision_reason: 把自然語言偏好（「輕的」「不要太油」「想吃熱的」）轉成結構化的可檢索 spec，需要語義理解。`
`logical_model_role: fast_router_model`

- 讀取 Node 1 的 recommendation_context_result
- 把 soft preferences 轉成結構化的 candidate spec
- 決定 retrieval 的方向和約束

### 5A.3 可讀

- `recommendation_context_result`
- `PreferenceProfileSummary`
- `RecentCommittedMealsView`（今天已吃了什麼，避免重複）

### 5A.4 必須輸出

`candidate_spec`，包含：

- `desired_meal_style`：例如 `light` / `filling` / `hot` / `cold`
- `acceptable_cuisine_families[]`：例如 `[taiwanese, japanese]`
- `excluded_item_patterns[]`：例如 `[fried, sugary_drinks]`
- `soft_target_kcal_band`：例如 `{min: 400, max: 650}`
- `venue_posture`：`convenience_store` / `restaurant` / `any`
- `swaps_allowed`：boolean（是否允許替換建議）
- `priority_signals[]`：例如 `[high_protein, avoid_repeat_from_today]`

### 5A.5 不可做的事

- 不直接產生候選清單
- 不做 retrieval
- 不建立 proposal / intake state

---

## 6. Node 3: `candidate_retrieval`

### 6.1 目標

用 Node 2 的 `candidate_spec` 去撈候選，輸出未排序的 candidate pool。

### 6.2 責任

`decision_mode: deterministic`
`decision_reason: 候選的撈取和 hard constraint 過濾是機械的查詢。但因為有 Node 2 的 candidate_spec 作為輸入，這個 deterministic retrieval 才不是 dumb SQL——它是在執行 LLM 語義化後的檢索藍圖。`

- 從可用來源撈出候選
- 過濾明顯不合法的選項（超出預算、已知不吃、不可取得）
- 正規化成統一 candidate 結構
- 輸出 candidate pool（不排序）

### 6.3 候選來源優先順序

1. `historical preference matches`（來自 `PreferenceProfileSummary`）
2. `context-valid nearby candidates`（來自 location API，若可用）
3. `golden orders`（來自 memory）
4. `menu_scan_items`（若 `recommendation_mode = menu_scan`）
5. `safe fallback candidates`
6. `generic healthy suggestions`（最後 fallback）

### 6.4 可讀

- `recommendation_context_result`
- `candidate_spec`（來自 Node 2）
- `PreferenceProfileSummary`
- store / menu retrieval results
- location-aware candidates（若可用）
- `menu_scan_context`（若 menu scan mode）

### 6.5 必須輸出

- `candidate_items[]`（未排序）
- `candidate_source_summary`
- `candidate_count`
- `coverage_gaps`（若某些來源無法取得）

### 6.6 Cold-Start 規則

若 `PreferenceProfileSummary` 為 empty / sparse：

- 退回 safe fallback candidates + generic healthy suggestions
- 不因記憶不足而 fail closed
- cold-start 時不得假造偏好推理；缺乏個人偏好時應退回 safe fallback candidates 與 generic healthy suggestions

### 6.7 不可做的事

- 不排序候選
- 不決定 top choice
- 不建立 proposal / intake state

---

## 7. Node 4: `ranking_and_synthesis`

### 7.1 目標

LLM 讀取候選 + 完整情境，真正理解「這個人現在最適合吃什麼」，生成排序和推薦理由。

這是 recommendation flow 的 agentic 核心。

### 7.2 責任

`decision_mode: llm`
`decision_reason: 在多個合法候選中做 soft tradeoff ranking 需要真正理解使用者情境——今天已吃了什麼、偏好是什麼、現在的心情和需求是什麼。這不是機械排序，而是語義理解後的選擇。`
`logical_model_role: strict_reasoner_model`

- 讀取 candidate pool + 完整情境
- 理解「這個人現在最適合吃什麼」
- 生成排序：top pick + backup picks
- 生成個人化推薦理由（不是模板，是真正針對這個人這個時刻的說明）
- 決定對外呈現密度

### 7.3 可讀

- `recommendation_context_result`
- `candidate_retrieval_result`
- `PreferenceProfileSummary`
- `RecentCommittedMealsView`（今天已吃了什麼）
- `OpenProposalsView`（rescue 狀態）
- budget posture
- body-plan posture

### 7.4 必須輸出

- `ranked_candidates[]`
- `top_pick`
- `backup_picks[]`
- `ranking_explanation`（個人化，不是模板）
- `presentation_policy`

### 7.5 ranking 規則

先 hard constraints（deterministic gate），再 soft preferences（LLM synthesis）。

**Hard constraints（deterministic gate，在 Node 3 已過濾，Node 4 再確認）：**
- 明顯超出預算
- 與已接受 rescue 方案衝突
- 已知不吃 / 已知拒絕條件

**Soft preferences（LLM synthesis）：**
- 今天已吃了什麼（避免重複、補充不足的營養）
- 常見 `item_kind` / `staple_type` / `cuisine_family`
- 時段偏好
- 地點模式
- 過去接受 / 忽略某類推薦的行為訊號
- 當下說的話（「我想吃點輕的」「我想吃飽一點」）

### 7.6 不可做的事

- 不建立 recommendation intent state
- 不直接 commit intake
- 不重寫 hard constraints

---

## 8. Node 5: `recommendation_response`

### 8.1 目標

把 Node 4 的結果轉成 chat / UI 可消費的呈現格式。

### 8.2 責任

`decision_mode: llm`
`decision_reason: 自然語言生成`
`logical_model_role: response_writer_model`

- chat 中輸出少量高信心建議（1 主推 + 1-2 備選）
- UI 中輸出完整候選與篩選資訊
- 產生 quick actions
- 決定是否附帶 actionable nudges

### 8.3 可讀

- `ranking_result`
- `recommendation_context_result`
- channel / surface context

### 8.4 必須輸出

- `reply_text`
- `ui_cards`
- `quick_actions`
- `asked_follow_up`
- `ui_hints`
- `hint_packet`

### 8.5 呈現規則

- chat：預設 1 個主推 + 1-2 個備選
- UI：可顯示更多候選與篩選器

### 8.6 quick actions

允許：

- `換一個`
- `看低熱量`
- `看高蛋白`
- `看附近店家`
- `開啟地圖`
- `幫我記這個`

其中 `幫我記這個` 是 explicit intake action，點擊後直接轉進 `L3.1 intake flow`。

### 8.7 不可做的事

- 不直接建立 canonical intake state
- 不建立 recommendation intent state
- 不直接改 budget / body plan

---

## 9. PreferenceProfileSummary Contract

### 9.1 定位

`PreferenceProfileSummary` 是 recommendation flow 可讀的偏好摘要。

它不是 raw memory，也不是全量歷史資料，而是由歷史 intake 與行為訊號聚合出的 summary view。

### 9.2 最小欄位

- 常見 `item_kind` 分布
- 常見 `staple_type` 分布
- 常見 `cuisine_family`
- 常見 `store / chain`
- `drink_preference_strength`
- `protein_posture_preference`
- `time_of_day_patterns`
- `location_patterns`
- `accepted_recommendation_patterns`
- `ignored_recommendation_patterns`

### 9.3 與記憶層的關係

這個 summary 應對齊未來的三層記憶機制：

- L1 / typed history：實際吃過什麼、做過什麼操作
- L2 / pattern layer：從歷史中推得的偏好 pattern
- L3 / confirmed preference layer：已被口頭確認或高信度確認的偏好

recommendation runtime 在讀取這份 summary 時，應假設偏好具有時間敏感性。
- 新近行為應可對舊偏好形成提權或衰減
- 很久以前的偏好不應被視為永久真理
- 具體 aging / decay 公式留到 `L4 Memory / Retrieval / Context Spec`

本文件只定義 recommendation 可以讀的 summary contract，不定義它的實作寫入機制；那部分留給 `L4 Memory / Retrieval / Context Spec`。

### 9.4 Cold-start / Sparse-memory Rule

`PreferenceProfileSummary` 對新使用者或低歷史量使用者可以是 empty 或 sparse。

正式規則：

- empty / sparse preference summary 仍是合法輸入
- recommendation 必須降級到 `safe fallback candidates`、`generic healthy suggestions`、以及其他不依賴記憶聚合的來源，而不是報錯或回傳空結果
- memory awareness 會提升排序品質，但 recommendation 的基本可用性不得綁死在已完成的 memory consolidation 上

---

## 10. Recommendation 與 Intake 的邊界

### 10.1 recommendation 預設不產生 state

以下行為都不建立 canonical state：

- 看推薦
- 排序推薦
- 切換篩選器
- 換一批候選

### 10.2 何時轉 intake

只有使用者明確表達：

- `我吃這個`
- `幫我記這個`
- `加到今天`
- `就記這餐`

才建立真正的 intake request，轉入 `L3.1 intake flow`。

### 10.3 轉 intake 時帶過去的資訊

- selected candidate summary
- source metadata
- estimated kcal hint
- store / item title
- current surface channel

這些只是 intake 的輸入線索，不直接成為 canonical truth。

---

## 11. Recommendation 與 Proposal 的邊界

### 11.1 何時只是 recommendation

- 一般下一餐建議
- 同預算內候選
- 單次高蛋白 / 低熱量選項

### 11.2 何時升格為 proposal

- rescue 狀態下的計畫性建議
- calibration 後的短期飲食策略調整
- 需要被確認並持續影響之後行為的建議

也就是：

- recommendation 是候選
- proposal 是需要被確認的未來變更

---

## 12. Location Context Contract

### 12.1 是否納入 contract

正式納入，但作為 optional input，不要求第一版必定實作。

### 12.2 `location_context` 最小欄位

- `availability`
- `lat`
- `lng`
- `accuracy`
- `captured_at`
- `location_label`
- `location_cluster_id`（可選）

### 12.3 使用方式

- 若 location 可用，啟用 `context-valid nearby candidates`
- 若 location 不可用，退回 `historical preference matches + golden orders + fallback`
- location 只是候選來源放大器，不應凌駕 budget / body-plan constraints
- `location unavailable` 應被視為合法 context posture，而不是錯誤；此時 recommendation 應優先切換到 `known chain mode`、`takeout-safe mode` 或其他非 nearby 依賴的 fallback posture

### 12.4 外部連結

UI 可允許 recommendation card 附：

- `google_maps_link`
- `place_detail_link`

但這些屬於呈現層能力，不是 canonical state。

---

## 13. Source Extensions

### 13.1 第一版主來源

- favorite stores
- nearby places
- golden orders
- safe defaults
- known recurring items

### 13.2 recipe source

recipe recommendation 先不進第一版主流程，但保留 extension point。

正式規則：

- `recipe_candidates` 可作未來 recommendation source type
- v1 主流程不依賴 recipes
- 若未來加入 recipes，應作為新的 candidate source，而不是重寫現有 recommendation contract

### 13.3 delivery platform

Foodpanda / 外送平台整合不納入 v1 contract。

---

## 13A. Menu Scan Mode（外食菜單掃描）

### 13A.1 定位

Menu scan 是 recommendation flow 的一個 input mode，不是 intake flow。

核心差異：
- intake flow：記錄**已吃**的食物
- menu scan：在**吃之前**根據菜單幫使用者決定點什麼

### 13A.2 觸發方式

- 使用者在 chat 上傳菜單照片，並說「我在 XX 餐廳，有什麼可以點？」
- 使用者在 chat 說「我等一下要去 XX，幫我看看菜單」並附上照片

### 13A.3 Flow

1. `vision_parser_model` 解析菜單照片，提取菜單項目清單（item name + 估算 kcal range）
2. 進入 recommendation flow 的 `candidate_retrieval_filtering_and_ranking` node
3. 以菜單項目作為 candidate pool，依剩餘預算 + 偏好排序
4. 輸出推薦點什麼（例如「建議點雞腿飯約 550 kcal，符合你的剩餘預算 600 kcal」）

### 13A.4 規則

- 菜單解析結果是 recommendation 的 candidate source，不直接成為 canonical intake state
- 使用者說「就點這個」後，才轉入 intake flow
- 若菜單照片無法解析，系統應說明並引導使用者手動描述
- `menu_scan_context` 作為 `recommendation_context_result` 的 optional 欄位

### 13A.5 `MenuScanContext` 最小欄位

- `scan_source`: `photo` / `text_description`
- `restaurant_name`（若可識別）
- `parsed_items[]`：每項包含 `item_name`、`estimated_kcal_range`、`confidence`
- `parse_confidence`：整體解析信心
- `unparsed_items[]`：無法識別的項目

---

## 13B. Swap Suggestion Mode（食物替換建議）

### 13B.1 定位

Swap suggestion 是 recommendation 的一個 sub-mode，觸發條件是使用者剛記錄了高熱量食物，系統主動提出具體替換選項。

它不是「下一餐吃什麼」，而是「你剛才吃的東西，下次可以換成什麼」。

### 13B.2 觸發條件

- 使用者剛 commit 一個 `MealItem`，其 `estimated_kcal` 明顯高於同類食物的平均值
- 或使用者剛超標，系統在 intake reply 後（獨立訊息）提出替換建議

### 13B.3 規則

- swap suggestion 是獨立訊息，不夾帶在 intake reply 裡
- 只在使用者有歷史記錄（知道他常吃什麼）時才提出，cold-start 使用者不觸發
- 建議應具體可執行（例如「全糖珍奶改半糖每次省 100 kcal，一週省 700 kcal」）
- 不建立 proposal state，只是 recommendation 的 informational output
- 使用者可以說「記住這個建議」，系統才寫入 confirmed preference memory

### 13B.4 `SwapSuggestion` 最小欄位

- `original_item_name`
- `original_kcal`
- `suggested_item_name`
- `suggested_kcal`
- `kcal_saving_per_instance`
- `weekly_saving_estimate`（若使用者有固定頻率）
- `suggestion_basis`：`preference_pattern` / `generic_healthier_option`

---

## 13C. Pre-Meal Planning Mode（餐前情境規劃）

### 13C.1 定位

Pre-meal planning 是 recommendation 的 proactive / context-aware variant，觸發條件是使用者說「等一下要去哪裡吃」或「今晚有聚餐」。

### 13C.2 觸發方式

- 使用者說「我等一下要去信義區吃飯」
- 使用者說「今晚有公司聚餐，不知道會吃什麼」
- 使用者說「我要去 XX 餐廳」

### 13C.3 Flow

1. 系統識別 pre-meal planning intent
2. 讀取剩餘預算、偏好、位置（若可用）
3. 若有具體地點：走 menu scan 或 nearby candidate retrieval
4. 若無具體地點（例如聚餐）：走全天熱量分配策略（見 13C.4）
5. 輸出建議

### 13C.4 全天熱量分配策略（聚餐情境）

當使用者說「今晚有聚餐，不知道會吃多少」：

1. 系統計算今日剩餘預算
2. 系統建議白天保留空間（例如「今晚聚餐建議保留 600 kcal，午餐控制在 400 kcal 以內」）
3. 若使用者接受，系統在 chat 說明今日的分配策略
4. 不建立 proposal state（這是 informational recommendation，不是 budget overlay）
5. 若使用者說「幫我設定今晚保留 800 kcal」，才升格為 `planned_event_budget_allocation`（見 L3.4 補充）

### 13C.5 規則

- pre-meal planning 是 recommendation flow，不是 rescue flow
- 不直接改寫 `DayBudgetLedger`，除非使用者明確確認分配策略
- 聚餐後使用者記錄實際吃了什麼，走標準 intake flow

---

## 14. Proactive Recommendation Contract

### 14.1 可觸發條件

- 用餐時段接近且尚未記錄
- rescue 期間需要低損害選擇
- 某時段 historically 有固定行為（如下午茶）
- 某類建議在某時段有高接受率

### 14.2 suppression / cooldown

recommendation proactive 必須受：

- quiet hours
- ignore history
- recent fire count
- user preference suppression
- trigger dedupe

約束。

### 14.3 actionable nudges

允許：

- 低熱量快捷選項
- 高蛋白快捷選項
- 飲料替代選項
- `幫我記這個` 的明確 intake action

仍不建立 recommendation intent state。

### 14.4 proactive recommendation quality

Proactive recommendation uses adaptive intensity instead of a fixed send / no-send policy.

Formal rule:

- `high_quality_context` may send one primary recommendation plus one backup
- `medium_quality_context` should send only a low-friction offer
- `low_quality_context` should skip silently

Hard gates:

- calorie target / budget fit must pass
- confirmed negative preferences must not be violated
- the candidate must be realistically executable as recommended
- quiet hours, cooldown, suppression, and recent-send caps must pass

Quality signals:

- availability or likely availability
- frequent choice / golden order
- meal-time pattern match
- budget fit
- evidence quality
- interaction tolerance

Evidence rule:

- proactive recommendations may use exact or narrow anchored item evidence
- generic category-only suggestions are not proactive recommendations
- if no concrete candidate can pass the calorie and evidence gates, the system should not proactively recommend

Live enrichment rule:

- proactive recommendation should use prepared or cheap-to-verify candidates by default
- Google Places, web search, menu lookup, blog evidence, or photo/menu enrichment should be user-engaged by default
- cache-backed enrichment may be introduced later as a separate capability

---

## 15. Important Types / Interfaces

建議正式化以下 contract types：

- `RecommendationContextResult`
- `RecommendationCandidate`
- `CandidateGenerationResult`
- `RankingResult`
- `RecommendationResponseResult`
- `PreferenceProfileSummary`
- `HintPacket`
- `RecommendationActionHint`

`RecommendationCandidate` 最小欄位：

- `candidate_id`
- `title`
- `source_type`
- `store_name`
- `estimated_kcal_range`
- `item_kind`
- `staple_type`
- `protein_posture`
- `cuisine_family`
- `confidence`
- `why_it_matches`
- `disqualifier_flags`

`HintPacket` 最小欄位：

- `candidate_id`
- `title`
- `store_name`
- `source_type`
- `estimated_kcal_range`
- `estimated_protein_posture`
- `surface_channel`
- `selection_context`
- `retrieval_metadata`
- `external_links`

---

## 16. 與 L0 / L1 / L2 的對齊

### 對 L0

- recommendation 明確依賴 `meal_thread + day_budget_ledger + body_plan`
- recommendation 偏好來源補充為歷史 `MealItem` 分類聚合訊號

### 對 L1

- recommendation flow 不建立 recommendation intent state
- recommendation 可輸出 UI quick actions，但不直接 commit canonical state
- proactive recommendation 受 suppression / cooldown 管控

### 對 L2

- `MealItem` 的粗分類與 optional 細分類直接成為 recommendation 的偏好來源
- `PreferenceProfileSummary` 應作為未來 derived memory view
- location / time pattern 屬於偏好摘要的一部分，而不是新 canonical object

---

## 17. 測試情境

後續實作至少應覆蓋：

- 在同樣 budget 下，偏飯使用者優先看到飯類而非麵類
- 常喝飲料使用者在下午時段看到飲料相關建議
- rescue 狀態下，明顯超出 hard constraints 的候選被過濾
- calibration 後，推薦熱量 posture 跟著調整
- chat 與 UI 對同一批 recommendation 候選呈現不同密度
- recommendation 點選不自動建立 canonical state
- 使用者明確點 `幫我記這個` 後，正確轉入 intake flow
- proactive recommendation respect suppression / cooldown
- `MealItem` 細分類缺失不影響 recommendation 基本可用性
- location 存在時，nearby candidates 進入前排；location 不存在時正常 fallback
- generic healthy suggestion 不應在偏好充分時佔據前排

---

## 18. 實作假設

- recommendation 偏好學習依賴 `MealItem` 歷史分類，不引入 recommendation intent state
- `PreferenceProfileSummary` 現在只定 contract，不定寫入實作
- `location_context` 正式進 contract，但第一版可不實作
- recipe source 只保留 extension point，不進 v1 主流程
- external map links 可進 UI contract，但不進 canonical state
