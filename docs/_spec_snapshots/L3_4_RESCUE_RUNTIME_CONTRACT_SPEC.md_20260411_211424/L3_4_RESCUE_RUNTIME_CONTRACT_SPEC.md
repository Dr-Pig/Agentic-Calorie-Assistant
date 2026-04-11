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
- current intake event context
- recent rescue history

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

形成 rescue proposal options，並決定主推方案。

`decision_mode: hybrid`
`decision_reason: option legality 應 deterministic-first，但在多個合法 rescue family 間選主推方案屬權衡問題`

### 8.2 可讀

- `rescue_assessment_result`
- `CurrentBudgetView`
- `ActiveBodyPlanView`
- recommendation context
- recent rescue outcomes

### 8.3 rescue option families

至少支援：

#### `same_day_soft_cap`

適用：

- 當日仍有剩餘空間
- overshoot 不大

效果：

- 對當日剩餘 intake 給出柔性上限

#### `short_horizon_spread`

適用：

- 需要分攤到未來數天
- 但仍在合理範圍

效果：

- 透過數日小幅 overlay 回收本次 overshoot

規則：

- v1 預設只允許 3 天或 5 天 spread
- 不應把 rescue horizon 無限拉長

#### `next_meal_protection`

適用：

- 當前重點是保護下一餐不要再失守

效果：

- 給下一餐 clear calorie posture
- 可直接銜接 recommendation

#### `logging_first_rescue`

適用：

- 目前連這次 overshoot 的真實規模都不夠清楚

效果：

- 先補記、先釐清，再決定是否需要正式 rescue

#### `rescue_stop_and_escalate`

適用：

- `recovery_viability = non_viable`

效果：

- 不再繼續攤平
- 導向 calibration / `計畫重啟`

### 8.4 必須輸出

- `rescue_options[]`
- `top_option`
- `backup_options[]`
- `option_effect_summaries`
- `guardrail_notes`

---

## 9. Pass 4: `rescue_response_pass`

### 9.1 目標

把 rescue proposal 轉成可執行、低挫敗感的對外呈現。

`decision_mode: llm`
`decision_reason: 此步驟主要負責 coaching tone、proposal framing、與 user-facing explanation`

### 9.2 必須輸出

- `reply_text`
- `proposal_cards`
- `top_option`
- `backup_options`
- `quick_actions`
- `ui_hints`

### 9.3 對外呈現原則

- 預設只主推一個方案
- alternatives 可收起，但不可不可見
- 用語應偏未來導向，不責備

### 9.4 quick actions

至少支援：

- `套用這個方案`
- `換個方案`
- `先不要`
- `看明天怎麼吃`

若 top option 是 `logging_first_rescue`，可支援：

- `補記這餐`
- `先幫我估`

---

## 10. Rescue Guardrails

### 10.1 不可讓 rescue 變成懲罰機制

不應提出：

- 極端低熱量方案
- 讓未來多天難以執行的懲罰式補償
- 明顯超過 safety floor 的壓縮方案

### 10.2 與 calibration safety floor 對齊

rescue safety floor 的權威值來源為 `active BodyPlan.safety_floor_kcal`。

若 `BodyPlan.safety_floor_kcal` 尚未設定，才 fallback 到 v1 safety floor heuristic：

- 女性預設 `1200 kcal/day`
- 男性預設 `1500 kcal/day`

正式規則：

- rescue proposal 不得低於 resolved `safety_floor_kcal`
- heuristic fallback 只應作為 v1 相容路徑，不應覆蓋已解析的 `BodyPlan` scalar source

則應優先：

- 拉長 horizon
- 降低修復幅度
- 或升級成 `rescue_stop_and_escalate`

說明：

- 這些數字不應被視為醫療定律，而應視為 v1 的 evidence-informed safety heuristic
- 它們與常見減重建議區間相容，但後續仍可依族群或產品政策調整

### 10.3 單次 rescue 的調整步長

v1 應偏好：

- 小幅、可執行的步長
- 與 `L3.3B budget_adjustment` 不衝突

更具體地說：

- 單日壓縮量不應超過該日有效預算的 15%

若 15% 壓縮仍無法在 safety floor 內完成修復：

- 不應繼續加大壓縮
- 應改為延長至合法 horizon
- 若仍不可行，則升級到 `rescue_stop_and_escalate`

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

- 單次輕微 overshoot 觸發 `same_day_soft_cap`
- 中度 overshoot 觸發 `short_horizon_spread`
- 對下一餐風險高時，`next_meal_protection` 成為主推
- 記錄不清時，`logging_first_rescue` 優先
- `recovery_viability = non_viable` 時，`rescue_stop_and_escalate` 合法成為 top option
- rescue 不提出低於 safety floor 的方案
- accept 後正確建立 rescue overlay
- recommendation 正確讀到 rescue 後的 caloric posture

---

## 17. v1 Default Decisions

1. `recovery_viability` 採三段式啟發：
   - `viable`：在合法 horizon 與 safety floor 內可完成，且單日壓縮不超過 `15%`
   - `strained`：理論可完成，但會逼近 `15%` 壓縮上限、或明顯增加未來 adherence 風險
   - `non_viable`：需要跌破 floor、超過 `15%`、或 horizon 拉長後仍不具可執行性
2. `strained` 可進 `short_horizon_spread` 或 `next_meal_protection`，但不應長期延展
3. `non_viable` 必須前排 `rescue_stop_and_escalate`，不得繼續硬攤
