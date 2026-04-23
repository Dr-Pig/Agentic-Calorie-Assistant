# V2 Foundation Docs Execution Patch

## 目的

本文件記錄 2026-04-24 討論後，應同步補入 foundation docs 與 Wave 1 spec 的小幅增量內容。

它的角色是：

- 避免直接大幅覆蓋既有長文件時誤刪內容
- 將 execution-aware、evidence-path、fake-pass、tool-correctness 等新增規則集中收斂
- 作為後續精修以下文件的 patch source：
  - `V2_FAILURE_TAXONOMY.md`
  - `V2_GRADING_RUBRIC.md`
  - `V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`

注意：
- `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md` 已直接補入 Target Execution Stance 與 Build-Order Principle
- 本文件不是新的 canonical truth，而是 foundation-doc patch queue

---

## Patch 1 — `V2_FAILURE_TAXONOMY.md`

### 要補的原因

目前 taxonomy 已能覆蓋大多數 product-truth failures，但 Wave 1 micro-suites 進一步引入：

- evidence-path selection
- Tavily retrieval usage
- evidence normalization
- fake green / benchmark patching

因此 taxonomy 應補強對「工具選路錯誤」與「假通過」的失敗分類。

---

### 建議補入 `FAM-GROUND` 的 subfamilies

#### FAM-GROUND-06 Wrong evidence-path selection
系統選錯 evidence acquisition path，導致後續估算或 committed truth 風險。

典型情況：
- 明明可 exact DB lookup，卻直接 generic estimate
- 明明是家常菜 / 滷味 / 合菜且資訊不足，卻先 Tavily search 或硬估
- exact DB miss 後，本應走 Tavily candidate retrieval，卻直接 heuristic estimate
- Tavily evidence 不足時，本應 ask user / degrade，卻假裝 exact

- default severity: `P1_major`
- upgrade to `P0_blocker` if it causes committed false exactness or ledger mutation
- affected suites: MS3, MS4, MS6
- affected journeys: B, C, D, O, P

#### FAM-GROUND-07 Retrieved evidence misclassified
retrieval 回來的 evidence 被錯誤分類為 exact / anchored / usable，導致錯誤估算。

典型情況：
- Tavily snippet 被直接當作 nutrition truth
- unrelated search result 被當成 matched entity
- fan page / blog / menu discussion 被當官方 source
- serving basis 不明，卻被當成可 commit exact value

- default severity: `P1_major`
- upgrade to `P0_blocker` if it creates false exactness in committed state
- affected suites: MS4, MS5, MS6

#### FAM-GROUND-08 Evidence packet missing required fields
系統雖然有 retrieval / DB result，但沒有轉成可審計、可判斷、可降級的 evidence packet。

典型缺漏：
- no source_type
- no matched_entity
- no serving_basis
- no identity_confidence
- no uncertainty_level
- no usable_for_exact / usable_for_anchor / unusable classification

- default severity: `P1_major`
- affected suites: MS5

---

### 建議補入 `FAM-TRACE` 的 subfamilies

#### FAM-TRACE-05 Unearned green via benchmark patching
測試表面通過，但修法是針對單一 benchmark phrase / case id / fixture shape 的 shortcut，而不是 generalized capability rule。

典型情況：
- code 中出現 benchmark-specific condition
- 只讓某一個 case green，但 sibling cases 沒有改善
- no linked failure family / generalized rule in fix explanation

- default severity: `P1_major`
- upgrade to `P0_blocker` if used to claim bundle readiness
- affected suites: MS12 and all bundle gates

#### FAM-TRACE-06 Surface-only pass without product-truth proof
chat 或 UI 的表面輸出看起來正確，但沒有 state delta / trace / artifact 證明 product truth 真的成立。

典型情況：
- response says “已記錄” but no meal_thread mutation
- UI number appears correct but ledger artifact missing
- bundle report claims pass but request-linked trace absent

- default severity: `P0_blocker`
- affected suites: MS9, MS11, MS12

#### FAM-TRACE-07 Hidden-layer overfit
為了通過測試新增無法解釋、不可觀察、責任混亂的 hidden rewrite / repair / adapter layer。

典型情況：
- hidden layer modifies final output but not product truth
- extra layer duplicates domain semantics outside owner domain
- patch fixes output wording while bypassing state contract

- default severity: `P1_major`
- upgrade to `P0_blocker` if it mutates committed truth incorrectly

---

## Patch 2 — `V2_GRADING_RUBRIC.md`

### 要補的原因

目前 rubric 已定義 functional / semantic / cross-surface / state-boundary / quality / founder-fit 六軸。

新增 micro-suites 後，應補一個輔助檢查：

> Tool / Evidence Path Correctness Checklist

這不是要把 incidental tool order 變成評分主體，而是避免 evidence path 選錯造成 false exactness、bad estimate 或 fake pass。

---

### 建議新增段落：Tool / Evidence Path Correctness Checklist

此 checklist 應放在 hard-fail gates 後，或 A2 Semantic / Product-Truth Correctness 之下。

#### 適用範圍
- exact / generic / Tavily / ask-user / heuristic fallback 之間的 evidence-path correctness
- retrieval result 的 usability classification
- nutrition estimate 的 source posture

#### 檢查項目

1. **Exact DB should be preferred when available**
   - 若 exact DB 中有明確品牌 / 品項 / 規格，不應直接走 generic estimate 或 Tavily

2. **Clarify-first cases should not be searched prematurely**
   - 家常菜、合菜、滷味、麻辣燙等 composition unknown cases，應優先 clarify，不應先用 web search 假裝精準

3. **Tavily is candidate retrieval, not truth oracle**
   - Tavily result 必須進 evidence normalization
   - snippet 不得直接變 final kcal truth

4. **Retrieved evidence must be classified**
   - usable_for_exact
   - usable_for_anchor
   - unusable

5. **Insufficient evidence must degrade honestly**
   - 找不到或 evidence 不足時，應 ask user / anchored estimate / heuristic with uncertainty，不得假裝 exact

6. **Evidence-path failure can hard-fail if it causes false committed truth**
   - 如果選路錯誤導致 committed ledger truth 錯誤，應視為 hard fail

#### 對應 failure families
- `FAM-GROUND-06`
- `FAM-GROUND-07`
- `FAM-GROUND-08`
- `FAM-TRACE-06`

---

## Patch 3 — `V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`

### 要補的原因

Wave 1 spec 已定義 F2.3 Grounding / Estimation Posture，但還需要將 evidence-path selection 從 F2.3 中拆出成更清楚的 current-wave system capability。

---

### 建議新增 capability：F2.3b Evidence Path Selection

#### Purpose
決定本次 nutrition resolution 應走哪一條 evidence acquisition path。

#### Inputs
- food identity signals
- brand / store / product hints
- modifiers / serving / size information
- DB hit / miss status
- ambiguity / composition completeness

#### Outputs
- selected_evidence_path:
  - `exact_db`
  - `generic_db`
  - `tavily_retrieval`
  - `ask_user`
  - `heuristic_fallback`
- rationale
- next tool / workflow call

#### Path selection ladder

1. `exact_db`
   - 用於明確品牌 / 品項 / 規格且 DB 有命中

2. `generic_db`
   - 用於通用食物、份量或組成足夠，可由 generic priors / anchors 估算

3. `tavily_retrieval`
   - 用於明確店家 / 品牌 / 菜名，但 local DB 沒有命中，且 web evidence 有機會提供 anchor

4. `ask_user`
   - 用於 composition / quantity 缺失高影響，且 web search 無法有效解決的情境

5. `heuristic_fallback`
   - 用於可給合理範圍，但必須保留 uncertainty 的情境

#### Invariants
- Tavily retrieval is candidate acquisition, not final truth
- homemade / mixed dish ambiguity should usually prefer clarify over search
- exactness posture must not exceed evidence quality
- selected path must be observable in trace or decision artifact

#### Typical failure families
- `FAM-GROUND-06 Wrong evidence-path selection`
- `FAM-GROUND-07 Retrieved evidence misclassified`
- `FAM-GROUND-08 Evidence packet missing required fields`

---

### 建議更新 Guard Rules

新增：

#### Guard G8 — Evidence path honesty
若 evidence path 無法支撐 exactness，系統不得宣稱 exact 或 committed exact truth。

#### Guard G9 — Tavily candidate discipline
Tavily results must pass evidence normalization and usability classification before being used for estimate synthesis.

---

### 建議更新 Harness Contract

新增必要觀察欄位：

- `selected_evidence_path`
- `evidence_candidates_count`
- `normalized_evidence_packet_exists`
- `evidence_usability_classification`
- `retrieval_artifact_path` when Tavily is called

---

## 合併建議

### 第一階段：保持本 patch doc 作為安全增量
先讓 coding agent / human reviewer 參考本文件。

### 第二階段：等 micro-suites 第一批案例成形後
再將本文件內容合併進：
- taxonomy
- rubric
- Wave 1 spec

### 原因
這樣可以避免在長文件中直接大幅覆蓋造成誤刪，也讓新增概念先接受一次實作與測試回饋。

---

## 歷史

- 2026-04-24: 初始 patch，補充 evidence-path failures、fake-pass failures、tool/evidence grading checklist、Wave 1 evidence-path capability
