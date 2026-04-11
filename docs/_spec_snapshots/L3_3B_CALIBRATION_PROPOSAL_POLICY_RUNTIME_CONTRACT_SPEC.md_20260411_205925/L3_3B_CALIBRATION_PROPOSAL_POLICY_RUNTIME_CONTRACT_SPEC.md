# L3.3B Calibration Proposal Policy / Runtime Contract Spec

## 1. 目的

這份 spec 定義 calibration 的 proposal policy 與 runtime contract。

它承接 `L3.3A Deficit / Expenditure Calibration Model Spec`，回答：

- 什麼情況允許從 calibration model 進入 proposal flow
- calibration proposal 預設應提什麼類型的方案
- proposal option 應如何被排序、呈現、確認與落地
- `logging_quality_first`、`monitor_only`、`budget adjustment`、`plan reset` 等方案的邊界是什麼
- calibration accept 後如何回寫 `BodyPlan`、`LedgerEntry` 與 downstream budget posture

它暫時不回答：

- prompt wording
- LLM / model selection
- benchmark implementation

---

## 2. 核心定位

calibration proposal 不是 calibration 的核心真相，而是 calibration 判斷之後的輸出形式。

也就是：

- `L3.3A` 先判斷資料品質、operating expenditure、deficit reality、mismatch attribution
- `L3.3B` 再決定要不要提案、提什麼案、怎麼提

正式規則：

- proposal 必須建立在 `L3.3A` 的輸出之上
- proposal-first 只適用於會改變 active plan、effective budget、或中期 recommendation posture 的變更
- observation write 不需要 proposal

---

## 3. Proposal Eligibility Gate

### 3.1 進入 proposal flow 的最低條件

- `decision_mode: deterministic`
- `decision_reason: proposal eligibility 是來自 `L3.3A` posture 與門檻的布林 gate`

至少應同時滿足：

- `proposal_eligibility = true`
- `calibration_confidence` 達最低門檻
- `logging_quality_posture` 不是 `insufficient_data`
- `deficit_reality_status` 不是純短期噪音

### 3.2 不應進入 proposal flow 的情況

以下情況應優先停在非 proposal posture：

- `insufficient_data`
- `logging_quality_first`
- `monitor_only`
- `likely_noise_only`
- 最近已有相似 calibration proposal 尚未結束

### 3.3 proposal gate 的核心原則

calibration proposal 應寧可少提，也不要在低品質資料上過度調 plan。

---

## 4. Proposal Option Families

calibration proposal option 至少分成以下族群：

### 4.1 `monitor_only`

適用情境：

- 訊號存在但仍不夠穩
- 偏差幅度小
- 近期 observation window 還在累積

效果：

- 不改 active `BodyPlan`
- 不改 effective budget
- 建立後續觀察期

### 4.2 `logging_quality_first`

適用情境：

- 資料量勉強足夠，但 logging 品質不足
- mismatch 更像 intake underestimation 或 logging gap

效果：

- 不直接改 plan
- 要求或引導進入較乾淨的記錄期
- 強化體重 / intake 記錄一致性

### 4.3 `budget_adjustment`

適用情境：

- operating expenditure 已有足夠可信度
- 目前赤字與預期不一致
- 透過調整每日目標熱量即可修正

效果：

- 調整 effective daily budget posture
- 必要時建立 `LedgerEntry(calibration_adjustment)`
- 反映到 recommendation 的 caloric posture

### 4.4 `pace_adjustment`

適用情境：

- 問題不只是短期攝取目標，而是整體減重速度過激或不合理

效果：

- 調整 target rate / plan aggressiveness
- 可伴隨較溫和的 budget policy

### 4.5 `plan_reset`

適用情境：

- 原本方案長期不可行
- rescue 已失去 recovery viability
- 使用者需要重新設定較可持續的節奏

效果：

- 建立新的 `BodyPlan` version
- 明確 supersede 舊 plan

---

## 5. Proposal Generation Priority

在 v1 的 calorie-deficit 產品核心下，proposal family 應依以下優先順序考慮：

1. `logging_quality_first`
2. `monitor_only`
3. `budget_adjustment`
4. `pace_adjustment`
5. `plan_reset`

這代表：

- 先修資料品質
- 再觀察
- 再調熱量
- 最後才動整體節奏或重設計畫

---

## 6. Runtime Shape

`L3.3B` 的 canonical default 應採 2-3 node graph：

1. `deterministic_proposal_gate`
2. `proposal_policy_shaping`
3. `proposal_response`（若 surface 需要）

補充規則：

- `proposal_gate` 的合法性判斷完全來自 `L3.3A` 的輸出，是確定性閘門，不進 LLM
- `proposal eligibility`、`blocked option families`、`budget delta math`、`effect payload legality` 應優先 deterministic-first
- 當 option family 很少且 effect payload 已模板化時，可直接 collapse 成 `deterministic_proposal_gate -> proposal_response`
- cross-domain 原則見 [`L6E LLM Pass Design Policy Spec`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md)

expanded mode 可保留 4-pass：

1. `proposal_gate_pass`
2. `option_generation_pass`
3. `option_ranking_pass`
4. `proposal_response_pass`

這條 flow 的責任與 intake / recommendation 不同，因為它的核心是：

- gate
- option shaping
- ranking / guardrail
- user-facing proposal presentation

expanded mode 下，只有 LLM-backed 的 named pass 才需要 logical model role 對應：

- `option_generation_pass` -> `strict_reasoner_model`
- `option_ranking_pass` -> `strict_reasoner_model`
- `proposal_response_pass` -> `response_writer_model`

補充規則：

- `proposal_gate_pass` 若保留為 named stage，仍是 deterministic gate，不映射 LLM role

### 6.1 Canonical Output Contract

canonical path 至少應輸出：

- `proposal_gate_decision`
- `proposal_policy_packet`
- `proposal_result`
- `trace_envelope`

其中：

- `proposal_gate_decision` 來自 deterministic gate
- `proposal_policy_packet` 是 graph-neutral shaping artifact
- expanded mode 可再拆成 `proposal_gate_result`、`proposal_options[]`、`option_ranking_result`

---

## 7. Pass 1: `proposal_gate_pass`

### 7.1 目標

根據 `L3.3A` 的輸出判斷：

- 是否允許提案
- 若允許，應提哪一類 proposal family

`decision_mode: deterministic`
`decision_reason: proposal gate 的合法性完全來自 calibration outputs，不應由 LLM 重做 truth judgment`

### 7.2 可讀

- `operating_expenditure_estimate`
- `intake_estimation_bias_posture`
- `deficit_reality_status`
- `mismatch_attribution`
- `calibration_confidence`
- `logging_quality_posture`
- `trend_window_summary`
- `CurrentBudgetView`
- `ActiveBodyPlanView`
- rescue viability summary

### 7.3 必須輸出

- `proposal_gate_result`
- `allowed_option_families[]`
- `blocked_option_families[]`
- `gate_rationale`
- `primary_policy_posture`

### 7.4 不可做的事

- 不直接產生最終 option payload
- 不直接 accept proposal
- 不直接改 active state

---

## 8. Pass 2: `option_generation_pass`

### 8.1 目標

針對被允許的 option family 產生可呈現、可比較的 proposal options。

`decision_mode: hybrid`
`decision_reason: effect payload 與 legality 應 deterministic-first，但多個合法 proposal 的 shaping 與 framing 可使用 LLM`

### 8.2 可讀

- `proposal_gate_result`
- `ActiveBodyPlanView`
- `CurrentBudgetView`
- `L3.3A` calibration outputs

### 8.3 必須輸出

- `proposal_options[]`
- `default_option_candidate`
- `option_effect_summaries`
- `guardrail_notes`

### 8.4 option payload 最少應包含

- `option_label`
- `option_family`
- `effect_type`
- `effect_payload`
- `expected_effect_summary`
- `reversibility_hint`
- `guardrail_summary`
- `confidence`

### 8.5 v1 option shaping 原則

- 方案要圍繞熱量赤字管理
- 預設先給低侵入性選項
- 不要一開始就只給激進方案

---

## 9. Pass 3: `option_ranking_pass`

### 9.1 目標

決定哪些 options 應該成為主推與備選。

`decision_mode: hybrid`
`decision_reason: guardrail legality 應 deterministic-first，但在多個合法 option 間做主推排序屬政策權衡`

### 9.2 ranking 原則

優先考量：

- 資料品質 posture
- 對赤字管理的直接幫助
- 對使用者負擔的大小
- reversibility
- 與當前 rescue / recommendation posture 的相容性

### 9.3 預設排序傾向

在一般情況下：

- `logging_quality_first` 應高於直接改 plan
- 小幅 `budget_adjustment` 應高於 `plan_reset`
- `plan_reset` 只有在短期修復已 non-viable 時才進前排

### 9.4 必須輸出

- `top_option`
- `backup_options[]`
- `ranking_explanation`
- `presentation_policy`

---

## 10. Pass 4: `proposal_response_pass`

### 10.1 目標

把 calibration proposal 轉成可理解、可確認的對外呈現。

`decision_mode: llm`
`decision_reason: 此步驟主要負責 negotiation framing 與 user-facing wording`

### 10.2 必須輸出

- `reply_text`
- `proposal_cards`
- `top_option`
- `backup_options`
- `quick_actions`
- `ui_hints`

### 10.3 提案密度

預設應採：

- `single primary recommendation`
- hidden alternatives by default

也就是：

- 對外預設只主推一個最優方案
- 備選方案預設收起來
- 只有當使用者拒絕、要求其他方案、或主動展開時，才揭露 alternatives

### 10.3 quick actions

至少應支援：

- `套用這個方案`
- `看其他方案`
- `先維持不變`
- `之後再說`

若 top option 是 `logging_quality_first`，也可支援：

- `開始 7 天乾淨記錄`
- `先只記體重`
- `提醒我補記`

### 10.4 不可做的事

- 不直接 commit
- 不可讓 alternatives 不可見或不可取得
- 不把 monitor 訊息偽裝成 plan change

---

## 11. `logging_quality_first` Contract

### 11.1 定位

`logging_quality_first` 是合法且重要的 calibration proposal family。

它的目的是：

- 在資料不夠乾淨時，先改善記錄品質
- 避免系統過早把偏差誤歸因成 expenditure shift

### 11.2 最小 effect payload

至少可包含：

- `recording_window_days`
- `required_weight_check_count`
- `required_intake_coverage_target`
- `follow_up_strategy`

### 11.3 預設建議窗

`logging_quality_first` 的 v1 預設乾淨記錄期應為：

- 7 天預設
- 必要時可延長到 10 天

理由：

- 7 天足以覆蓋一個完整週期，包含週末
- 10 天可作為資料品質仍邊界時的保守延長

### 11.4 與 intake runtime 的關係

accept 後可影響：

- reminder posture
- follow-up priority
- logging-related proactive triggers

但不應直接重寫 nutrition truth。

---

## 12. `budget_adjustment` Contract

### 12.1 定位

在 calorie-deficit product core 下，`budget_adjustment` 是 calibration proposal 的主要可執行輸出之一。

### 12.2 最小 effect payload

至少可包含：

- `new_daily_budget_kcal`
- `delta_kcal`
- `effective_from`
- `review_after_days`
- `rationale_summary`

### 12.3 調整步長與安全底線

`budget_adjustment` 的 v1 預設單次調整步長應為：

- 150 到 200 kcal

並採 safety floor heuristic：

- 女性預設 intake floor 不低於 `1200 kcal/day`
- 男性預設 intake floor 不低於 `1500 kcal/day`

若 proposal 將導致目標低於 floor，系統不應再提出更低 intake 的方案，而應改為：

- 延長觀察或執行時間窗
- 降低減重速度
- 建議增加活動量
- 或改為 `計畫重啟`

### 12.4 accept 後 side effects

- 建立新的 `BodyPlan` version 或等價 active policy version
- 更新 effective budget posture
- 必要時建立 `LedgerEntry(calibration_adjustment)`
- 更新 recommendation caloric posture

---

## 13. `plan_reset` Contract

### 13.1 什麼情況才應出現

只有在以下情況才應被放進 option set：

- rescue horizon 已明顯非可行
- recovery viability 很低
- 當前 plan 長期不可持續
- 使用者需要更可持續的節奏而不是繼續硬撐

### 13.2 不建議的做法

- 不用固定「失敗幾次」當唯一門檻
- 不要因單次體重波動就推 plan reset

### 13.3 最小 effect payload

- `new_target_rate`
- `new_budget_posture`
- `reset_reason`
- `review_window_days`

### 13.4 對外命名

對外使用者語言應優先採：

- `計畫重啟`

內部型別可保留：

- `plan_reset`

---

## 14. Commit Contract

### 14.1 什麼可直接 commit

- proposal acceptance event
- proposal rejection event
- proposal expiry bookkeeping

### 14.2 什麼需 proposal accept 才能 commit

- active `BodyPlan` update
- effective budget posture change
- `LedgerEntry(calibration_adjustment)`
- long-term plan aggressiveness change

### 14.3 application layer 落地後應做的事

- 建立或更新 `ProposalContainer`
- 標記 accepted option
- 建立新 `BodyPlan` version
- supersede 舊 active plan
- 依 option family 建立對應 side effects
- refresh `ActiveBodyPlanView`
- refresh `CurrentBudgetView`

### 14.4 生效時機

若接受的是會影響帳務或有效預算的 calibration proposal，例如：

- `budget_adjustment`
- `pace_adjustment`
- `plan_reset`

則 v1 預設採：

- 當地時間 `11:00` 前接受：今日生效
- 當地時間 `11:00` 後接受：明日生效

若接受的是 `logging_quality_first` 或純觀察類型：

- 可立即生效

---

## 15. 與其他 flows 的邊界

### 15.1 與 L3.1 Intake

- intake 提供 logging quality 與 calorie estimate 基礎
- calibration proposal 不應直接改寫 intake truth
- `logging_quality_first` 可改變 reminder / follow-up posture，但不應變成 nutrition override

### 15.2 與 L3.2 Recommendation

- calibration accept 後，recommendation 需讀新 budget posture
- 若 v1 主軸是熱量赤字，proposal accept 的主要影響先落在 caloric posture

### 15.3 與 Rescue

- rescue 是短期赤字恢復
- calibration proposal 是中期 plan 校正
- rescue non-viable 時，允許 calibration option set 出現 `plan_reset`

---

## 16. Important Types / Interfaces

建議正式化：

- `ProposalGateResult`
- `CalibrationProposalOption`
- `CalibrationProposalRankingResult`
- `CalibrationProposalResponseResult`
- `CalibrationProposalCommitEffect`

`CalibrationProposalOption` 最小欄位：

- `proposal_option_id`
- `option_family`
- `option_label`
- `option_summary`
- `effect_type`
- `effect_payload`
- `expected_effect_summary`
- `guardrail_summary`
- `reversibility_hint`
- `confidence`

---

## 17. 測試情境

後續至少應覆蓋：

- `logging_quality_first` 在資料品質不足時成為 top option
- `monitor_only` 在訊號不足時不誤升級成 `budget_adjustment`
- `budget_adjustment` 在 high-confidence mismatch 下成為主推
- `plan_reset` 不會在短期噪音下被前排推薦
- proposal accept 後正確建立新 `BodyPlan`
- `LedgerEntry(calibration_adjustment)` 只在需要時建立
- recommendation 在 accept 後讀到新的 caloric posture
- rescue non-viable 時，`plan_reset` 合法進入 option set

---

## 18. v1 Default Decisions

1. proposal accept 後，recommendation posture 應立即刷新
2. `CurrentBudgetView` 與 `ActiveBodyPlanView` 應在同一個 commit transaction 完成後同步更新
3. UI / chat 在 accept 後看到的 recommendation，應以新 posture 為準，不允許保留舊 caloric posture 做長延遲過渡
