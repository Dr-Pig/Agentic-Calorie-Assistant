# L3M Guardrail Math Spec

## 1. 目的

本文件定義 `L3.x` 中所有 deterministic guardrail math 的具體公式與分母。

它回答：

- `DayBudgetLedger` 如何重算
- rescue 的 `15%` 分母是什麼
- `remaining_kcal` 的精確算法
- calibration window 需要哪些最小門檻
- 哪些情況只允許 monitor / logging_quality_first

本文件刻意不回答：

- LLM prompt wording
- 生理學理論推導細節
- provider/model 差異

---

## 2. Global Math Rules

### 2.1 Deterministic math inputs only

本文件的公式只能依賴：

- canonical objects
- derived numeric summaries
- explicitly typed runtime inputs

不得依賴：

- 自由文字推論
- prompt 裡的自然語言估計
- 未定義的隱性 heuristic

### 2.1A Decision-Mode Boundary

`L3M` defines deterministic math / guardrail truth, not an LLM reasoning workflow.

Rules:

- formulas, thresholds, boolean gates, viability checks, and safety bounds defined here must not be delegated to LLM truth decisions
- if an `L3.x` runtime step depends on `L3M`, its `decision_mode` should resolve to `deterministic`, or to `hybrid` only when the non-math portion is separately identified
- LLM may only explain already-resolved math results or phrase user-facing guidance without changing the underlying guardrail truth

`L3M` does not authorize free-form model reasoning for safety floor, rescue viability, proposal eligibility, or budget math.

### 2.2 Rounding posture

v1 規則：

- kcal 以 integer 表示
- 百分比計算後若需轉 kcal，採 `floor`
- 除非另有說明，不做銀行家捨入

---

## 3. DayBudgetLedger Math

### 3.1 Base definitions

對任一 `local_date = D`：

- `base_budget_kcal(D)` = 該日基礎可攝取熱量
- `meal_consumption_total(D)` = 所有 active `meal_consumption` entries 的 `delta_kcal` 總和
- `rescue_overlay_total(D)` = 所有 active `rescue_overlay` entries 的 `delta_kcal` 總和
- `calibration_adjustment_total(D)` = 所有 active `calibration_adjustment` entries 的 `delta_kcal` 總和

### 3.2 Effective budget

公式：

`effective_budget_kcal(D) = base_budget_kcal(D) + rescue_overlay_total(D) + calibration_adjustment_total(D)`

注意：

- rescue / calibration adjustment 可能是負值
- 所以這是帶符號加總，不取絕對值

### 3.3 Remaining budget

公式：

`remaining_kcal(D) = effective_budget_kcal(D) - meal_consumption_total(D)`

### 3.4 Consumed kcal

公式：

`consumed_kcal(D) = meal_consumption_total(D)`

### 3.5 Recompute rule

當以下任一事件發生時，必須重算該 `local_date` ledger：

- active meal version 新增
- active meal version supersede
- rescue overlay accept / void
- calibration adjustment accept / void

---

## 4. Rescue Guardrail Math

### 4.1 Overshoot definition

對當日 `D`：

`overshoot_kcal(D) = max(0, meal_consumption_total(D) - effective_budget_kcal(D))`

### 4.2 Rescue spread target

若要對未來 `H` 天分攤：

`target_recovery_kcal = overshoot_kcal(D)`

### 4.3 Max compression denominator

`15%` 的分母是：

`base_budget_kcal(target_day)`

不是：

- TDEE
- effective budget
- remaining budget

公式：

`max_daily_rescue_compression(target_day) = floor(base_budget_kcal(target_day) * 0.15)`

### 4.4 Safety floor check

對 target day：

- female floor = `1200`
- male floor = `1500`

定義：

`candidate_effective_budget(target_day) = base_budget_kcal(target_day) + calibration_adjustment_total(target_day) + proposed_rescue_overlay(target_day)`

合法條件：

`candidate_effective_budget(target_day) >= safety_floor(user)`

### 4.5 Rescue viability rule

對某個 rescue 方案，若存在任一 target day 不滿足以下條件，該方案不可行：

1. `abs(proposed_rescue_overlay(target_day)) <= max_daily_rescue_compression(target_day)`
2. `candidate_effective_budget(target_day) >= safety_floor(user)`

### 4.6 `recovery_viability`

定義：

- `viable`
  - 所有 target days 都同時滿足壓縮上限與 floor
- `strained`
  - 技術上可行，但至少一日的 proposed compression > `10%` 且 <= `15%`
- `non_viable`
  - 任一 target day 超過 `15%` 或跌破 floor

### 4.7 Activation rule

若 rescue family = `short_horizon_spread`

- 接受時間在 `11:00` 前：
  - 可從今日午餐後的可調整區間開始
- `11:00` 後：
  - 從明日 `00:00` 生效

若 rescue family = `next_meal_protection`

- 立即作用於下一餐，不受 `11:00` 限制

---

## 5. Calibration Eligibility Math

### 5.1 Observation window minimum

v1 proposal eligibility 最低門檻：

- 最近 `14` 天 window
- 至少 `5` 次 body observation

若未達：

- `proposal_eligibility = false`
- 決策只能是 `monitor_only` 或 `insufficient_data`

### 5.2 Intake coverage minimum

v1 logging quality 門檻：

`intake_coverage = logged_days_with_meaningful_intake / window_days`

門檻：

- `intake_coverage >= 0.80` 才可進 plan-impacting calibration proposal

若低於：

- 優先 `logging_quality_first`

### 5.3 Drift evidence posture

若同時滿足：

- observation window 合法
- intake coverage 合法
- trend stability != `insufficient_data`

才允許把 drift signal 當作 proposal gate 依據。

否則：

- 不得直接進 `budget_adjustment / pace_adjustment / plan_reset`

### 5.4 Behavior-first attribution gate

若 intake coverage < `0.80` 或 adherence posture = `poor`

則：

- 不得直接下 `expenditure_shift` 高信心結論
- 應先 `logging_quality_first` 或 `monitor_only`

---

## 6. Recommendation Guardrail Math

### 6.1 Remaining-kcal posture

recommendation 讀：

`remaining_kcal(today) = effective_budget_kcal(today) - meal_consumption_total(today)`

### 6.2 Budget posture classification

v1 建議分層：

- `on_track`
  - `remaining_kcal >= 0.35 * effective_budget_kcal(today)`
- `tight`
  - `0 <= remaining_kcal < 0.35 * effective_budget_kcal(today)`
- `over_budget`
  - `remaining_kcal < 0`
- `unknown`
  - ledger 不足

### 6.3 Candidate legality heuristic

recommendation 不是硬數學 commit，但候選要受這個 heuristic 約束：

- `tight` posture 時，不應主推明顯超過 `remaining_kcal + 150` 的候選
- `over_budget` posture 時，應優先：
  - lower-calorie fallback
  - next_meal_protection style suggestion
  - non-liquid / safer candidates if relevant

這是 ranking guardrail，不是 persistence formula。

---

## 7. Meal Commit Arithmetic

### 7.1 Meal total kcal

若有 `component_estimates[]`：

`meal_total_kcal = sum(component.estimated_kcal)`

若 assembled payload 已明確給 `estimated_kcal`：

- v1 可接受 `estimated_kcal` 作 canonical version total
- 但若 component sum 與 total 明顯矛盾，應記 trace anomaly

### 7.2 Macro derivation posture

v1 規則：

- meal commit 以 kcal truth 為主
- macro derivation failure 不阻止 meal commit
- 只有 commit-critical fields 缺失才阻止 commit

---

## 8. Cross-Midnight Attribution Math

### 8.1 Local date truth

若 `occurred_at_local` 可判定：

- ledger attribution 以 `occurred_at_local.date()` 為準

若使用者是補記：

- 仍以被解析出的 `occurred_at_local` 為準，不以 `recorded_at` 替代

若無法判定：

- v1 fallback 可用 `recorded_at_local.date()`
- 但需 trace `time_attribution_uncertain = true`

---

## 9. No-Guess Zones

以下數學決策不得讓 agent 自由猜：

- rescue 的 15% 分母
- safety floor 判定
- remaining kcal 計算方式
- `effective_budget_kcal` 的加總公式
- calibration proposal eligibility 的 `14/5/80%` 門檻

---

## 10. Implementation Rule

任何 deterministic code 涉及：

- ledger recompute
- rescue spread
- budget remaining
- calibration gate
- cross-midnight attribution

都必須直接以本文件公式實作，不得自行引入替代算法。
