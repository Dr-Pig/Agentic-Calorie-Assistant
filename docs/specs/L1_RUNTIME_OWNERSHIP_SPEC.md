# L1 Runtime Ownership Spec

## 1. 目的

本文件定義 L0 產品能力層之下的第一層 runtime 規格：共享狀態、layer ownership、合法狀態轉移、commit 邊界，以及 chat / UI / proactive 三條路徑如何匯流到同一組 canonical state。

本文件要回答：

- 哪些共享物件是 runtime 的 canonical objects
- 哪些 layer 可以讀、提案、commit 這些物件
- 哪些狀態轉移可以自動發生
- 哪些狀態轉移必須經過使用者確認
- correction、proposal、proactive、body calibration、budget adjustment 的正式邊界是什麼

本文件刻意不回答：

- 精確 DB schema
- 精確 API wire contract
- prompt wording
- 模型供應商或框架選型
- 精確四層 LLM prompt 細節

---

## 2. 核心原則

### 2.1 `meal_thread` 是第一核心物件

整個產品不是以單次回覆為核心，而是以 `meal_thread` 作為主要狀態單位。

所有 intake、clarification、correction、refinement 都應優先被解讀為對某個 `meal_thread` 的建立、補充、修正或提交。

### 2.2 `default-commit`

只要系統能形成可信的熱量數字，就預設直接提交為正式紀錄。

只有在完全無法形成可信估計時，才停留在 draft / unresolved 狀態。

本規則的目的：

- 降低對話阻力
- 避免「每一餐都先追問」的高摩擦體驗
- 把修正主導權交給使用者

### 2.3 `proposal` 與 committed state 必須分離

任何未來導向的調整，例如：

- 救援方案
- 體態校準後的預算調整
- 主動提醒後的快捷建議

都必須先以 `proposal` 存在，不可直接偷偷改寫 canonical active state。

### 2.4 `last_intent_wins`，但必須保留版本鏈

不論來源是 chat、UI 或 smart chip，只要是合法且通過 guard 的最後一筆操作，就成為新的 canonical version。

但不能覆蓋掉舊版本；必須保留 version chain 與 superseded 關係。

### 2.5 主觀真實優先

當文字描述與照片視覺推論衝突時，優先採信使用者明確表達的主觀敘述，例如：

- 「我只吃半碗」
- 「這個醬我沒有吃」

系統可以保留偏差警示，但不能用視覺推論強行覆蓋使用者明示內容。

### 2.6 不建立 recommendation intent state

現階段不建立「推薦被點選但尚未吃下」的中間狀態，也不建立獨立的 recommendation-linked intent object。

原則如下：

- recommendation acceptance 預設不產生 canonical state
- 只有使用者明確表示「我吃了 / 幫我記這個 / 就記這餐」時，才建立真正的 `meal_thread`
- UI 的推薦卡片預設只做瀏覽與明確記錄，不做中間 intent tracking

本規則的目的：

- 避免多一種半吊子的 planned state
- 避免污染 ledger
- 讓資料模型維持最小必要複雜度

---

## 3. Canonical Runtime Objects

### 3.1 `meal_thread`

定義：

- 一個 `meal_thread` 代表單一餐點事件從首次提及、追問、修正到最終提交的完整生命週期

應承載：

- thread identity
- 原始輸入與後續相關回合
- 最新的 candidate interpretation
- thread 內的多個 food items / meal components
- unresolved slots / pending follow-up
- 已提交的 nutrition snapshot
- correction lineage
- 最近一次對外追問狀態
- 發生時間語意

重點規則：

- `meal_thread` 的粒度是飲食事件，不是訊息，也不是單一食物
- item-level 修正由後續 `MealItem` 層承接
- 允許 provisional understanding
- 允許 thread ambiguity 暫時存在
- committed meal 不可無聲覆寫
- correction 需產生新版本並 supersede 舊版本

### 3.2 `day_budget_ledger`

定義：

- 表示某一天有效熱量預算的帳本物件

應承載：

- base daily budget
- committed meal consumption
- accepted rescue overlays
- accepted calibration-driven adjustments
- effective available budget
- adjustment provenance

重點規則：

- ledger 採多層結構，不是單一數字
- UI 必須能明確區分基準預算、救援扣減、有效預算
- committed meal 影響 consumption layer
- rescue / calibration 影響 overlay 或 active adjustment layer

### 3.3 `body_plan`

定義：

- 表示使用者目前體態目標與校準狀態的 canonical object

應承載：

- raw body observations
- trend interpretation
- active goal policy
- calibration state
- pending calibration proposals

重點規則：

- 體重 observation 可以直接寫入
- 影響預算或目標策略的校準結果不可直接生效
- calibration 預設先形成 proposal，再由使用者確認

### 3.4 `proposal_container`

定義：

- 表示一個待協商提案容器，可包含一個或多個候選方案

應承載：

- proposal type
- source object
- target effect
- candidate options
- presentation policy
- negotiation status
- accepted / rejected option
- commit source
- expiry / invalidation state

重點規則：

- proposal 是未來導向變更的唯一正式入口
- proposal 可由 proactive 預先建立
- proposal 可以被 chat、UI、smart chip 共同查看與確認

### 3.5 `proactive_trigger`

定義：

- 表示系統主動發起互動的原因、條件與節制機制

應承載：

- trigger type
- target object
- eligibility reason
- fired timestamp
- suppression state
- cooldown state
- acknowledgement / dismissal state
- optional linked proposal id

重點規則：

- proactive trigger 與 proposal 是不同物件
- trigger 回答「為什麼現在出手」
- proposal 回答「這次想談什麼方案」

---

## 4. Runtime Layers 與 Ownership

### 4.1 `Interpretation Layer`

責任：

- 判斷使用者輸入是否為 intake、clarification、correction、general chat
- 嘗試連結到既有 `meal_thread`
- 產生 candidate meaning 與 candidate linkage

可以：

- 讀取 `meal_thread`、最近對話、必要的 active views
- 產生 provisional interpretation update

不可以：

- 直接 commit canonical state
- 直接改寫 ledger 或 body plan

### 4.2 `Decision Layer`

責任：

- 決定下一步是直接估、追問、查證、建立 proposal、或進入 rescue / calibration flow

可以：

- 讀取所有 relevant shared objects
- 產生 next action
- 決定是否建立 proposal

不可以：

- 直接 commit meal、budget、body plan

### 4.3 `Resolution Layer`

責任：

- 產生 nutrition resolution
- 產生 proposal option payload
- 產生 correction-ready payload

可以：

- 生成 kcal / macros / component breakdown
- 生成 proposal options
- 生成 `meal_thread` candidate update

補充規則：

- `nutrition_resolution_pass` 可輸出 `MealItem` 粗分類
- `MealItem` 細分類可選，但不應成為 commit blocking 條件

不可以：

- 直接落地重大狀態變更

### 4.4 `Response Layer`

責任：

- 把上游決策轉成對使用者的自然語言、可點擊互動、或可確認 proposal

可以：

- 呈現結果
- 呈現 follow-up
- 呈現 proposal options

不可以：

- 發明未經授權的狀態變更
- 在 response 階段偷偷提交新 state

### 4.5 `Application / Deterministic Layer`

責任：

- 驗證合法轉移
- 做正規化、去重、trace、bookkeeping
- 執行允許的 persistence

可以：

- 驗證 schema
- 驗證 transition legality
- 執行 guard
- 建立 version chain
- 做 ledger arithmetic
- 做 downstream macro derivation 與 derived-view 降級
- 落地 canonical state

不可以：

- 做 open-world semantic reasoning
- 重算 meal boundary
- 偷改工具路由
- 偷改 LLM 語意結論

### 4.6 `Persistence Layer`

責任：

- 儲存 canonical objects 與歷史版本

可以：

- 儲存 active state 與 superseded history

不可以：

- 決定語意或推理結果

### 4.7 `UI Interaction Layer`

責任：

- 呈現共享物件
- 接收顯式確認、拒絕、手動修改

可以：

- 確認 proposal
- 觸發危險修改 guard
- 對 canonical object 發起顯式修正

不可以：

- 產生 chat runtime 看不到的隱藏狀態

### 4.8 `Proactive Scheduler Layer`

責任：

- 決定何時觸發 proactive
- 管理 suppression / cooldown / preference-awareness
- 在合法情況下建立 linked proposal

可以：

- 標記 trigger eligible
- 發起 proactive trigger
- 預先建立 proposal container

不可以：

- 未經確認直接 commit rescue / calibration 這類重大變更

---

## 5. 合法狀態轉移類型

補充概念：

- `MessageEvent` 是 observation source，不是 canonical meal unit
- recommendation 不建立 recommendation intent state
- 只有明確 intake 確認後，才建立真正的 `MealThread`
- 一個被建立的 `MealThread` 之下可包含多個 `MealItem`

### 5.1 `observation_write`

定義：

- 原始觀測資料寫入

例子：

- 使用者送出餐點文字
- 使用者回報體重
- 使用者點下 UI 確認鍵
- 系統記錄 proactive fired time

規則：

- 可直接寫入
- 必須保留來源

### 5.2 `interpretation_update`

定義：

- runtime 對 observation 產生的候選理解

例子：

- 這句話是在補充上一餐
- 這餐目前像是雞腿便當
- 這個體重趨勢暗示 intake bias 漂移

規則：

- 可更新 provisional state
- 不可直接覆蓋 committed truth

### 5.3 `proposal_creation`

定義：

- 產生待協商方案

例子：

- 三天 rescue 計畫
- calibration budget adjustment
- afternoon snack quick-log proposal

規則：

- proposal 可由 runtime 主動建立
- proposal 與 committed state 分離

### 5.4 `commit_transition`

定義：

- 正式改變 canonical active state 的轉移

例子：

- 建立 committed `meal_thread`
- 接受 rescue option
- 接受 calibration option
- 接受 correction version

規則：

- 必須經過合法 commit path
- 必須保留 commit source
- 所有介面共享同一個 commit 結果

### 5.5 `supersession_transition`

定義：

- 新版本取代舊版本，但歷史保留

例子：

- correction 後新 meal version 取代舊 version
- 新 calibration 取代舊 active calibration
- 新 proposal 取代過期 proposal

規則：

- 舊版本不可消失
- 新版本成為 active state

### 5.6 `suppression_update`

定義：

- 更新 proactive 節制狀態

例子：

- 這個使用者在上班時段不想被打擾
- 類似提醒已連續被忽略三次
- 某種推薦類型近期命中率過低

規則：

- 可以由系統自動更新
- 不可影響已提交的核心營養紀錄

---

## 6. 各共享物件的 commit 與 supersession 規則

### 6.1 `meal_thread`

#### 自動 commit 規則

只要能形成可信數字，就直接 commit。

只有在以下情況才不 commit：

- 完全無法形成可信估計
- 無法判斷輸入是否屬於可估餐點

#### correction 規則

- chat 中自然修正直接建立新版本
- UI 小改可直接建立新版本
- UI 大幅修改需先通過 guard，再建立新版本

#### UI guard 規則

典型危險情況：

- kcal 大幅降低到異常值
- macros 與 kcal 明顯不合理
- 變更幅度遠超一般修正範圍

guard 通過後：

- 直接寫成新 canonical version
- 不進 proposal

### 6.2 `day_budget_ledger`

#### ledger layer 規則

至少分為：

- `base_budget_layer`
- `consumption_layer`
- `rescue_overlay_layer`
- `calibration_adjustment_layer`
- `effective_budget_view`

#### commit 規則

- committed meal 直接影響 consumption layer
- rescue / calibration 影響對應的 adjustment layer
- 所有 adjustment 必須可追溯到 accepted proposal 或明確設定變更

### 6.3 `body_plan`

#### observation 規則

- 體重 observation 可直接寫入

#### calibration 規則

- trend 與 calibration 可背景重算
- 影響 plan 的輸出必須先形成 proposal
- proposal 被接受後，才更新 active body-plan state

### 6.4 `proposal_container`

#### 預設型態

proposal 預設支援多方案並列，而不是只有單一 yes/no。

每個 container 可包含：

- 一個主推方案
- 其他 1-2 個候選方案

#### presentation policy

初期預設直接對外呈現多方案。

後續可依使用者偏好收斂成：

- 單一主推方案
- 單一主推加隱藏候選
- 持續多方案顯示

但 runtime 內部仍保留多 option 結構。

### 6.5 `proactive_trigger`

#### trigger 規則

同一條件不可無冷卻重複觸發。

trigger 需納入：

- cooldown
- suppression
- user preference awareness

#### proposal linkage

某些 proactive 可直接連結 proposal，例如：

- 爆卡後的 rescue plan
- 校準後的新 budget 建議
- snack quick-log 快捷項

---

## 7. 跨介面 Commit 模型

### 7.1 合法 commit source

合法來源包括：

- `chat`
- `ui`
- `smart_chip`

### 7.2 同步規則

任一來源一旦成功 commit，必須：

- 只更新一次 canonical state
- 讓所有介面看到同一結果
- 保留 commit source 與 timestamp

### 7.3 跨介面衝突規則

採 `last_intent_wins + version_chain`。

也就是：

- 最後一筆合法且通過 guard 的操作成為 active version
- 較舊版本轉為 superseded
- 系統保留 lineage，不刪歷史

---

## 8. 時間語意與跨午夜規則

### 8.1 `occurred_at` 優先

餐點歸帳與 ledger 分類以 `occurred_at` 為準，而不是以系統接收到訊息的 clock time 為準。

### 8.2 跨午夜補記

若使用者在午夜後補記前一餐：

- 仍應歸入實際發生的日期
- 不得錯算到當前日 ledger

### 8.3 主觀時間優先

若使用者明確表示：

- 「這是昨天晚餐」
- 「剛剛那杯是下午喝的」

runtime 應優先尊重這類主觀發生時間敘述。

---

## 9. Rescue 與 Calibration 的專屬規則

### 9.1 Rescue Proposal

預設支援多方案並列，但要有基本護欄。

基本護欄至少包含：

- 不可無限期往後攤平
- 每日最大扣減量要有限制
- 可調整天數要有限制

### 9.2 Rescue Failure Escalation

若救援方案連續多日失敗，不應無限延長同類補償方案。

應升級為：

- 重新評估目標速度
- 重新評估預算壓力
- 提出新的目標 / 節奏重設 proposal

### 9.3 Calibration Proposal

體態校準的預設呈現是多方案比較，例如：

- 保守方案
- 中性方案
- 積極方案

但 presentation policy 可依使用者偏好收斂。

---

## 10. Minimum Runtime Views

後續 L2 / L3 至少應建立以下 runtime views：

- `active_meal_view`
- `recent_committed_meals_view`
- `current_budget_view`
- `active_body_plan_view`
- `open_proposals_view`
- `proactive_status_view`

每個 view 在後續 spec 都必須補齊：

- source object
- freshness requirement
- read-only / mutation-capable 性質
- 可消費 layer

---

## 11. Runtime 合法輸出類型

後續 runtime layer 的輸出應統一落在以下類別中：

- `observation_write`
- `provisional_state_update`
- `proposal_draft`
- `commit_request`
- `user_visible_response`
- `suppression_update`

這樣後續每個 pass 只要再定義：

- 可以讀哪些 views
- 可以輸出哪些 output classes

ownership 就能維持清楚。

---

## 12. 與後續規格的邊界

### 本文件已決定

- canonical shared objects
- layer ownership 原則
- default-commit
- version chain / last-intent-wins
- layered ledger
- calibration 必須 proposal-first
- proactive 可 proposal-first
- recommendation 不建立 intent state
- cross-surface commit 規則
- occurred_at 時間歸帳原則

### 本文件留給後續規格

- 精確資料 schema
- 每個 object 的欄位級 contract
- LLM pass 與 object 的細粒度 handoff contract
- prompt / tool / search 細節
- framework fit 與 model allocation 的最終方案

---

## 13. 實作前提假設

- 目前產品仍以 chat-first 為主
- UI 是 dashboard、history、confirm surface，不是主要 reasoning surface
- `meal_thread` 是第一級 canonical object
- committed meal 與 proposal 必須清楚分離
- 使用者偏好記憶會影響 proactive 的呈現與頻率，但不影響 canonical nutrition truth
- 若未來真的需要 recommendation intent tracking，應在更高階產品能力被明確提出後，再新增獨立 state object
