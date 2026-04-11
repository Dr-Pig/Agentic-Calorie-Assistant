# L5A Eval Spec

## 1. 目的

這份 spec 定義系統的 evaluation framework。

它要回答：

- 我們如何做 `pass-level / flow-level / cross-flow / end-to-end` 評估
- 各 flow 要看哪些核心指標
- 哪些 trace 欄位是 eval 必需品
- manual correction 與真實使用回饋如何回流
- tool fallback、proposal、safety gate 如何進入評估

它不回答：

- benchmark case 本身怎麼建
- safety policy 的最終法律邊界

這兩者分別由 `L5B` 與 `L5C` 定義。

---

## 2. Eval Levels

系統至少要有四層評估：

- `pass-level eval`
- `flow-level eval`
- `cross-flow integration eval`
- `end-to-end product eval`

---

## 3. Eval Dimensions

所有 flow 至少都要看這幾類指標：

- correctness
- usefulness
- friction
- consistency
- latency / token cost
- safety outcome
- downgrade quality

---

## 4. Flow-Specific Eval

### 4.1 Intake

- meal linking accuracy
- correction handling
- commit readiness quality
- kcal usefulness
- conservative fallback quality when tools fail
- food detection recall should be weighted above moderate kcal deviation

### 4.2 Recommendation

- candidate relevance
- budget alignment
- preference fit
- explicit intake handoff correctness
- fallback quality under missing location / missing retrieval

### 4.3 Calibration

- deficit reality judgment quality
- proposal appropriateness
- operating expenditure usefulness
- intake bias posture usefulness
- logging-quality-first gate correctness

### 4.4 Rescue

- rescue appropriateness
- horizon selection quality
- escalation timing quality
- low-friction recovery quality

---

## 4A. Founder-Fit Eval Posture

v1 的 primary eval 應以 founder-fit 為主，而不是一開始就追求泛化最優。

### 4A.1 primary eval target

v1 primary eval 應優先衡量：

- founder 的高頻飲食情境
- founder 的常見說法與 correction 模式
- founder 的 recommendation 體感
- founder 的 rescue / calibration 可執行性

### 4A.2 secondary sanity target

即使 v1 以 founder-fit 為主，仍應保留 generalized sanity layer，用來防止：

- 過度 overfit founder 飲食習慣
- 對安全與 cross-flow 案例視而不見
- recommendation / correction 在非 founder 語境下完全失效

### 4A.3 eval weighting guidance

在 intake early-stage eval 中：

- `food detection recall` 應高於中度熱量誤差
- 但 recall 優先不等於允許 hallucinated food items

---

## 5. Trace Requirements

所有 eval 都必須依賴結構化 trace，而不是只看自然語言輸出。

至少要有：

- pass inputs / outputs
- selected evidence summary
- token usage
- latency
- commit / no-commit decision
- proposal / no-proposal decision
- safety gate result
- fallback mode

---

## 6. Feedback Loop / Review Signal

使用者手動修正系統輸出，不應一律被當成負樣本；v1 應先視為 `review_signal`。

### 6.1 review-signal sources

- UI 手動修改熱量或份量
- 對話中修正已提交餐點
- recommendation 被明確拒絕且附理由
- calibration / rescue proposal 被拒絕且附理由

### 6.2 review-signal classes

每筆 review signal 應至少被分類到以下其中一類：

- `likely_model_error`
- `user_preference_override`
- `logging_refinement`
- `time_or_scope_correction`
- `ambiguous_case_relabel`

### 6.3 eval usage

- repeated `likely_model_error` signals 應觸發 prompt / retrieval / tool-policy review
- corrected production traces 應升級成 regression candidates
- `user_preference_override` 不應直接算成模型品質失敗

---

## 7. Trace Envelope Policy

### 7.1 JSON-first serialization

所有 eval artifact、runtime trace、tool trace、pass output、benchmark result log，應統一採結構化 JSON，或可穩定序列化成 JSON 的 schema。純文字 log 不應成為唯一分析來源。

### 7.2 required trace fields

eval 可見的 `trace_envelope` 至少應包含：

- `trace_id`
- `flow_type`
- `pass_type`
- `recorded_at`
- `timezone`
- `local_date`
- `user_local_time`
- `tool_calls[]`
- `tool_reason[]`
- `fallback_mode`
- `commit_decision`
- `proposal_decision`
- `safety_gate_result`

### 7.3 retention policy

v1 預設：

- 全量 `trace_envelope` 保留 `30 days`
- decision metadata / aggregate metrics / eval outputs 長期保留

### 7.4 de-identification for retained traces

進入長期 retention 或共享分析集前，trace 應先遮罩或去識別化至少以下資訊：

- 姓名
- 精細私人位置
- 直接聯絡資訊
- 其他不必要的自由文字 PII

---

## 8. Human Eval / Human Review in Eval

### 8.1 human eval 應聚焦的情況

- ambiguity-heavy multi-turn cases
- proposal tone / explanation quality
- recommendation felt usefulness
- rescue 可執行性

### 8.2 不必每筆都 human review

v1 不要求每次日常執行都做人工審核；人工審核應集中在：

- new model / prompt rollout
- repeated regression cluster
- safety-near misses
- user-trust damage cases

---

## 9. Score Shape

不同 eval 維度不應共用單一計分方式。v1 至少應支持以下 score shape：

### 9.1 binary pass/fail

適用於：

- hard guard 是否被違反
- commit legality
- proposal legality
- required schema presence

### 9.2 partial credit

適用於：

- recommendation 候選相關性
- calibration explanation quality
- rescue option appropriateness

### 9.3 rubric score

適用於：

- human eval 的 explanation / tone / usefulness
- cross-flow 體感品質

### 9.4 ranked outcome

適用於：

- recommendation top-pick quality
- rescue / calibration option ordering

### 9.5 scoring rule

每個 eval item 都應明確標註：

- `score_type`
- `pass_condition`
- `hard_fail_override`

---

## 10. Pass-Level Oracle

pass-level eval 不應只看最終回答，必須對應到各 pass 的合法 oracle。

### 10.1 `task_meal_link_pass`

至少評估：

- target meal / thread linkage
- boundary judgment
- occurred-at interpretation
- split-into-intake-units correctness

### 10.2 `decision_pass`

至少評估：

- next action legality
- clarify blocking correctness
- tool-plan appropriateness
- fallback choice legality

### 10.3 `nutrition_resolution_pass`

至少評估：

- resolution payload completeness
- kcal / item structure usefulness
- commit readiness correctness
- bias posture usage legality

### 10.4 `final_response_pass`

至少評估：

- wording correctness
- follow-up restraint
- no unauthorized semantic change
- no added numbers / no added boundary change

### 10.5 pass-level oracle rule

如果前一 pass 已錯，後一 pass 的好文案不能掩蓋上游失敗。

---

## 11. Offline / Online Eval Split

v1 應至少區分三類 eval：

### 11.1 offline benchmark eval

以 `L5B` benchmark case 為主，適合：

- prompt / runtime regression
- guardrail verification
- deterministic gate verification

### 11.2 trace-derived eval

以真實 runtime trace 與 review signal 為主，適合：

- correction replay
- fallback quality review
- repeated model-error cluster detection

### 11.3 online product eval

以產品使用結果為主，適合：

- adherence-related outcome proxy
- user trust / correction rate
- recommendation acceptance / rejection behavior

### 11.4 split rule

- 新 prompt / runtime 變更先過 offline
- 真實上線後再看 trace-derived
- 產品策略調整才主要看 online

---

## 11A. Abstain Policy in Eval

eval 不應把「低信心但有用的 provisional response」與「空白回應」混為一談。

### 11A.1 preferred policy

v1 預設應採：

- abstain from commit when necessary
- not necessarily abstain from response

### 11A.2 acceptable low-confidence behavior

當信心不足時，可接受的行為包括：

- 回 provisional estimate
- 明示不確定性
- 要求更多資訊
- 不寫入 canonical state

### 11A.3 unacceptable abstain behavior

以下行為不應被視為高品質：

- 在可提供有用 provisional guidance 時直接回空
- 用模糊語氣掩蓋其實已 no-commit 的狀態

---

## 12. Human Eval Rubric

human eval 不應只寫自由評論，應至少有可重複使用的 rubric。

### 12.1 minimum rubric dimensions

- correctness
- helpfulness
- clarity
- friction
- trustworthiness

### 12.2 suggested scale

v1 建議採 `1-5` 分制，並保留：

- `critical_note`
- `would_block_release`

### 12.3 human-eval priority cases

優先給 human eval 的案例：

- multi-turn ambiguity
- proposal explanation
- rescue tone / blame risk
- recommendation felt usefulness
- cross-flow sync oddity

---

## 13. Release Gate

eval 最後要服務 release decision，因此 v1 應至少有基本 release gate。

### 13.1 minimum release conditions

- Tier 1 benchmark buckets 不得明顯退步
- safety-critical buckets 不得新增 `hard_fail`
- correction replay 不得退步
- tool-failure downgrade 不得違反 policy

### 13.2 monitored-but-not-blocking metrics

以下可先作觀察，不一定直接 block release：

- token cost 小幅上升
- latency 小幅上升
- recommendation personalization 波動

### 13.3 automatic block conditions

任一情況應 block release：

- 新增 `hard_fail`
- proposal / commit boundary 被破壞
- below-floor caloric posture 可被產出
- implicit meal-intent / pending intake state 被建立

---

## 13A. KPI Pass Thresholds

v1 應有可執行的最低通過線，但只定到足以做 release gating 的程度，不追求過度精細。

### 13A.1 Tier 1 flow KPI baseline

- Intake：
  - `food detection recall` 應至少達到 `0.90`
  - `commit-critical correctness` 應至少達到 `0.95`
  - `correction handling correctness` 應至少達到 `0.90`
- Recommendation：
  - `candidate legality / hard-constraint compliance` 應至少達到 `0.95`
  - `top-pick usefulness` 可先採 human rubric 平均 `>= 4.0 / 5`
- Calibration：
  - `proposal gate correctness` 應至少達到 `0.90`
  - `insufficient-data abstain correctness` 應至少達到 `0.95`
- Rescue：
  - `guardrail compliance` 應至少達到 `0.98`
  - `recommended family correctness` 應至少達到 `0.90`

### 13A.2 safety-coupled KPI rule

- 任何 safety-coupled KPI 若低於門檻，不得以其他高分抵銷
- `hard_fail` 相關 KPI 一律視為 blocking KPI
- `soft_fail` 可進入 monitored-but-not-blocking 區，但不得連續兩個 release cycle 退步

### 13A.3 founder-fit weighting

- founder-fit dataset 上，`food detection recall` 與 `correction correctness` 權重高於中度 kcal 誤差
- general-sanity dataset 上，應維持基本泛化，不可因 founder-fit 最佳化而明顯退步

---

## 13B. Human Eval Sampling Policy

human eval 應作為高價值抽驗，而不是全量人工評讀。

### 13B.1 v1 sampling baseline

- 每次 release candidate：
  - Tier 1 benchmark bucket 至少抽 `20%` 做 human eval
  - safety-critical bucket 至少抽 `50%`
  - cross-flow stress set 至少抽 `25%`
- founder-fit golden set 應保證每次 release 至少抽 `10` 題
- 新增或最近修復的 regression case，若屬高風險，應優先進 human eval 抽樣池

### 13B.2 mandatory human-review cases

以下情況不得完全跳過 human eval：

- 新 prompt / runtime path 首次上線
- calibration proposal gate 有明顯變更
- rescue policy guardrail 有明顯變更
- recommendation handoff 到 intake 的邊界有變更
- 過去 30 天內曾造成 user-trust damaging issue 的 case family

### 13B.3 adaptive sampling

- 若某 bucket 連續兩個 release cycle 穩定通過，可適度下調抽樣比例
- 若某 bucket 出現新 regression / repeated soft-fail，下一輪應自動上調抽樣比例

---

## 13C. Online / Offline Boundary Rule

v1 應明確區分 offline benchmark、trace-derived eval、與 online product eval 的角色。

### 13C.1 offline-first release rule

- 所有 prompt / runtime / retrieval policy 變更，必須先通過 offline benchmark eval
- 若 offline 未過，不得用 online 指標「先上再看」替代
- offline 是 release 的必要條件，但不是充分條件

### 13C.2 trace-derived eval role

- trace-derived eval 用於發現：
  - prompt drift
  - tool fallback 異常
  - correction / manual review signal 聚集
  - founder-fit 與 general-sanity 之間的落差
- trace-derived eval 應作為 regression 升級與 benchmark 補題來源

### 13C.3 online eval role

- online eval 主要觀察：
  - logging continuation / retention proxy
  - recommendation acceptance / dismissal
  - rescue acceptance / rejection
  - correction rate
  - user-trust complaints
- online 指標可影響優先級排序與後續優化方向
- online 指標不應單獨覆蓋 offline safety 結論

### 13C.4 override rule

- 若 online product metrics 明顯改善，但 offline safety / benchmark 退步，仍以 offline safety 為準
- 若 offline 全過，但 online 出現連續 user-trust damage，應暫停擴大 rollout 並進 trace review

---

## 14. 與其他 specs 的關係

- benchmark case 的來源與結構由 [`docs/quality/L5B_BENCHMARK_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5B_BENCHMARK_SPEC.md) 定義
- safety fail / guardrail 邊界由 [`docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5C_SAFETY_GUARDRAIL_SPEC.md) 定義
- trace envelope 與 runtime 輸出型別應與 `L3.x` flow specs 對齊
- founder-fit / founder-golden / general-sanity dataset 分層應與 `L5B` 對齊

---

## 15. 後續可再細化的項目

- recommendation `top-pick usefulness` 是否需要再拆成 budget fit / preference fit / actionability 三個子分數
- human eval rubric 是否需要依 founder-fit 與 general-sanity 各自微調
- online 指標是否要再補 cohort / rollout-stage 分層
