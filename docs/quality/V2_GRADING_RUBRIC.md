# V2 Grading Rubric

## 目的

本文件定義 **V2 的 whole-product grading rubric**。

它的角色是：

- 把 `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md` 的 capability families，轉成可實際判定的 grading axes
- 把 `V2_FAILURE_TAXONOMY.md` 的 failure families，轉成 hard-fail / major / moderate / minor 的評分規則
- 為下游文件與流程提供共同評分標準：
  - bundle eval packs
  - replay packs
  - founder human review
  - production regression triage
  - ChatGPT / LLM baseline 對照評比

它回答：

- 一個案例要用哪些維度來判斷 pass / fail
- 哪些失敗一出現就直接 fail
- 哪些失敗可以降級為 major / moderate / minor
- functional correctness 與 response quality 應如何分層評估
- founder review / ChatGPT baseline / LLM judge 應該放在 grading pipeline 的哪一層

它不回答：

- 單一案例的 oracle 常數
- 單一 bundle 的具體 case 清單
- 單一模型 prompt 如何寫
- 單一 runner 如何實作

---

## 關係說明

### 與 `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md` 的關係

- capability lattice 定義「評什麼能力」
- 本文件定義「這些能力怎麼評」

### 與 `V2_FAILURE_TAXONOMY.md` 的關係

- failure taxonomy 提供失敗類別 vocabulary
- 本文件定義這些失敗類別如何影響 pass / fail / score

### 與 bundle eval packs 的關係

- bundle eval packs 應直接引用本 rubric 的 hard-fail / scoring rules
- bundle eval packs 只需要補本 bundle 的 case-level oracle 與 expected behavior

---

## 設計原則

1. **先 functional，後 quality**
   - 先判定功能與 product truth 是否成立
   - 功能層沒過，不進 quality 層

2. **Product-truth-first**
   - 以 shared product objects、proposal boundary、chat/UI shared truth 為優先
   - 不是以答案文字表面像不像 ChatGPT 為優先

3. **Outcome-first, not path-first**
   - 主要評 user-visible outcome 與 committed truth
   - 不以 incidental tool order 當主要評分依據

4. **Failure-family-aware**
   - 每個 fail 都應盡量落到 failure taxonomy，而不是只寫 vague notes

5. **Current-wave 深評，later-wave 先保留 rubric 骨架**
   - current-wave families 要有較細 rubric
   - later-wave families 可先保留 family-level rubric，等 deep spec 補齊後再細化

6. **Human-calibrated**
   - founder review 是最終產品適配度校準，不由 LLM judge 取代

---

## 評分總流程

```text
Step 1. Preflight / artifact sanity
Step 2. Functional gate
Step 3. Semantic/product-truth gate
Step 4. Cross-surface consistency gate
Step 5. Proposal / state-boundary gate
Step 6. Response quality gate
Step 7. Founder / baseline comparison review
Step 8. Final verdict + failure-family labeling
```

硬規則：

- Step 2~5 任一層出現 hard-fail，案例直接 fail
- Step 6 不得覆蓋 Step 2~5 的 fail
- Step 7 只做 quality calibration，不得把已 fail 的 functional case 拉回 pass

---

## Verdict 等級

### PASS
- 所有 hard-fail gates 通過
- 無 P0 failure family
- 若有 P1/P2/P3 問題，仍在該案例可接受門檻內

### SOFT_PASS
- functional 與 product truth 成立
- 有 1 個以上明顯 quality 問題，或有 P1/P2 缺陷但未達 blocker
- 可暫時保留，但應列入優化 backlog 或 regression observation

### FAIL
- 任一 hard-fail gate 失敗
- 或出現 P0_blocker
- 或出現使 journey 主體行為無法成立的 P1_major

### NOT_EVALUABLE
- 缺 trace、缺 oracle、缺 required artifact、環境不完整
- 這不是 pass，也不是 fail；是 evaluation invalid

---

## Severity 對應規則

| Severity | 預設結果 |
|---|---|
| `P0_blocker` | 直接 `FAIL` |
| `P1_major` | 依 bundle 與 journey 決定 `FAIL` 或 `SOFT_PASS`，默認傾向 fail on P0 journeys |
| `P2_moderate` | 可 `SOFT_PASS`，需記錄優化 |
| `P3_minor` | 通常仍可 `PASS`，但需記錄 polish notes |

補充：
- 若同一案例有多個 P1，通常升級為 `FAIL`
- 若 P2 影響 founder fit 且反覆出現，可 promote 為 blocking regression

---

## Hard-Fail Gates

以下類型一旦出現，通常直接 fail：

1. **shared truth fail**
   - chat / UI / later query / trace 之間真相不一致

2. **wrong committed state mutation**
   - draft / proposal 被當 committed
   - 或 committed state 沒有更新到位

3. **wrong-thread / wrong-target mutation**
   - 補充 attach 錯 thread
   - correction 改壞 unrelated item

4. **dishonest degradation**
   - 缺 body plan 仍假裝知道剩餘熱量
   - 不確定時假裝 exact

5. **missing critical artifact**
   - bundle claim pass 但無 trace / runner evidence

6. **journey-breaking behavior**
   - 本應 clarify 卻停止
   - 本應 commit 卻沒 commit
   - rescue 應 proposal-first 卻直接套用 committed overlay

---

## Scoring Axes

每個案例可沿以下 6 個軸評估：

| Axis ID | Axis | Layer | Typical Range |
|---|---|---|---|
| A1 | Functional Correctness | hard gate | pass/fail |
| A2 | Semantic / Product-Truth Correctness | hard gate | pass/fail |
| A3 | Cross-Surface Consistency | hard gate | pass/fail |
| A4 | State Boundary Correctness | hard gate | pass/fail |
| A5 | Response Quality | scored | 0-3 |
| A6 | Product Fit / Founder Fit | scored | 0-3 |

建議總分：
- hard gates 全過後，A5 + A6 作為 quality subscore
- quality subscore 不是是否通過的唯一依據，但可用於排序、比較、回歸監控

---

## A1. Functional Correctness

### 定義
案例最基本的功能性行為是否成立。

### 檢查重點
- 該問有問、該答有答
- 該 commit 有 commit，該不 commit 時沒 commit
- 該建立 object / 更新 state 有發生
- 該出現的 UI 變化有出現

### Fail 條件
- 任何使 journey 主體行為無法成立的功能錯誤

### 常見對應 failure families
- `FAM-BOOT`
- `FAM-THREAD`
- `FAM-CLARIFY`
- `FAM-CORR`
- `FAM-SYNC`

---

## A2. Semantic / Product-Truth Correctness

### 定義
是否維持產品語義與 shared product objects 的正確關係。

### 檢查重點
- `meal_thread` 是否被正確理解為 primary intake object
- `day_budget_ledger` 是否為剩餘 / 超標真相來源
- `body_plan` / `proposal` / `proactive_trigger` 是否沒有被混用
- 是否誠實處理 uncertainty / degraded mode

### Fail 條件
- proposal 與 committed state 邊界破壞
- no-plan 時假裝有 plan
- false exactness
- channel-specific truth fork

### 常見對應 failure families
- `FAM-GROUND`
- `FAM-STATE`
- `FAM-CHANNEL`

---

## A3. Cross-Surface Consistency

### 定義
chat、UI、later query、trace 是否反映同一組產品真相。

### 檢查重點
- chat 數字 = UI 數字
- correction 後 query 與 UI 一致
- overshoot 說法與 ledger 真相一致
- onboarding / fallback 情境各 surface 不矛盾

### Fail 條件
- 任一 user-visible 數字不一致
- sidecar / trace 與實際 state 明顯不符

### 常見對應 failure families
- `FAM-SYNC`
- `FAM-TRACE`
- `FAM-CAL`

---

## A4. State Boundary Correctness

### 定義
proposal、draft、negotiation、accepted、committed 之間的 state boundary 是否正確。

### 檢查重點
- clarify draft 不應進 committed truth
- rescue / calibration proposal 未接受前不應生效
- accepted 後應正確轉 committed / overlay
- correction 應建立正確 lineage / supersede 狀態

### Fail 條件
- proposal 當 committed
- committed 當 draft
- accepted 後未反映
- correction lineage 消失

### 常見對應 failure families
- `FAM-STATE`
- `FAM-CORR`
- `FAM-RESCUE`
- `FAM-CAL`

---

## A5. Response Quality（0-3）

只在 A1~A4 通過時評估。

### 3 = excellent
- 回答精簡但完整
- uncertainty 表達得當
- clarify 問得具體
- proposal wording 清楚自然
- 不像 generic essay

### 2 = acceptable
- 功能成立
- 有些冗長、保守或 wording 稍硬，但不妨礙產品使用

### 1 = weak
- 功能成立，但回覆明顯不自然、太長、太短、或 next step 不清楚
- founder 可能會覺得「能用但不像產品」

### 0 = unacceptable
- 雖然功能表面成立，但文字品質嚴重影響可用性或信任
- 通常伴隨 `FAM-UX-01` ~ `FAM-UX-05`

### 常見對應 failure families
- `FAM-UX`

---

## A6. Product Fit / Founder Fit（0-3）

這一軸主要由 founder / human review 校準。

### 3 = strong product fit
- 很像產品本身的語氣與節奏
- 在 chat-first 場景下自然
- 比 generic assistant 更符合產品目標

### 2 = acceptable fit
- 大致符合產品感
- 仍有 generic assistant 味道，但不嚴重

### 1 = poor fit
- 功能成立，但整體不太像這個產品
- proposal / rescue / calibration 的互動節奏不對

### 0 = off-product
- 內容雖可理解，但產品人格、互動節奏、對話設計完全失焦

---

## Capability-Family-Specific Rubric

以下是 family-level 重點。bundle eval 可只引用當前 family 相關段落。

## CF1 / F1 Plan Bootstrap & Fallback Rubric

### Hard-pass條件
- onboarding 後 `body_plan` / `day_budget_ledger` truth 建立成功
- 無 onboarding 時，budget answer 誠實降級
- chat / UI 對目標數字一致

### Hard-fail 對應
- `FAM-BOOT-01`
- `FAM-BOOT-02`
- `FAM-BOOT-04`

### Quality 檢查
- fallback 引導是否清楚、不中斷使用者
- onboarding result explanation 是否讓使用者理解目標從哪裡來

---

## CF2 / F2 Meal Thread Resolution Rubric

### Hard-pass條件
- 正確建立或延續 `meal_thread`
- clarify 模式正確
- exact / estimate / range honesty 正確
- correction 不污染 unrelated truth
- commit 時機正確

### Hard-fail 對應
- `FAM-THREAD-01`
- `FAM-THREAD-03`
- `FAM-THREAD-04`
- `FAM-CLARIFY-01`
- `FAM-CLARIFY-03`
- `FAM-GROUND-01`
- `FAM-CORR-01`
- `FAM-CORR-04`

### Quality 檢查
- clarify 問題是否高資訊密度
- estimate wording 是否保留正確 uncertainty
- correction acknowledgement 是否自然、具體

---

## CF3 / F3 Budget & Cross-Surface Sync Rubric

### Hard-pass條件
- ledger 更新正確
- chat / UI / later query 一致
- overshoot truth 一致
- degraded mode 一致

### Hard-fail 對應
- `FAM-SYNC-01`
- `FAM-SYNC-02`
- `FAM-SYNC-03`
- `FAM-STATE-02`

### Quality 檢查
- overshoot explanation 是否精準但不責備
- remaining budget explanation 是否清楚

---

## CF4 / F5 Body Observation & Calibration Rubric

### Hard-pass條件
- new body observation 可跨 surface 讀取
- calibration proposal 只在資料充分時出現
- confirmed calibration 才改變 committed truth

### Hard-fail 對應
- `FAM-CAL-02`
- `FAM-CAL-04`
- `FAM-SYNC-01`

### Quality 檢查
- trend explanation 是否合理
- calibration proposal 是否像協作，不像強制命令

---

## CF5 / F4 Rescue & Proposal Negotiation Rubric

### Hard-pass條件
- rescue 以 proposal-first 出現
- rescue 不嵌在 intake reply 裡
- accept / reject / complaint interpretation 正確
- accepted overlay 正確生效

### Hard-fail 對應
- `FAM-STATE-01`
- `FAM-RESCUE-02`
- `FAM-RESCUE-04`

### Quality 檢查
- wording 是否 future-oriented
- 是否避免 blame / punishment tone

---

## CF6 / Recommendation & Preference Learning Rubric

### Hard-pass條件
- recommendation 與 budget / body plan 不衝突
- explicit preference 被讀到
- intake handoff 成功

### Hard-fail 對應
- `FAM-REC-01`
- `FAM-REC-04`
- `FAM-STATE-01`（若 recommendation proposal wrongly committed）

### Quality 檢查
- recommendation 是否少而精
- explanation 是否能讓人採取行動

---

## CF7 / Proactive Triggering Rubric

### Hard-pass條件
- trigger explainable
- suppression / cooldown respected
- proactive message 有明確 handoff

### Hard-fail 對應
- `FAM-PROACTIVE-02`
- `FAM-PROACTIVE-03`

### Quality 檢查
- proactive timing 是否自然
- 是否有被打擾感

---

## CF8 / Cross-Channel / Entry Modality Rubric

### Hard-pass條件
- channel / modality 不得創造平行真相
- image / voice / quick action 應落入共享 product object workflow

### Hard-fail 對應
- `FAM-CHANNEL-01`
- `FAM-CHANNEL-02`

### Quality 檢查
- 不同入口雖有差異，但 user 感覺仍像同一產品

---

## CF9 / Trace, Explainability & Governance Rubric

### Hard-pass條件
- required artifact 存在
- request / trace / bundle result 可連結
- state transition 可審計

### Hard-fail 對應
- `FAM-TRACE-01`
- `FAM-TRACE-02`

### Quality 檢查
- trace 是否能幫助 replay 與 regression triage
- not merely logs exist, but evidence is usable

---

## 評分模板（Case-Level）

建議每個 case 最後輸出類似：

```yaml
case_id:
journey:
capability_families:
verdict: PASS | SOFT_PASS | FAIL | NOT_EVALUABLE
hard_gates:
  functional_correctness: pass | fail
  semantic_correctness: pass | fail
  cross_surface_consistency: pass | fail
  state_boundary_correctness: pass | fail
quality_scores:
  response_quality: 0-3
  founder_fit: 0-3
failure_labels:
  primary_failure_family:
  secondary_failure_families:
severity:
notes:
```

---

## Founder / Human Review Layer

### 角色
- 校準產品適配度
- 判斷這是否像真正的產品，而不是 generic assistant
- 決定某些 recurrent P2 是否應提升為 blocking regression

### Founder Review 問題建議
1. 這個回覆是否像產品本身，而不是通用 AI？
2. 在這個 journey，最關鍵的事情有沒有做好？
3. 若你是真實使用者，你會不會因為這個回覆失去信任？
4. 這個案例應不應升級成 regression gate？

### Founder Review 輸出建議
```yaml
founder_review:
  pass: true | false
  founder_fit: 0-3
  should_promote_to_regression: true | false
  notes:
```

---

## ChatGPT / LLM Baseline Comparison Layer

### 定位
- baseline / comparison aid
- 不是 primary truth
- 不可覆蓋 hard-gate 結果

### 適用場景
- A5 / A6 quality comparison
- response brevity / naturalness / product-fit contrast
- alternative wording exploration

### 不適用場景
- proposal / committed boundary correctness
- chat/UI same-number truth
- whether state mutation is legal

### Pairwise 標記建議
```yaml
baseline_comparison:
  compared_against: chatgpt
  result: win | tie | lose
  reasons:
    - brevity
    - completeness
    - uncertainty_expression
    - product_fit
```

---

## Current-Wave 評分建議

current-wave（F1/F2/F3/CF9）建議採：

### Gate 1 — Functional / Semantic Gate
- A1~A4 全過，才進下一層

### Gate 2 — Quality Gate
- A5 >= 2
- founder_fit >= 2（若有人審）

### Gate 3 — Bundle Readiness
- P0 cases 全過
- 無未解決 `P0_blocker`
- trace / artifact 完整

---

## Later-Wave 評分建議

later-wave families 在 deep spec 未完成前，可先使用 family-level rubric，不強求 sub-capability 細分，但仍需遵守：
- hard-fail gates
- state boundary correctness
- shared truth correctness
- proposal separation

---

## 如何用於 Regression 決策

### 必升級為 regression gate
- 所有 `P0_blocker`
- 重複出現的 `FAM-SYNC-01`
- 重複出現的 `FAM-THREAD-01`
- 重複出現的 `FAM-STATE-01/02`
- founder 明確標記 `should_promote_to_regression = true`

### 可先觀察
- 單次出現的 `P2_moderate`
- 純 wording polish 的 `P3_minor`

---

## Definition of Done for This Document

本文件完成，表示：

- whole-product grading axes 已明確
- hard-fail 與 soft-quality 分層已明確
- capability families 與 failure families 之間已有穩定評分關係
- founder review / ChatGPT baseline / LLM judge 的角色已明確分層
- bundle eval packs 可直接引用本 rubric 建立 case-level verdict format

本文件完成，不表示：

- 所有 family-level rubric 都已深到 sub-capability 層
- 所有 detectors 都已自動化
- founder calibration 已完成

---

## 下一步

1. 只對 current-wave（F1/F2/F3/CF9）建立 deep capability spec
2. 為 bundle eval packs 加入：
   - hard gate coverage
   - failure-family coverage
   - founder review output fields
3. 建立 tiny golden sets 與 replay triage template

---

## 歷史

- 2026-04-24: v1 初始版本，建立 whole-product grading rubric，供 bundle eval、founder review、baseline comparison、regression triage 使用
