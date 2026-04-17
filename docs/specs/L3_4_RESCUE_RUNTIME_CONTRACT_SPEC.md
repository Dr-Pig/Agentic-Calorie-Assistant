# L3.4 Rescue Runtime Contract Spec

## 1. 目的

這份 spec 定義 rescue flow 的 canonical runtime contract。

它回答：

- 何時應啟動短期 rescue
- rescue 讀哪些 shared objects / views
- rescue 如何形成短期補救方案
- rescue 如何管理 `rescue horizon` 與 `recovery viability`
- 何時 rescue 應停止繼續攤平，並升級到 calibration / `計畫重啟`
- rescue accept 後如何回寫 budget posture、proposal state、與 downstream recommendation

它暫時不回答：

- prompt wording
- 模型選型
- benchmark implementation

---

## 2. 核心定位

rescue 是短期恢復熱量赤字的操作層。

它不是：

- intake truth correction layer
- calibration model layer
- 長期計畫重設 layer

它的核心任務是：

- 在使用者偏離當前 caloric posture 後
- 用低挫敗感的方式提供可執行的短期修復方案
- 讓使用者不要因一次或幾次超標就整體放棄

---

## 3. 核心原則

### 3.1 Rescue is Future-Oriented

rescue 的目標是改善接下來幾天，而不是懲罰已經發生的超標。

### 3.1A 11:00 啟動界線

對會影響未來帳務或 caloric posture 的 rescue：

- 當地時間 11:00 前確認：可從今日午餐開始生效
- 當地時間 11:00 後確認：從明日 00:00 開始生效

但若 rescue family 是 `next_meal_protection`：

- 應保留立即作用於下一餐的例外

### 3.2 Proposal-First

會影響未來 budget posture 的 rescue 都應先以 proposal 呈現，而不是直接改 canonical state。

### 3.3 Short-Horizon First

rescue 預設先處理短期 horizon，不直接跳成長期計畫重設。

### 3.4 Non-Viable Rescue Should Escalate

若短期 rescue 已失去 recovery viability，就不應無限延長攤平；應升級到 calibration / `計畫重啟`。

---

## 4. 主流程輸入與最終輸出

### 4.0 Rescue 與 Intake 的分離規則

**rescue 與 intake 是完全分開的 flow，不可混用。**

正式規則：

- intake reply 完成後，不可在同一則回覆裡附加 rescue 內容
- 不允許在 intake 訊息的第二段夾帶 rescue proposal
- rescue 訊息必須是獨立的一則 chat 訊息
- `rescue_trigger_pass` 不可讀 `current intake event context` 作為觸發依據；rescue trigger 只依賴 ledger state 與 history，不依賴當前 intake 事件

**合法的 rescue 觸發入口只有兩種**：

1. **Proactive**：`ProactiveScheduler` 的 `budget_alert_check` 偵測到 overshoot，建立 rescue proposal 後作為獨立訊息送出
2. **Reactive**：使用者在 chat 中明確詢問補救（例如「我今天超標了怎麼辦」「幫我想想怎麼補救」）

不允許：

- intake reply 裡順手夾帶 rescue
- 系統在使用者沒有問的情況下，在 intake 回覆後自動附加 rescue 建議

### 4.1 主流程最小輸入

- `user_id`
- `message_event_id`（若由 chat 觸發）
- `raw_user_input`（若由 chat 觸發）
- `CurrentBudgetView`
- `RecentCommittedMealsView`
- `ActiveBodyPlanView`
- `OpenProposalsView`
- `ProactiveStatusView`
- recent rescue history summary
- adherence summary
- optional location / schedule context

### 4.2 主流程最終輸出

- `rescue_assessment_packet`
- `rescue_result | no_rescue`
- `rescue_response_result`
- `trace_envelope`

`rescue_assessment_packet` 的定位：

- canonical path 的 combined deterministic assessment artifact
- 至少包含 trigger summary、overshoot math、recovery viability、safety floor input、allowed rescue families
- expanded mode 可拆成 `rescue_trigger_result` 與 `rescue_assessment_result`

`rescue_result` 的定位：

- canonical path 的 rescue option artifact
- 可為 structured rescue proposal，或明確的 `no_rescue` posture

不直接輸出：

- canonical budget rewrite
- active `BodyPlan` rewrite
- direct `LedgerEntry`

除非 proposal 被接受，才由 application layer commit。

---

## 5. Canonical Runtime Shape

`L3.4` 的 canonical default 應採 2-3 node graph：

1. `deterministic_trigger_and_viability_assessment`
2. `rescue_option_shaping`
3. `rescue_response`（若 surface 需要）

補充規則：

- `overshoot math`、`spread horizon limit`、`safety floor`、`recovery_viability`、`cooldown / suppression` 應優先 deterministic-first
- 若 rescue family 已模板化，LLM 可只負責 option phrasing 與 response presentation
- cross-domain 原則見 [`L6E LLM Pass Design Policy Spec`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md)

expanded mode 可保留 4-pass：

1. `rescue_trigger_pass`
2. `rescue_assessment_pass`
3. `rescue_option_pass`
4. `rescue_response_pass`

expanded mode 下，只有 LLM-backed 的 named pass 才需要 logical model role 對應：

- `rescue_trigger_pass` 若只是 overshoot / cooldown / proposal-state trigger 判斷，則保持 deterministic，不映射 LLM role
- `rescue_assessment_pass` 若只是 viability / horizon / safety floor assessment，則保持 deterministic，不映射 LLM role
- `rescue_option_pass` -> `strict_reasoner_model`
- `rescue_response_pass` -> `response_writer_model`
- 下方 `Pass 1-4` 章節屬 expanded decomposition only，不得覆蓋 canonical graph 的優先序

---

## 6. Pass 1: `rescue_trigger_pass`

### 6.1 目標

判斷當前是否存在 rescue-worthy condition。

`decision_mode: deterministic`
`decision_reason: trigger 主要來自 overshoot、history、cooldown、proposal state 等明確條件`

### 6.2 可讀

- `CurrentBudgetView`
- `RecentCommittedMealsView`
- `OpenProposalsView`
- `ProactiveStatusView`
- recent rescue history

（不可讀 `current intake event context`；rescue trigger 不依賴當前 intake 事件，見 Section 4.0）

### 6.3 必須輸出

- `triggered`
- `trigger_type`
- `trigger_severity`
- `trigger_object_ref`
- `overshoot_summary`
- `proactive_eligibility`

### 6.4 典型 trigger

- 當日熱量明顯超出有效預算
- 連續兩到三日接近或超出上限
- 已接受 rescue overlay 但再次 overshoot
- 高風險時段仍未記錄且已知常在該時段失守

### 6.5 不可做的事

- 不直接產生 rescue option
- 不直接 commit overlay

---

## 7. Pass 2: `rescue_assessment_pass`

### 7.1 目標

判斷這次偏離適合用什麼類型的短期修復策略，以及目前 rescue 是否仍具可行性。

`decision_mode: deterministic`
`decision_reason: horizon、viability、safety floor、spread feasibility 應以 rescue math 與 guardrail rule 決定`

### 7.2 可讀

- `rescue_trigger_result`
- `CurrentBudgetView`
- `ActiveBodyPlanView`
- recent rescue history
- adherence summary
- recommendation posture

### 7.3 必須輸出

- `rescue_needed`
- `rescue_horizon`
- `recovery_viability`
- `recommended_rescue_family`
- `escalation_risk`
- `assessment_confidence`

### 7.4 核心概念

#### `rescue_horizon`

本次 rescue 預計的短期修復窗口，例如：

- 1 天
- 3 天
- 5 天

#### `recovery_viability`

代表短期 rescue 現在是否仍合理可執行。

至少支援：

- `high`
- `medium`
- `low`
- `non_viable`

### 7.5 規則

- rescue horizon 不應無限延長
- 若未來幾天需要被壓得過於不合理，`recovery_viability` 應下降
- 若短期修復已失去可行性，應標記 `non_viable`

---

## 8. Pass 3: `rescue_option_pass`

### 8.1 目標

形成 rescue proposal，決定建議的分攤天數與每日回收量。

`decision_mode: deterministic`
`decision_reason: v1 rescue 採單一分攤模型，建議天數與每日回收量由 overshoot math 與 guardrail rule 決定，不需要 LLM 在多個 family 間做選擇`

### 8.2 可讀

- `rescue_assessment_result`
- `CurrentBudgetView`
- `ActiveBodyPlanView`
- recent rescue outcomes

### 8.3 v1 Rescue Model：單一分攤模型

**v1 rescue 採單一分攤模型，不是多 family 選單。**

對使用者的核心體驗是：
- 系統告訴你這次超出多少
- 系統建議用幾天攤回來
- 使用者可調整強度（更短更積極 / 更長更緩和）

差別只剩分幾天、每天回收多少，不是不同策略家族。

#### 建議天數計算規則

1. 計算需回收總量：`overshoot_kcal`
2. 以每日預算的 `15%` 為標準每日回收上限：`daily_cap = base_budget_kcal × 0.15`
3. 計算最少需要幾天：`min_days = ceil(overshoot_kcal / daily_cap)`
4. 建議天數 = `min(min_days, 5)`
5. 若 `min_days > 5`，標記 `recovery_viability: non_viable`，進 `rescue_stop_and_escalate`

#### 強度調整規則

使用者可在 chat 中調整強度，系統重新計算：

- **`更短更積極`**：每日回收上限放寬到 `20%`（`daily_cap = base_budget_kcal × 0.20`），重新計算天數
  - 若連 `20%` 上限都無法在 5 天內完成，明確告知不可行
- **`更長更緩和`**：在最大 5 天內延長天數，降低每日回收量
  - 若已是 5 天，告知已是最緩和版本

#### 保留的特殊 posture

以下情況不走標準分攤模型，而是走對應的特殊 posture：

- **`logging_first_rescue`**：overshoot 規模不清楚（logging 不足）時，先補記再決定是否 rescue
- **`rescue_stop_and_escalate`**：`recovery_viability = non_viable` 時，不繼續攤平，導向 calibration

這兩個 posture 仍保留，但 `same_day_soft_cap` 和 `next_meal_protection` 在 v1 不作為獨立對外 family 呈現。

### 8.4 必須輸出

- `recommended_days`：建議分攤天數
- `daily_kcal_adjustment`：每日回收量（負數）
- `overshoot_kcal`：本次超出量
- `cap_basis`：`base_budget_kcal`
- `cap_mode`：`standard`（15%）或 `aggressive`（20%）
- `recovery_viability`：`viable` / `strained` / `non_viable`
- `special_posture`：`none` / `logging_first` / `escalate`
- `guardrail_notes`

---

## 9. Pass 4: `rescue_response_pass`

### 9.1 目標

把 rescue proposal 轉成可執行、低挫敗感的對外呈現。

`decision_mode: llm`
`decision_reason: 此步驟主要負責 coaching tone、proposal framing、與 user-facing explanation`

### 9.2 必須輸出

- `reply_text`
- `recommended_days`
- `daily_kcal_adjustment`
- `overshoot_kcal`
- `quick_actions`
- `ui_hints`

### 9.3 對外呈現原則

- 只呈現一個建議方案（建議天數 + 每日回收量）
- 不呈現 backup options，不做多策略選單
- 用語應偏未來導向，不責備
- 說明超出多少、建議幾天攤回、每天大約少吃多少

### 9.4 quick actions

v1 標準 quick actions：

- `{ "action_id": "accept_rescue_plan", "label": "接受這個方案" }`
- `{ "action_id": "shorten_rescue_plan", "label": "更短更積極" }`
- `{ "action_id": "extend_rescue_plan", "label": "更長更緩和" }`
- `{ "action_id": "reject_rescue_plan", "label": "不要這個方案" }`
- `{ "action_id": "explain_rescue_plan", "label": "為什麼這樣建議" }`

若 `special_posture = logging_first`，改為：

- `{ "action_id": "log_meal", "label": "補記這餐" }`
- `{ "action_id": "estimate_now", "label": "先幫我估" }`
- `{ "action_id": "skip_rescue", "label": "先不管" }`

若 `special_posture = escalate`，改為：

- `{ "action_id": "see_calibration", "label": "看看計畫重啟" }`
- `{ "action_id": "skip_rescue", "label": "先不管" }`

### 9.5 `reject_rescue_plan` 的行為

使用者點擊 `不要這個方案` 後：

- 系統在 chat 中問原因（例如「好的，可以告訴我為什麼嗎？太嚴格了，還是現在不想管？」）
- 不自動切換成另一個 backup proposal
- 不自動關閉 open rescue proposal
- 使用者回答後，系統可依原因決定：
  - 若「太嚴格」→ 提示可用 `更長更緩和`
  - 若「現在不想管」→ 標記 proposal 為 `dismissed`，不再主動推送

### 9.5A 抱怨語氣 ≠ Reject

**正式規則：表達不滿或抱怨的語氣，不等於明確拒絕 rescue proposal。**

例子：

- 「這樣也太硬了吧」→ **不是 reject**，是對方案強度的抱怨或疑問，應路由為 `answer_only`（disposition: answer_only）
- 「這樣我做得到嗎」→ **不是 reject**，是詢問可行性
- 「有點難耶」→ **不是 reject**，是表達猶豫

以下才算明確 reject：

- 「不要」「不用了」「算了」「取消」「我不要這個方案」
- 明確說「我不接受」「不照這個做」

規則：

- 若 utterance 只表達抱怨、疑問、或猶豫，應路由為 `answer_only`，不改變 proposal state
- 若 utterance 含有明確拒絕語意，才路由為 `reject`
- 邊界模糊時，應優先保守路由為 `answer_only`，讓使用者在 response 中有機會明確表態

### 9.6 `explain_rescue_plan` 的行為

使用者點擊 `為什麼這樣建議` 後，系統應說明：

- 這次超出多少 kcal
- 為什麼建議這個天數（以 15% 每日上限為基準）
- 每天大約需要少吃多少
- 為什麼這樣比較健康（不是懲罰，是讓身體有時間調整）

### 9.7 Chat Delivery 形狀

rescue 訊息必須是獨立的一則訊息，不可夾帶在 intake reply 裡。

規則：

- intake reply 完成後，rescue 若需要送出，應作為獨立的下一則訊息
- 不允許在同一則 intake 回覆裡附加 rescue 第二段
- proactive rescue 由 `ProactiveScheduler` 觸發，作為獨立訊息送出
- reactive rescue（使用者主動問）作為獨立回覆送出

---

## 10. Rescue Guardrails

### 10.1 不可讓 rescue 變成懲罰機制

不應提出：

- 極端低熱量方案
- 讓未來多天難以執行的懲罰式補償
- 明顯超過 safety floor 的壓縮方案

### 10.2 與 calibration safety floor 對齊

rescue safety floor 的權威值來源為 `active BodyPlan.safety_floor_kcal`。

在 v1 正式規則下：

- active `BodyPlan.safety_floor_kcal` 應承載使用者目前生效的 hard floor
- 這個 hard floor 在產品政策上可由 baseline safety floor 生成：
  - 女性 baseline `1200 kcal/day`
  - 男性 baseline `1500 kcal/day`
- runtime 可接受 explicit override，但不得在缺值時自行推斷 sex / gender / profile 後臨時計算新的 floor

正式規則：

- rescue proposal 不得低於 resolved `safety_floor_kcal`
- `BodyPlan.safety_floor_kcal` 是 runtime 的 canonical source；不是臨時 heuristic
- recommendation / calibration 的日常建議熱量應另行計算，不得把 `safety_floor_kcal` 直接當成個人化 target
- 個人化 target 可依身高、體重、年齡、活動量與每週減重速度形成 deterministic estimate，但最終仍不得低於 hard floor

則應優先：

- 拉長 horizon
- 降低修復幅度
- 或升級成 `rescue_stop_and_escalate`

說明：

- `1200 / 1500` 應被視為 v1 的 hard lower-bound policy，而不是個人化日常 target
- 個人化 target 與 deficit 建議可高於此值，並應由 calibration / target-calculation logic 另行決定

### 10.3 單次 rescue 的調整步長

v1 採單一分攤模型，調整步長規則如下：

**標準模式（standard）**：

- 單日回收量不超過每日有效預算的 `15%`
- 最多分攤 `5` 天

**積極模式（aggressive）**：

- 使用者選擇 `更短更積極` 後啟用
- 單日回收量上限放寬到每日有效預算的 `20%`
- 最多分攤 `5` 天
- 若連 `20%` 上限都無法在 5 天內完成，明確告知不可行，不繼續加大壓縮

**共同規則**：

- 任何模式下，每日實際攝取不得低於 `safety_floor_kcal`
- 若 safety floor 限制導致無法完成回收，應升級到 `rescue_stop_and_escalate`
- 不應提出讓未來多天難以執行的懲罰式補償

---

## 11. Rescue 與 Recommendation 的關係

### 11.1 rescue 會直接影響 recommendation posture

一旦 rescue proposal 被接受，recommendation 應讀新的短期 caloric posture。

### 11.2 `next_meal_protection`

這是 rescue 與 recommendation 最直接的接點。

也就是：

- rescue 負責定下一餐應守的 caloric posture
- recommendation 負責在該 posture 下給使用者願意吃的選擇

---

## 12. Rescue 與 Calibration 的邊界

### 12.1 rescue 適用於短期偏離

例如：

- 一餐爆卡
- 一兩天超標
- 可透過短 horizon 補回來

### 12.2 calibration 適用於結構性偏移

例如：

- 長期赤字不成立
- rescue 已 repeatedly non-viable
- 現有 plan 不可持續

### 12.3 升級條件

不建議用固定失敗次數。

應以：

- `rescue_horizon`
- `recovery_viability`
- 近期 rescue history

共同判定是否升級。

若 `recovery_viability = non_viable`，`rescue_stop_and_escalate` 應成為合法 top option。

---

## 13. Commit Contract

### 13.1 什麼需要 proposal accept

- 短期 rescue overlay
- 未來幾天的 caloric posture change
- 與 rescue 相關的 `LedgerEntry`

### 13.2 application layer 落地後應做的事

- 建立或更新 `ProposalContainer`
- 標記 accepted option
- 建立 `LedgerEntry(rescue_overlay)` 或等價 overlay effect
- refresh `CurrentBudgetView`
- refresh recommendation posture

### 13.3 生效時機

rescue accept 應偏向立即或下一餐生效，而不是拖太久。

v1 可採：

- 若是 `next_meal_protection`：立即生效於下一餐
- 若是 `same_day_soft_cap`：11:00 前可從今日午餐後生效；11:00 後不應強行壓縮當日晚間到不合理
- 若是 `short_horizon_spread`：11:00 前可從今日午餐後生效；11:00 後從明日 00:00 開始
- 若是 `logging_first_rescue`：可立即生效

---

## 14. Important Types / Interfaces

建議正式化：

- `RescueTriggerResult`
- `RescueAssessmentResult`
- `RescueOption`
- `RescueResponseResult`
- `RescueCommitEffect`
- `RescueResponseCard`

`RescueAssessmentResult` 最小欄位：

- `rescue_needed`
- `rescue_horizon`
- `recovery_viability`
- `recommended_rescue_family`
- `escalation_risk`
- `assessment_confidence`

`RescueOption` 最小欄位：

- `proposal_option_id`
- `option_family`
- `option_label`
- `option_summary`
- `effect_type`
- `effect_payload`
- `expected_effect_summary`
- `guardrail_summary`
- `confidence`

### 14A. `RescueResponseCard` 最小欄位

`RescueResponseCard` 是 rescue response pass 輸出給 chat / UI 消費的 proposal card 結構。

v1 採單一分攤模型，card 結構對應如下：

最小欄位：

- `card_id`：對應 `proposal_id`
- `overshoot_kcal`：本次超出量
- `recommended_days`：建議分攤天數
- `daily_kcal_adjustment`：每日回收量（負數）
- `cap_mode`：`standard`（15%）或 `aggressive`（20%）
- `effective_from`：`today` / `tomorrow`（依 11:00 規則決定）
- `headline`：對外顯示的短標題，例如「超出約 400 大卡，建議分 3 天補回來」
- `summary`：一到兩句說明效果與每日大約少吃多少
- `guardrail_note`：若有 safety floor 限制相關說明
- `quick_actions`：此 card 對應的 quick action 列表（見 Section 9.4）

### 14B. Rescue Accept / Reject API Contract

**Accept 觸發來源**：

- `chat`：使用者說「接受」「好」「就這樣」等明確接受語意，或點擊 `accept_rescue_plan`
- `ui`：使用者在 UI proposal inbox 點擊接受
- `smart_chip`：使用者點擊 LINE 訊息中的快捷按鈕

**Accept 最小輸入**：

```json
{
  "proposal_id": "<ProposalContainer.proposal_id>",
  "commit_source": "chat | ui | smart_chip",
  "accepted_at": "<ISO 8601 timestamp>",
  "user_id": "<user_id>",
  "cap_mode": "standard | aggressive"
}
```

**Accept 後 application layer 必須執行**：

1. 更新 `ProposalContainer.status` 為 `accepted`
2. 依 `recommended_days` 建立多筆 `LedgerEntry(rescue_overlay)`，每日一筆
3. 每筆 `LedgerEntry` 的 `delta_kcal` = `daily_kcal_adjustment`
4. `effective_from` 依 11:00 規則決定（見 Section 3.1A）
5. refresh `CurrentBudgetView`
6. refresh recommendation posture
7. 回傳 `RescueCommitEffect`

**Reject 觸發來源**：

- 使用者點擊 `reject_rescue_plan` 或說「不要」「算了」等明確拒絕語意

**Reject 後行為**：

- 系統在 chat 中問原因（不自動關閉 proposal）
- 不自動切換成另一個方案
- 依使用者回答決定後續：
  - 「太嚴格」→ 提示可用 `extend_rescue_plan`
  - 「現在不想管」→ 標記 `ProposalContainer.status = dismissed`

**`RescueCommitEffect` 最小欄位**：

- `proposal_id`
- `recommended_days`
- `daily_kcal_adjustment`
- `cap_mode`
- `ledger_entries_created[]`
- `effective_from`
- `effective_to`
- `budget_view_refreshed`: boolean
- `recommendation_posture_updated`: boolean
- `escalation_flagged`: boolean（僅 `rescue_stop_and_escalate` 時為 true）

---

## 15. 與其他 specs 的對齊

### 對 L0

rescue 是 future-oriented 的短期恢復能力，不是責備系統。

### 對 L1

rescue 影響 budget posture 時必須 proposal-first。

### 對 L2

依賴：

- `DayBudgetLedger`
- `LedgerEntry(rescue_overlay)`
- `ProposalContainer`
- `ProposalOption`

### 對 L3.1

intake 是 rescue trigger 的主要來源之一。

### 對 L3.2

rescue accept 後，recommendation 需讀新的短期 caloric posture。

### 對 L3.3A / L3.3B

當 rescue non-viable 時，應讓 calibration / `計畫重啟` 進場，而不是繼續硬攤。

---

## 16. 測試情境

後續至少應覆蓋：

- overshoot 在 15% 標準模式下正確算出建議天數
- overshoot 需要超過 5 天才能回收時，標記 `non_viable` 並進 `rescue_stop_and_escalate`
- `更短更積極` 放寬到 20% 後重新計算天數
- 連 20% 都無法在 5 天內完成時，明確告知不可行
- `更長更緩和` 在已是 5 天時告知已是最緩和版本
- logging 不足時，`logging_first_rescue` posture 優先
- rescue 不提出低於 safety floor 的方案
- accept 後正確建立多筆 `LedgerEntry(rescue_overlay)`
- recommendation 正確讀到 rescue 後的 caloric posture
- rescue 訊息不出現在 intake reply 裡（獨立訊息）
- `reject_rescue_plan` 後系統問原因，不自動切換方案
- proactive rescue 作為獨立訊息送出，不夾帶在 intake 回覆裡

---

## 17. v1 Default Decisions

1. v1 rescue 採單一分攤模型，不是多 family 選單
2. 標準模式每日回收上限：每日有效預算的 `15%`
3. 積極模式每日回收上限：每日有效預算的 `20%`（使用者選擇 `更短更積極` 後啟用）
4. 最大分攤天數：`5` 天
5. 超過 5 天仍無法回收 → `recovery_viability: non_viable` → `rescue_stop_and_escalate`
6. `recovery_viability` 採三段式：
   - `viable`：在合法 horizon 與 safety floor 內可完成，且單日壓縮不超過 `15%`
   - `strained`：理論可完成，但會逼近 `15%` 壓縮上限、或明顯增加未來 adherence 風險
   - `non_viable`：需要跌破 floor、超過 `20%`（即使積極模式）、或 horizon 超過 5 天
7. `strained` 可進標準分攤，但應在 response 中提示使用者這已是較緊的方案
8. `non_viable` 必須進 `rescue_stop_and_escalate`，不得繼續硬攤

---

## 18. Degraded Mode Policy

### 18.1 定位

當 LLM provider 不可用、required view 無法取得、或 pass 輸出不合法時，rescue flow 應有明確的 degraded mode 行為。

### 18.2 Provider 不可用

rescue flow 的前兩個 pass（`rescue_trigger_pass`、`rescue_assessment_pass`）是 deterministic，不依賴 LLM。

若 `rescue_option_pass`（hybrid）或 `rescue_response_pass`（LLM）不可用：

| Pass | Degraded 行為 |
|------|-------------|
| `rescue_option_pass` | 若 deterministic 部分已完成，可用 rule-based fallback 選出 top option（依 `recommended_rescue_family` 直接映射）；跳過 LLM ranking |
| `rescue_response_pass` | 使用 deterministic template 組出最小合法 response；不顯示 coaching tone，只顯示方案摘要與 quick actions |

### 18.3 Required View 無法取得

| View | 無法取得時的行為 |
|------|--------------|
| `CurrentBudgetView` | rescue flow 無法執行；不觸發 rescue；標記 `rescue_skipped: budget_view_unavailable` |
| `ActiveBodyPlanView` | rescue 可執行，但 safety floor 使用 conservative default（`1500 kcal/day`）；在 trace 中標記 `safety_floor_source: conservative_fallback` |
| `RescueHistorySummary` | rescue 可執行，但 `recovery_viability` 計算不考慮歷史 rescue 次數；可能略為高估 viability |
| `OpenProposalsView` | rescue 可執行，但無法檢查是否有 open rescue proposal；可能重複建立 proposal |

### 18.4 Rescue 在 Onboarding 未完成時

若 `BodyPlan` 不存在（使用者跳過 onboarding）：

- rescue flow 不應觸發
- `ProactiveScheduler` 的 `budget_alert_check` 應在 `BodyPlan` 不存在時跳過
- 若使用者在 chat 中主動問「我今天爆卡了怎麼辦」，應引導進入 onboarding 而不是執行 rescue
