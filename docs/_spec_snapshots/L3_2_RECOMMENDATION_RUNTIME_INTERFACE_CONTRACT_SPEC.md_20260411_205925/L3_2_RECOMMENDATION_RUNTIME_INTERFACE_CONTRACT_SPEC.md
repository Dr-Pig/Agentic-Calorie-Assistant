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

正式 recommendation flow 的 canonical default 應採 3-node graph：

1. `recommendation_context`
2. `candidate_retrieval_filtering_and_ranking`
3. `recommendation_response`

補充規則：

- `candidate retrieval / availability filtering / hard constraint filtering` 應優先 deterministic-first
- 若 candidate pool 已由 deterministic retrieval 組好，可 collapse 成 2-node graph：
  1. `ranking_and_selection`
  2. `recommendation_response`
- chat surface 通常需要 response node；UI / API surface 可直接輸出 structured ranking result
- cross-domain 原則見 [`L6E LLM Pass Design Policy Spec`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md)

expanded mode 啟用條件至少包括：

- candidate pool 為零，需要 LLM 生成 fallback candidates
- candidate generation 本身需要獨立的 LLM synthesis，而不能由 deterministic retrieval 組成

expanded mode 可保留 4-pass decomposition：

1. `recommendation_context_pass`
2. `candidate_generation_pass`
3. `ranking_and_selection_pass`
4. `recommendation_response_pass`

若後續需要與 intake 共用統一 runtime 命名，可映射成：

- context
- candidate / decision
- ranking / resolution
- response

expanded mode 下，只有實際為 LLM-backed 的 named pass 才需要 logical model role 對應：

- `recommendation_context_pass` -> `fast_router_model`
- `candidate_generation_pass` -> `fast_router_model`（僅當 candidate generation 不是 deterministic retrieval/filtering）
- `ranking_and_selection_pass` -> `strict_reasoner_model`
- `recommendation_response_pass` -> `response_writer_model`

---

## 5. Pass 1: `recommendation_context_pass`

### 5.1 目標

決定現在為什麼要推薦，以及推薦必須遵守哪些上下文約束。

### 5.2 責任

- `decision_mode: hybrid`
- `decision_reason: recommendation goal 與 soft preference 解讀需要語義判斷，但 hard constraints 應保持 deterministic-first`

- 判斷 recommendation 是主動還是被動觸發
- 組合 recommendation 所需 context
- 提取 hard constraints 與 soft preferences
- 決定 recommendation mode

### 5.3 可讀

- `CurrentBudgetView`
- `ActiveBodyPlanView`
- `RecentCommittedMealsView`
- `OpenProposalsView`
- `ProactiveStatusView`
- `PreferenceProfileSummary`
- raw user ask（若由 chat 觸發）
- optional `location_context`

### 5.4 必須輸出

- `recommendation_goal`
- `hard_constraints`
- `soft_preferences`
- `context_window_summary`
- `recommendation_mode`
- `budget_posture`
- `preference_profile_ref`
- `location_posture`

### 5.5 hard constraints 範例

- 剩餘預算上限
- rescue 狀態下的短期扣減
- calibration 後的策略限制
- 已接受 proposal 的短期行為限制

### 5.6 soft preferences 範例

- 愛喝飲料
- 偏飯類 / 麵類
- 常見 `cuisine_family`
- 偏高蛋白
- 偏特定店家 / 鏈店
- 某些時段常選某類食物
- 某些地點常吃某類餐

### 5.7 不可做的事

- 不產生最終候選清單
- 不建立 proposal
- 不建立 intake state

---

## 6. Pass 2: `candidate_generation_pass`

### 6.1 目標

產生可排序的 recommendation candidate set。

### 6.2 責任

- `decision_mode: deterministic`
- `decision_reason: candidate pool 的主體應來自 retrieval、availability、source filtering，而不是自由生成`

- 從可用來源抽取 candidate
- 去掉明顯不合法候選
- 將候選正規化成統一 recommendation item 結構

### 6.3 候選來源優先順序

正式建議固定如下：

1. `historical preference matches`
2. `context-valid nearby candidates`
3. `golden orders`
4. `safe fallback candidates`
5. `generic healthy suggestions`

#### 定義

`historical preference matches`
- 根據 `MealItem` 歷史、店家歷史、時段偏好、location pattern 產生的高相容候選

`context-valid nearby candidates`
- 在當前時間與位置可取得、且符合 hard constraints 的附近店家 / 餐點

`golden orders`
- `favorite stores + near search + current calorie / protein gap fit`
- 在 recommendation runtime 中，`golden orders` 可被視為高信度的 item bundle 記憶；例如特定店家 + 特定餐點或飲料組合，可在相符時段與情境下被明顯提權

`safe fallback candidates`
- 偏好資料不足或 location 不可用時的保底候選

`generic healthy suggestions`
- generic 健康選項，只能作為最後 fallback，不應成為前排

### 6.7 Cold-Start 執行模式

若 `PreferenceProfileSummary` 為 empty / sparse：

- `candidate generation` 應優先退回 safe defaults、available menu candidates、generic fallback，不得因記憶不足而 fail closed
- `ranking_and_selection_pass` 可降級為 deterministic sort，例如依與 budget 的 kcal distance、protein posture、availability 做排序
- 此模式下 graph 可簡化為 `context + filter -> response`
- LLM 若仍介入，優先用在 response phrasing，而不是假造偏好推理

### 6.4 可讀

- `recommendation_context_result`
- favorite stores / golden orders
- store / menu retrieval results
- known safe defaults
- optional location-aware candidates

### 6.5 必須輸出

- `candidate_items[]`
- `candidate_source_summary`
- `candidate_filter_reasons`
- `candidate_count`
- `coverage_gaps`

### 6.6 `RecommendationCandidate` 最小欄位

- `candidate_id`
- `title`
- `source_type`
- `store_name`
- `estimated_kcal_range`
- `protein_posture`
- `staple_type`
- `item_kind`
- `cuisine_family`
- `confidence`
- `why_it_matches`
- `disqualifier_flags`
- `external_links`

### 6.7 不可做的事

- 不決定最終 top choice
- 不直接對使用者呈現
- 不建立 proposal / intake state

---

## 7. Pass 3: `ranking_and_selection_pass`

### 7.1 目標

根據 hard constraints 與 soft preferences 對候選排序，決定主推與備選。

### 7.2 責任

- `decision_mode: hybrid`
- `decision_reason: 在多個合法 candidate 間做 soft tradeoff ranking 可用 LLM，但 ranking 必須受 budget 與 availability 約束`

- 先做 constraint filtering
- 再做 preference scoring
- 產生 top result 與備選集
- 決定對外呈現密度

### 7.3 可讀

- `recommendation_context_result`
- `candidate_generation_result`
- `PreferenceProfileSummary`
- budget posture
- body-plan posture

### 7.4 必須輸出

- `ranked_candidates[]`
- `top_pick`
- `backup_picks[]`
- `ranking_explanation`
- `presentation_policy`

### 7.5 ranking 規則

先 hard constraints，再 soft preferences。

#### hard constraints

- 明顯超出預算
- 與已接受 rescue 方案衝突
- 與短期 body-plan posture 明顯衝突
- 已知不吃 / 已知拒絕條件

#### soft preferences

- 常見 `item_kind`
- 常見 `staple_type`
- 常見 `cuisine_family`
- 常喝飲料與飲料時段
- 常見店家 / 鏈店
- 時段偏好
- 地點模式
- 過去接受 / 忽略某類推薦的行為訊號

### 7.6 不可做的事

- 不建立 recommendation intent state
- 不直接 commit intake
- 不重寫 hard constraints

---

## 8. Pass 4: `recommendation_response_pass`

### 8.1 目標

把 recommendation 轉成 chat / UI 可消費的呈現格式。

### 8.2 責任

- `decision_mode: llm`
- `decision_reason: 此步驟主要負責 recommendation 的 explanation 與 chat phrasing`

- chat 中輸出少量高信心建議
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
- 上方可顯示主推組
- 下方可顯示附近店家 / 類別切換 / 更多候選

### 8.6 quick actions

允許：

- `換一個`
- `看低熱量`
- `看高蛋白`
- `看附近店家`
- `開啟地圖`
- `幫我記這個`

其中：

- `幫我記這個` 是 explicit intake action
- 一旦使用者點擊，應直接轉進 `L3.1 intake flow`
- 這不是 recommendation intent state
- `幫我記這個` 與 `換一組` 應作為預設 quick actions 存在；具體 action 可依 channel / surface / context 降級或替換

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
