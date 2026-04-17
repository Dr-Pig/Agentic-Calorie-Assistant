# L5B Benchmark Spec

## 1. 目的

這份 spec 定義 benchmark dataset、case taxonomy、bucket coverage、dataset governance、以及 benchmark 的演進方式。

它要回答：

- v1 要測哪些 bucket
- 每個 bucket 最低需要多少 case
- `golden / edge / adversarial / regression / safety_critical` 怎麼分
- `real-derived` 與 `synthetic` 的比例怎麼抓
- regression case 何時升級
- cross-flow stress set 至少要覆蓋什麼
- benchmark 應如何持續擴張而不失控

---

## 2. Supporting Docs

本 spec 依賴下列 supporting docs：

- case schema 以 [`docs/quality/BENCHMARK_CASE_SCHEMA.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/BENCHMARK_CASE_SCHEMA.md) 為準
- benchmark repo layout 以 [`docs/quality/BENCHMARK_FOLDER_LAYOUT.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/BENCHMARK_FOLDER_LAYOUT.md) 為準
- stateful multi-turn case 模板以 [`docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/STATEFUL_MULTI_TURN_CASE_TEMPLATE.md) 為準
- supporting-doc drift 與額外欄位對齊以 [`docs/quality/BENCHMARK_SUPPORTING_DOCS_ALIGNMENT.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/BENCHMARK_SUPPORTING_DOCS_ALIGNMENT.md) 為準
- suite-level inventory、authority tier、以及 suite 與既有資產的映射以 [`docs/quality/L5D_SUITE_GOVERNANCE_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5D_SUITE_GOVERNANCE_SPEC.md) 為準

### 2.1 與 L5D 的分工

`L5B` 保留：

- bucket taxonomy
- case classes
- minimum case counts
- source mix
- case schema

`L5D` 則作為上層 suite-governance layer，負責：

- `suite_id`
- `authority_tier`
- `maturity_status`
- `workflow_family`
- `capability_family`
- `validation_layer`
- suite promotion 與 migration ownership

對 intake 等成熟 workflow，`L5B` bucket 是 scenario parent grouping；`L5D` suite 是 finer-grained execution unit。

---

## 3. Benchmark Philosophy

benchmark 不只是測回答像不像，而是要測：

- runtime contract 是否被遵守
- policy guardrail 是否被遵守
- multi-turn / stateful behavior 是否穩定
- degraded / fallback mode 是否合理
- trace 與 review signal 是否可回流

---

## 4. Benchmark Bucket Map

### 4.1 Intake

- `intake_single_turn`
- `intake_multi_turn`
- `historical_correction`
- `time_handling`
- `commit_boundary`

### 4.2 Recommendation

- `recommendation_budget_fit`
- `recommendation_preference_fit`
- `recommendation_location_fallback`
- `recommendation_negative_preference`
- `recommendation_explicit_intake_handoff`

### 4.3 Calibration

- `calibration_insufficient_data`
- `calibration_logging_quality_first`
- `calibration_noise_only`
- `calibration_mismatch`
- `calibration_proposal_gate`

### 4.4 Rescue

- `rescue_same_day_soft_cap`
- `rescue_short_horizon_spread`
- `rescue_next_meal_protection`
- `rescue_logging_first`
- `rescue_non_viable_escalation`

### 4.5 Proactive / Cross-Flow

- `proactive_suppression`
- `cross_midnight`
- `memory_preference_override`
- `proposal_commit_boundary`
- `cross_flow_state_sync`

### 4.6 Tool / Runtime Degradation

- `tool_failure_conservative_fallback`
- `tool_failure_need_more_info`
- `tool_failure_no_commit`
- `tool_reason_presence`

---

## 5. Case Classes

- `golden`
- `edge`
- `adversarial`
- `regression`
- `safety_critical`

### 5.1 golden

正常主流程與高價值成功路徑。

### 5.2 edge

模糊、邊界、壓力較高但仍合理的情境。

### 5.3 adversarial

故意測 boundary、guardrail、錯誤恢復與不合理輸入。

### 5.4 regression

來自真實錯誤、修過的 bug、或高風險重現樣本。

### 5.5 safety_critical

任何涉及 safety floor、implicit state、plan-impacting output、或錯誤 commit 的 case，都應加上 `safety_critical`。

---

## 6. Minimum Case Counts

### 6.1 Tier 1 buckets

主流程 bucket 每桶至少 `20` case：

- `intake_single_turn`
- `intake_multi_turn`
- `historical_correction`
- `recommendation_budget_fit`
- `calibration_proposal_gate`
- `rescue_short_horizon_spread`

建議組成：

- `8 golden`
- `5 edge`
- `4 adversarial`
- `3 regression`

### 6.2 Tier 2 buckets

重要但次核心 bucket 每桶至少 `12` case。

建議組成：

- `5 golden`
- `3 edge`
- `2 adversarial`
- `2 regression`

### 6.3 Tier 3 buckets

補充 / cross-flow bucket 每桶至少 `8` case。

建議組成：

- `3 golden`
- `2 edge`
- `2 adversarial`
- `1 regression`

---

## 7. Source Mix Policy

### 7.1 overall ratio

整體 benchmark v1 應滿足：

- `real-derived >= 30%`
- `synthetic <= 70%`

### 7.2 regression ratio

`regression` set 應優先來自真實案例：

- `real-derived >= 60%`

### 7.3 source guidance

- `golden` 可較多 synthetic
- `edge` 建議 synthetic + real-derived 混合
- `adversarial` 可主要採 hand-crafted synthetic
- `regression` 應優先使用真實錯誤 replay

---

## 7A. Founder Golden Set vs General Sanity Set

`golden dataset` 不是整個 benchmark 的同義詞，而是 benchmark 中最穩定、最適合做 regression gate 的子集。

### 7A.1 founder golden set

v1 應先建立 `Founder Golden Set`，用來覆蓋：

- founder 的高頻真實飲食案例
- founder 常見的多輪 correction
- founder 常見 recommendation / rescue / calibration 情境

### 7A.2 general sanity set

除了 founder golden set，v1 還應保留 `General Sanity Set`，至少覆蓋：

- 基本非 founder 語境的 intake 說法
- 基本 multi-turn / cross-midnight
- 基本 negative preference
- 基本 cross-flow safety sanity

### 7A.3 benchmark weighting guidance

v1 benchmark 可採：

- primary: founder-fit
- secondary: generalized sanity

這樣可以在早期貼近真實使用者，同時避免過度 overfit。

---

## 8. Flow Benchmark Matrices

### 8.1 Intake

至少應覆蓋：

- 單 item / 多 item / 多輪補充 / late clarification
- 歷史修正與 item-level correction
- cross-midnight 與 occurred_at / recorded_at 分離
- default-commit 與 commit-critical fail
- tool failure 時的 conservative fallback / need-more-info / no-commit

### 8.2 Recommendation

至少應覆蓋：

- budget fit
- preference fit
- negative preference
- location fallback
- explicit intake handoff
- 不得產生 implicit meal-intent / pending intake state
- nearby / chain / safe fallback 模式切換

### 8.3 Calibration

至少應覆蓋：

- insufficient data
- logging-quality-first
- noise-only
- mismatch attribution
- proposal gate
- tool / summary failure 下的保守降級

### 8.4 Rescue

至少應覆蓋：

- same-day soft cap
- 1 / 3 / 5 day horizon
- 15% single-day compression guardrail
- safety floor heuristic
- non-viable escalation
- recommendation sync after rescue overlay

---

## 9. Tool Failure / Feedback-Derived Buckets

### 9.1 tool-failure benchmark bucket

至少要有：

- tool unavailable but conservative estimate still possible
- tool unavailable and model should ask for more information
- tool unavailable and runtime should choose no-commit
- tool failure must not be misreported as tool success

### 9.2 feedback-derived regression bucket

manual correction / user feedback 回流後，應形成專門的 replay bucket，至少覆蓋：

- kcal correction replay
- portion correction replay
- recommendation rejection replay
- proposal rejection replay
- time / scope correction replay

---

## 10. Regression Promotion Rule

以下任一情況應升級成 regression：

- 任何 `hard_fail`
- 同類型 `soft_fail` 重複出現 `2` 次以上
- 使用者明確感知、會傷害信任的錯誤
- 已修 production bug
- correction / tool failure / fallback 相關錯誤被真實使用者觸發

---

## 11. Cross-Flow Stress Set Minimum Coverage

v1 `cross-flow stress set` 至少要覆蓋以下 `8` 類：

1. `intake -> ledger -> recommendation`
2. `recommendation -> explicit intake handoff -> intake commit`
3. `body observation -> calibration -> recommendation posture`
4. `overshoot -> rescue -> recommendation sync`
5. `rescue non-viable -> calibration / 計畫重啟`
6. `historical correction -> ledger recompute -> downstream views`
7. `negative preference update -> recommendation / proactive suppression`
8. `cross-midnight intake -> local_date -> rescue/recommendation logic`

最低要求：

- 每類至少 `2` case
- `cross-flow stress set` 總數至少 `16` case

---

## 12. Case Schema

每個 benchmark case 至少應帶：

- `case_id`
- `bucket`
- `case_class`
- `safety_classification`
- `source_type`
- `input_payload`
- `expected_outcome_shape`
- `hard_fail_expectation`
- `notes`
- `version`

建議額外欄位：

- `expected_trace_flags`
- `expected_commit_behavior`
- `expected_proposal_behavior`
- `expected_guardrail_hits`
- `dataset_split`
- `oracle_type`

---

## 13. Dataset Sources

benchmark case 可來自：

- hand-authored canonical scenarios
- synthetic cases
- failure replay
- adversarial hand-crafted cases
- feedback-derived corrected traces

### 13.1 source policy

- `real-derived` 優先給 regression / awkward multi-turn / cross-flow bugs
- `synthetic` 用來擴 coverage 與做 adversarial stress
- `feedback-derived` 優先流入 regression 與 correction replay set

---

## 13A. Golden Dataset Role

`golden dataset` 在本專案中指的是：

- 穩定標註
- 高價值
- 應在版本更新時穩定通過

它是 benchmark 的子集，不是 benchmark 全部。

### 13A.1 golden dataset usage

golden dataset 主要用於：

- prompt / runtime regression gate
- founder-fit 核心體驗守門
- Tier 1 release gate

### 13A.2 non-golden benchmark usage

其餘 benchmark buckets 主要用於：

- edge coverage
- adversarial stress
- safety verification
- cross-flow verification

---

## 14. Safety Coupling

`L5B` 必須和 [`docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md) 對齊。

至少以下違規應必測：

- implicit meal-intent / pending intake state violation
- below-floor caloric posture
- unconfirmed proposal commit
- unresolved meal boundary commit
- non-viable rescue continuing to spread
- tool failure being presented as successful retrieval
- missing `tool_reason` in internal trace

---

## 15. Benchmark Progression

benchmark v1 應按以下階段推進：

### 15.1 smoke set

最小可執行集。  
用來快速確認主要 flow 沒有整體崩壞。

### 15.2 core set

主流程的 `golden / edge / regression`。  
這是日常開發與 prompt / runtime 調整時的主要基準。

### 15.3 stress set

用來壓 multi-turn、stateful、adversarial、safety-critical、與 cross-flow 交界。

---

## 16. Dataset Governance

### 16.1 versioning

每個 benchmark case 應有穩定 `case_id` 與 `version`。  
case 被調整後，不應默默覆蓋舊語意。

### 16.2 review rule

新增 benchmark case 時，應明確標註：

- bucket
- class
- source type
- safety classification
- 為何加入

### 16.3 feedback-derived intake

來自真實 correction / rejection / fallback 的案例，應優先進入：

- regression set
- tool-failure set
- cross-flow stress set

### 16.4 founder-fit tagging

每個 case 應允許標註其所屬資料集分層，例如：

- `founder_golden`
- `general_sanity`
- `stress_only`
- `regression_only`

---

## 17. Oracle / Expected Outcome Types

不同 benchmark bucket 不應共用單一 oracle 形式。v1 至少應支持以下 oracle 類型：

### 17.1 intake oracle

- `expected_state_delta`
- `expected_commit_behavior`
- `expected_guardrail_hits`
- `expected_trace_flags`

### 17.2 recommendation oracle

- `candidate_legality`
- `top_pick_class`
- `forbidden_candidate_presence`
- `explicit_handoff_behavior`

### 17.3 calibration oracle

- `proposal_gate_result`
- `option_family_expectation`
- `forbidden_plan_change`
- `confidence_posture`

### 17.4 rescue oracle

- `rescue_family_expectation`
- `horizon_legality`
- `safety_floor_respected`
- `escalation_behavior`

### 17.5 cross-flow oracle

- `view_refresh_expectation`
- `state_sync_expectation`
- `no_implicit_state_creation`
- `cross_flow_guardrail_hits`

---

## 18. Benchmark Execution Modes

同一 benchmark case 之後可能需要在不同執行層級重播，因此 v1 應先區分：

### 18.1 `offline_deterministic_replay`

只驗證 state transition、guardrail、arithmetic、trace、與 deterministic gate。

### 18.2 `prompt_only_replay`

只驗證某一 pass 或某一 flow 的 prompt / model contract，不要求完整 persistence。

### 18.3 `full_runtime_replay`

驗證完整 orchestration、retrieval、context packing、prompt、deterministic gate、與 state write。

### 18.4 mode declaration

每個 case 應明確標註：

- `execution_mode`
- `required_runtime_layers`
- `mocked_dependencies`

---

## 19. Stateful Benchmark Reset Rule

stateful benchmark 不能依賴前一個 case 的殘留狀態。

### 19.1 default rule

- 每個 case 預設必須從乾淨 `initial_state` 與 `memory_seed` 啟動
- case 執行後產生的狀態不得默默污染下一個 case

### 19.2 allowed exception

若某組 benchmark 明確要測「連續案例序列」，必須顯式標註：

- `sequence_id`
- `sequence_order`
- `shared_seed_contract`

未標註者一律視為獨立 case。

### 19.3 reset verification

benchmark runner 應能驗證：

- seed 是否重新載入
- canonical state 是否回到預期初始值
- memory summary 是否未被上一 case 污染

---

## 20. 待確認問題

1. Tier 2 / Tier 3 bucket 是否要在 v1 就補滿
2. 哪些 bucket 應先從 real-derived replay 開始
3. 是否要額外建立 provider-failure benchmark bucket
