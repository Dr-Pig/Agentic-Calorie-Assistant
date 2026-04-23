# V2 Wave 1 Capability Micro-Suites

## 目的

本文件定義 **Wave 1 的 capability micro-suites 設計稿**。

它的角色是：

- 將 Wave 1 的 system capabilities 拆成可分測、可腳本驗證、可對位到失敗分類與評分規則的 micro-suites
- 讓 implementation 不只依賴 bundle-level end-to-end 驗收
- 幫助 coding agent 以 divide-and-conquer 的方式建置，而不是為了讓 Bundle 1 / 2 變綠做局部 patch
- 為後續 runner、自動化腳本、fixture、golden cases 提供結構

它回答：

- Wave 1 應該拆成哪些 micro-suites
- 每個 micro-suite 主要驗什麼 capability contract
- 哪些可以直接腳本驗證，哪些需要少量 judge / founder review
- 這些 micro-suites 與 Bundle 1 / Bundle 2 / benchmark v1/v2 / turn2 replay 的關係是什麼
- coding agent 應先過哪些 micro-suites，再跑哪些較大的驗收包

它不回答：

- 單一 micro-suite 的最終 runner 實作方式
- 每個測試案例的完整 fixture 值
- 每個能力的最終 prompt 逐字稿

---

## 關係說明

### 上游依據

1. `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`
2. `V2_FAILURE_TAXONOMY.md`
3. `V2_GRADING_RUBRIC.md`
4. `V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`
5. `V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md`

### 下游使用

- capability-specific scripts / runners
- benchmark / replay remapping
- bundle acceptance readiness checks
- regression promotion

---

## 核心原則

1. **Micro-suite 驗 system capability，不驗整個產品幻覺**
   - 每個 micro-suite 盡量只對一個核心 contract 負責

2. **能 deterministic 就 deterministic**
   - 優先腳本可驗證
   - 不要一開始就用 LLM judge 評 system contracts

3. **先過 micro-suites，再跑 bundle acceptance**
   - bundle 不是 build order；micro-suites 才是 divide-and-conquer 施工順序

4. **每個 suite 都要能映射到 failure taxonomy**
   - suite fail 時能快速知道自己屬於哪個 failure family

5. **優先測 contract，不優先測 wording**
   - wording 層放到後面的 response quality / founder fit

6. **避免把 tool order 當主驗收標準**
   - 但 evidence-path selection 本身是 product-critical capability，應單獨測

---

## Wave 1 測試分層總覽

### Layer A — Capability Micro-Suites
角色：system-capability contract tests

### Layer B — Bundle Acceptance
角色：journey-level functional acceptance

### Layer C — Replay / Benchmark Functional Layer
角色：realism / regression / anti-overfit layer

### Layer D — Quality / Founder Fit
角色：產品感、語氣、簡潔度、baseline comparison

硬規則：
- Layer A 不穩時，不應反覆 patch Layer B
- Layer B fail 時，先定位回哪個 Layer A suite
- Layer D 不可覆蓋 Layer A / B 的 functional fail

---

## Wave 1 Micro-Suites 總覽

| Suite ID | Suite Name | Primary Capability | Primary Fail Families | Main Verification Type |
|---|---|---|---|---|
| MS1 | Intent / Thread Resolution | F2.1 | FAM-THREAD | deterministic |
| MS2 | Clarify Mode Selection | F2.2 | FAM-CLARIFY | deterministic |
| MS3 | Evidence Path Selection | F2.3b | FAM-GROUND | deterministic |
| MS4 | Tavily Retrieval Usage | F2.3b / F2.3 | FAM-GROUND | deterministic + artifact |
| MS5 | Evidence Normalization | F2.3 | FAM-GROUND | deterministic |
| MS6 | Estimate / Grounding Synthesis | F2.3 | FAM-GROUND | mixed |
| MS7 | Draft vs Commit Boundary | F2.4 | FAM-THREAD, FAM-STATE | deterministic |
| MS8 | Correction Integrity & Versioning | F2.5 | FAM-CORR | deterministic |
| MS9 | Ledger Mutation & Overshoot Truth | F3.1 / F3.2 | FAM-SYNC | deterministic |
| MS10 | Macro Visibility Policy | F3.3 | FAM-GROUND, FAM-SYNC | deterministic |
| MS11 | Same-Truth Read Path | F3.4 | FAM-SYNC, FAM-CORR | deterministic |
| MS12 | Trace / Artifact Contract | T9.1 / T9.2 | FAM-TRACE | deterministic |
| MS13 | Intake Response Realization | F2.6 | FAM-UX, FAM-RESCUE-01 | mixed / quality-lite |
| MS14 | No-Plan Fallback Honesty | F1.2 | FAM-BOOT, FAM-SYNC | deterministic |

註：
- `F2.3b Evidence Path Selection` 為建議新增到 Wave 1 spec 的子能力名稱
- `Estimate / Grounding Synthesis` 需要 LLM，但其輸入輸出 contract 仍應盡量結構化

---

## Suite 詳細定義

## MS1 — Intent / Thread Resolution

### 目標
驗證 manager / intake layer 是否能正確區分：
- new meal
- same-meal followup
- correction
- info query

### Primary capability
- F2.1 Intake Routing / Thread Intent Detection

### 必驗 contract
- same-meal 補充優先 attach existing thread
- correction 不得誤判成新 meal
- query 不得誤判成 meal mutation

### 典型案例
- 「我喝了一杯珍珠奶茶」→ new meal
- 「半糖大杯」→ same-meal followup
- 「剛剛豆漿我記錯了」→ correction
- 「我今天吃了多少？」→ info query

### 驗證方式
- deterministic
- 檢查 target thread / action type / no unintended mutation

### 主要 failure families
- `FAM-THREAD-01`
- `FAM-THREAD-02`
- `FAM-THREAD-03`

---

## MS2 — Clarify Mode Selection

### 目標
驗證系統是否正確區分：
- `direct_commit`
- `estimate_with_followup`
- `clarify_before_estimate`

### Primary capability
- F2.2 Clarify Mode Selection

### 典型案例
- 「全糖大杯珍珠奶茶」→ direct commit / direct estimate
- 「珍珠奶茶」→ estimate_with_followup
- 「我剛吃了我媽做的家常菜」→ clarify_before_estimate
- 「炒青菜和白飯一碗」→ direct commit

### 驗證方式
- deterministic
- 檢查 clarify_mode / provisional range allowed / followup_required

### Hard-fail indicators
- 家常菜在未知組成下直接給 kcal
- 珍珠奶茶在資訊不足時只問不給範圍

### 主要 failure families
- `FAM-CLARIFY-01`
- `FAM-CLARIFY-02`
- `FAM-CLARIFY-03`
- `FAM-CLARIFY-04`

---

## MS3 — Evidence Path Selection

### 目標
驗證系統是否能正確決定：
- exact DB
- generic DB / prior
- Tavily retrieval
- ask user / clarify
- heuristic fallback

### Primary capability
- F2.3b Evidence Path Selection

### 原則
這個 suite **不驗 tool order 美學**，而是驗：
- evidence-path 選錯會不會直接導致 product truth 風險

### 典型案例
- 明確品牌連鎖品項 → exact DB
- generic food with sufficient anchors → generic DB
- known store dish not in DB → Tavily candidate retrieval
- homemade ambiguous dish → ask user / clarify
- evidence不足但可估 → heuristic fallback with uncertainty

### 驗證方式
- deterministic
- 檢查 `selected_evidence_path`
- 檢查是否違反 obvious routing rules

### 主要 failure families
- `FAM-GROUND-06 Wrong evidence-path selection` *(建議新增)*
- `FAM-GROUND-02`
- `FAM-CLARIFY-03`

---

## MS4 — Tavily Retrieval Usage

### 目標
驗證 Tavily 在 Wave 1 中是否被正確定位為 candidate retrieval，而不是 truth oracle。

### Primary capability
- F2.3b / F2.3

### 驗證重點
- 該查時有查
- 不該查時不查
- query 含關鍵 brand / store / dish anchors
- retrieval artifact 存在
- search 回來後不直接當 final truth

### 典型案例
- 「勝王牛白湯拉麵」exact DB miss → Tavily search candidate lane
- 「我媽做的家常菜」→ 不應 Tavily search，應 clarify
- 「聖王拉麵哪一碗」品牌/店名含糊 → query 應保留可 disambiguate anchors

### 驗證方式
- deterministic + artifact existence
- 檢查：
  - whether Tavily called
  - query shape
  - result packet created
  - no direct snippet-to-truth shortcut

### 主要 failure families
- `FAM-GROUND-06 Wrong evidence-path selection` *(建議新增)*
- `FAM-GROUND-07 Retrieved evidence misclassified` *(建議新增)*

---

## MS5 — Evidence Normalization

### 目標
驗證 exact / generic / Tavily 回來的 evidence 是否能統一轉成 usable packet。

### Primary capability
- F2.3 Grounding / Estimation Posture

### 建議 normalized fields
- source_type
- source_id / source_url
- matched_entity
- serving_basis
- modifiers
- extracted_kcal
- extracted_macros
- identity_confidence
- uncertainty_level
- usable_for_exact / usable_for_anchor / unusable

### 驗證方式
- deterministic
- 檢查 normalized packet 欄位完整性

### 主要 failure families
- `FAM-GROUND-04`
- `FAM-GROUND-07 Retrieved evidence misclassified` *(建議新增)*

---

## MS6 — Estimate / Grounding Synthesis

### 目標
驗證系統在 evidence 已就位後，能否正確輸出：
- exact value
- anchored range
- likely value
- uncertainty posture

### Primary capability
- F2.3 Grounding / Estimation Posture

### 特別說明
這個 suite 是少數會真正依賴 LLM judgement 的核心能力之一。
但仍應盡量結構化驗：
- exactness posture
- range existence
- likely value exists
- uncertainty preserved
- no fake exactness

### 驗證方式
- mixed
- deterministic 檢查 contract
- 少量 rubric / human calibration 檢查 estimate quality

### 主要 failure families
- `FAM-GROUND-01`
- `FAM-GROUND-03`
- `FAM-GROUND-05`

---

## MS7 — Draft vs Commit Boundary

### 目標
驗證 clarify / estimate 結果是否正確停在 draft 或進 committed truth。

### Primary capability
- F2.4 Draft vs Commit Candidacy

### 核心規則
- 資訊不足 → `canonical_commit == false`
- draft 不得進 ledger
- 資訊足夠 → 應 commit，不可無限卡 draft

### 典型案例
- 「珍珠奶茶」第一輪 → draft
- 「半糖大杯」第二輪 → commit
- 「炒青菜和白飯一碗」→ 直接 commit

### 驗證方式
- deterministic
- 檢查 `canonical_commit` / ledger unchanged vs changed

### 主要 failure families
- `FAM-THREAD-04`
- `FAM-STATE-02`

---

## MS8 — Correction Integrity & Versioning

### 目標
驗證 correction 是否：
- 只改 target item
- 建立新 version / supersede relation
- later query 能讀到新 truth

### Primary capability
- F2.5 Correction / Removal / Supersede

### 典型案例
- 豆漿 80 kcal → 150 kcal，牛肉麵不變
- 「豆漿我沒喝」→ remove item，thread 仍存在

### 驗證方式
- deterministic
- 檢查 non-target preservation / new version created / old superseded / ledger propagated

### 主要 failure families
- `FAM-CORR-01`
- `FAM-CORR-02`
- `FAM-CORR-03`
- `FAM-CORR-04`

---

## MS9 — Ledger Mutation & Overshoot Truth

### 目標
驗證 committed intake / correction 是否正確更新 ledger，且 overshoot 由 ledger truth 決定。

### Primary capability
- F3.1 Ledger Mutation
- F3.2 Overshoot Presentation

### 核心規則
- draft 不進 ledger
- commit 才更新 ledger
- overshoot amount 來自 ledger，不由 response layer自算新真相

### 驗證方式
- deterministic
- 檢查 budget delta / overshoot consistency / remaining correctness

### 主要 failure families
- `FAM-SYNC-02`
- `FAM-SYNC-03`
- `FAM-STATE-02`

---

## MS10 — Macro Visibility Policy

### 目標
驗證 `show_macro` 是否遵循 Wave 1 共享真相規則。

### Primary capability
- F3.3 Macro Visibility Policy

### 核心規則
- `canonical_commit == false` → `show_macro == false`
- macro alignment fail → `show_macro == false`
- uncertainty high / identity_confidence low → `show_macro == false`

### 驗證方式
- deterministic
- 檢查 `show_macro`
- 檢查 macro numbers only when allowed

### 主要 failure families
- `FAM-GROUND-05`
- `FAM-SYNC-01`

---

## MS11 — Same-Truth Read Path

### 目標
驗證 correction / commit 後，later query 讀到的是最新 committed truth。

### Primary capability
- F3.4 Same-Truth Read Path

### 典型案例
- correction 後再問「我今天吃了多少？」
- overshoot 後再問 today summary

### 驗證方式
- deterministic
- 檢查 later query numbers = current ledger / meal-thread version truth

### 主要 failure families
- `FAM-SYNC-01`
- `FAM-CORR-04`

---

## MS12 — Trace / Artifact Contract

### 目標
驗證每個 case 是否真的留下足夠 evidence，而不是只讓文字看起來像 pass。

### Primary capability
- T9.1 Request / Artifact Linkage
- T9.2 State Delta Visibility

### 核心規則
- no pass without request-linked artifact
- required observable fields exist
- bundle claim must point to evidence

### 驗證方式
- deterministic
- 檢查 request_id / artifact path / state delta visibility

### 主要 failure families
- `FAM-TRACE-01`
- `FAM-TRACE-02`
- `FAM-TRACE-05 Unearned green via benchmark patching` *(建議新增)*

---

## MS13 — Intake Response Realization

### 目標
驗證 Wave 1 response layer 是否正確呈現 shared truth，而不發明新語義。

### Primary capability
- F2.6 Intake Response Realization

### 核心規則
- 不得把 rescue proposal 塞進 intake reply
- 不得把 draft 說成完整記錄
- 若 `show_macro == false`，不應說具體 macro

### 驗證方式
- mixed / quality-lite
- deterministic 驗 contract
- 少量 human / rubric 驗 wording friction

### 主要 failure families
- `FAM-UX-01`
- `FAM-UX-02`
- `FAM-UX-03`
- `FAM-RESCUE-01`

---

## MS14 — No-Plan Fallback Honesty

### 目標
驗證沒有 active body plan 時，系統是否誠實降級，但仍允許 intake。

### Primary capability
- F1.2 No-Plan Fallback

### 核心規則
- 無 plan 仍可 logging
- 無 plan 不得給 concrete remaining kcal
- 必要時提供 setup guidance

### 驗證方式
- deterministic
- 檢查 intake allowed + budget degraded honestly

### 主要 failure families
- `FAM-BOOT-01`
- `FAM-BOOT-03`
- `FAM-SYNC-04`

---

## 建議建置順序（Micro-Suites First）

### Phase A — Routing & Boundary
先做：
1. MS1 Intent / Thread Resolution
2. MS2 Clarify Mode Selection
3. MS7 Draft vs Commit Boundary
4. MS14 No-Plan Fallback Honesty

理由：
- 這些能力決定大部分後續流程會不會一開始就走歪

### Phase B — Evidence Stack
再做：
5. MS3 Evidence Path Selection
6. MS4 Tavily Retrieval Usage
7. MS5 Evidence Normalization
8. MS6 Estimate / Grounding Synthesis

理由：
- 這些能力是 nutrition path 的核心，但應在 posture / boundary 先穩後再接入

### Phase C — Mutation & Projection
再做：
9. MS8 Correction Integrity & Versioning
10. MS9 Ledger Mutation & Overshoot Truth
11. MS10 Macro Visibility Policy
12. MS11 Same-Truth Read Path
13. MS12 Trace / Artifact Contract
14. MS13 Intake Response Realization

理由：
- 這些能力依賴前面的 routing / evidence / boundary 都先成形

---

## 與 Bundle / Benchmark / Replay 的關係

## Bundle 1 主要依賴
- MS1
- MS7
- MS9
- MS11
- MS12
- MS14

## Bundle 2 主要依賴
- MS2
- MS3
- MS4
- MS5
- MS6
- MS7
- MS8
- MS9
- MS10
- MS11
- MS12
- MS13

## benchmark v1 / v2 建議對位到
- direct commit / exact DB 家族
- generic estimate 家族
- no-plan honesty 家族
- budget sync / later query 家族

## turn2 replay 建議對位到
- same-meal followup
- draft → commit transition
- correction propagation
- thread continuity

---

## 每個 Micro-Suite 建議輸出格式

```yaml
suite_id:
case_id:
primary_capability:
primary_failure_family:
setup_state:
input:
expected_contract:
forbidden_outcomes:
verification_type:
verdict:
notes:
```

### `verification_type` 建議值
- `deterministic`
- `deterministic_plus_artifact`
- `mixed`

---

## 推進規則

### 規則 1
單一 micro-suite 不穩時，不應直接一直 patch Bundle 2。

### 規則 2
若 Bundle 2 fail，應先回映到哪個 micro-suite contract 壞掉。

### 規則 3
若某個 fix 只能讓 bundle case 綠，但對應 micro-suite 沒改善，應視為可疑 patch。

### 規則 4
Tavily 相關修法必須同時檢查：
- path selection
- retrieval artifact
- normalization
- usable vs unusable evidence classification

### 規則 5
MS6 / MS13 即使含 LLM judge，也不得跳過 deterministic contract checks。

---

## 建議最小起步版本（MVP Micro-Suites）

若你要最小可行起步，可先只做：

1. MS1 Intent / Thread Resolution
2. MS2 Clarify Mode Selection
3. MS7 Draft vs Commit Boundary
4. MS8 Correction Integrity & Versioning
5. MS9 Ledger Mutation & Overshoot Truth
6. MS10 Macro Visibility Policy
7. MS12 Trace / Artifact Contract
8. MS14 No-Plan Fallback Honesty

等這些穩了，再擴 MS3 / MS4 / MS5 / MS6 / MS11 / MS13。

---

## 與 Coding Agent 的關係

coding agent 不應只讀 bundle cases。

在進入 Wave 1 implementation 時，應同時閱讀：
- Wave 1 deep capability spec
- execution architecture overview
- micro-suites 設計稿
- bundle eval packs
- failure taxonomy / grading rubric

這樣 agent 才知道：
- build order 先看 system capability
- bundle 只是 acceptance gate
- 不可用 fake green 方式硬 patch

---

## Definition of Done for This Document

本文件完成，表示：

- Wave 1 的 system-capability micro-suites 已完整定義骨架
- 可清楚區分哪些 suite 先建、哪些後建
- 每個 suite 都可映射到 capability family 與 failure family
- Bundle 1 / Bundle 2 / benchmark / replay 已有對位方向

本文件完成，不表示：

- 所有 suite 的 runner 已實作
- 所有 fixture / golden cases 已寫完
- 所有 mixed suites 的 judge prompt 已定稿

---

## 下一步

1. 為 MVP Micro-Suites 先建立第一批案例
2. 將 Bundle 1 / Bundle 2 case 逐項 map 回對應 micro-suites
3. 小幅更新 foundation pack 與 Wave 1 spec

---

## 歷史

- 2026-04-24: v1 初始版本，建立 Wave 1 capability micro-suites 骨架與建置順序
