# V2 Execution Architecture and Wave Plan

## 目的

本文件定義 **V2 的執行架構總覽（execution architecture overview）** 與 **wave-by-wave build plan**。

它的角色是：

- 說明最終系統應長成什麼樣
- 說明 `manager style` 與 `domain workflows / tools` 如何共存
- 說明產品能力、系統能力、bundle、wave 之間的關係
- 為建置順序提供可執行的總覽，而不是只提供產品能力地圖
- 為 coding agent 提供一份「做事前先看懂整體系統」的執行參考

它回答：

- 最終系統應採取什麼 execution stance
- manager、domain workflows、truth owners、guards、trace 各自負責什麼
- 為什麼 bundle 不等於 build order
- Wave 1 / Wave 2 / Wave 3 各自的產品閉環與建置焦點是什麼
- coding agent 在每個 wave 應閱讀哪些文件
- micro-suites、bundle acceptance、benchmark/replay、quality review 應如何分層

它不回答：

- 單一 wave 的完整 deep capability 細節（由各 wave deep spec 定義）
- 單一 bundle 的完整 case 清單（由 bundle eval packs 定義）
- 單一 tool 的程式實作方式
- prompt 逐字稿

---

## 與其他文件的關係

### 上游 canonical docs

1. `L0_PRODUCT_CAPABILITY_SPEC.md`
2. `app_v2_ideal_architecture_final.md`
3. `APP_V2_IMPLEMENTATION_PLAN.md`
4. `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`

### 與 foundation pack 的關係

- `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`：定義 whole-product capability families
- `V2_FAILURE_TAXONOMY.md`：定義 whole-product failure families
- `V2_GRADING_RUBRIC.md`：定義 whole-product grading model

### 與 wave docs 的關係

- `V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`：Wave 1 深規格
- 未來可新增：
  - `V2_WAVE_2_DEEP_CAPABILITY_SPEC.md`
  - `V2_WAVE_3_DEEP_CAPABILITY_SPEC.md`

### 與 eval docs 的關係

- bundle eval packs = acceptance gates
- micro-suites = system-capability contracts
- replay / benchmark packs = regression / realism layer

---

## 核心觀念：四種不同層級，不要混用

### 1. Product Capabilities
使用者真實感受到的產品能力。

例如：
- 單回合錄入
- 珍珠奶茶 clarify
- 家常菜 clarify
- correction
- overshoot awareness
- rescue proposal
- recommendation

用途：
- 定義產品閉環
- 定義 journeys
- 定義外層 acceptance criteria

### 2. System Capabilities
系統內部為了做出產品能力，必須具備的能力。

例如：
- intent / thread detection
- clarify posture selection
- evidence-path selection
- exact DB lookup
- generic DB lookup
- Tavily retrieval
- evidence normalization
- estimate synthesis
- commit boundary
- ledger mutation
- same-truth projection
- trace / artifact linkage

用途：
- 定義建置順序
- 定義 micro-suites
- 定義 implementation dependency graph

### 3. Bundles
外層驗收分包。

例如：
- Bundle 1
- Bundle 2

用途：
- 作為 acceptance gate
- 將產品 journey 打包驗收

### 4. Waves
建置波次 / product closure phases。

例如：
- Wave 1 = intake core closure
- Wave 2 = proposal / calibration / rescue closure
- Wave 3 = recommendation / memory / proactive closure

用途：
- 控制 build scope
- 決定 current-wave deep spec 的範圍

---

## 核心觀念：Manager Style 與 Domain Workflows 不衝突

### 錯誤理解
- `manager style` 和 `workflow decomposition` 是兩套互斥系統

### 正確理解
- `manager style` 是 **外層 orchestration stance**
- `domain workflows / tools` 是 **內層 execution units**

最終穩定系統不是：
- 純 router + rigid workflow
也不是：
- 純 manager 腦內完成所有推理

而是：

> **single manager orchestration + domain-owned workflows / tools + shared truth owners + guards / trace / sidecar governance**

---

## Target Execution Stance

### Outer Layer — Single Manager Orchestration

主 manager 負責：
- 理解當前 user utterance
- 判斷這是 intake / correction / query / recommendation / proposal interaction 的哪一種
- 處理多意圖與跨能力疊加的情境
- 決定要調用哪些 domain workflows / tools
- 維持 proposal / draft / committed 的 state boundary
- 產生最終 response plan

主 manager 不應：
- 吞掉所有 domain business semantics
- 直接擁有 budget final truth
- 直接重算 renderer 層已不該做的 truth

---

### Inner Layer — Domain-Owned Workflows / Tools

每個 domain 應提供自己的 workflow / tools surface：

#### Intake domain
- meal-thread lifecycle
- followup attach
- correction / removal / supersede

#### Nutrition domain
- exact DB lookup
- generic DB lookup
- Tavily retrieval
- evidence normalization
- estimate synthesis

#### Budget domain
- ledger read / write
- remaining / overshoot truth
- today read model

#### Body domain
- onboarding bootstrap inputs
- body-plan truth
- later-wave calibration logic

#### Rescue domain（later wave）
- proposal drafting
- spread math
- negotiation state transitions

#### Recommendation domain（later wave）
- candidate generation
- ranking / filtering
- handoff to intake

---

### Shared Truth Owners

最終真相必須回到 shared product objects：

- `meal_thread`
- `day_budget_ledger`
- `body_plan`
- `proposal`
- `proactive_trigger`

硬規則：
- manager 可以協調，但不能偷走 product object ownership
- channel / UI / sidecar 都不得形成平行 truth

---

### Governance Layer

獨立層負責：
- execution guards
- trace / artifact linkage
- sidecar truth mirror
- bundle pass evidence

這一層的目的：
- 防 fake pass
- 防 hidden patching
- 防 surface-only correctness
- 讓 replay / regression 可審計

---

## 為什麼 Build Order 不應直接來自 Product Capabilities

產品能力通常描述的是外層結果，例如：
- 珍珠奶茶 clarify
- 家常菜 clarify
- correction
- overshoot display

如果直接拿它們當 build order，coding agent 很容易：
- 為了讓最終案例變綠而局部 patch
- 不去建共享中介能力
- 用 hardcoded / benchmark-driven shortcuts 混過去

因此：

> **product capability 決定 build scope 與 acceptance target**
> **system capability 決定 implementation order**

---

## Build-Order Principle

建置順序應主要由 system capabilities 的依賴關係決定。

推薦順序：

1. intent / thread detection
2. clarify posture selection
3. evidence-path selection
4. evidence retrieval
5. evidence normalization
6. estimate / grounding synthesis
7. commit boundary
8. ledger mutation / sync
9. same-truth projection
10. trace / artifact governance

這些能力組合起來，才會做出外層的 product journeys。

---

## Wave Plan 總覽

## Wave 1 — Intake Core Closure

### Product closure
- onboarding bootstrap / fallback
- intake logging
- clarify
- correction
- ledger sync
- overshoot display
- chat / UI / later-query same truth

### Main journeys
- A, B, C, D, E, J, K

### Key system capabilities
- intent / thread detection
- clarify posture
- evidence-path selection
- exact / generic / Tavily evidence acquisition
- evidence normalization
- estimate synthesis
- draft vs commit boundary
- correction / supersede
- ledger mutation
- same-truth projection
- trace / artifact contract

### Main deliverable spec
- `V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`

### Acceptance gates
- Bundle 1
- Bundle 2
- Wave 1 micro-suites
- benchmark v1 / v2 remap
- turn2 replay remap

---

## Wave 2 — Proposal / Calibration / Rescue Closure

### Product closure
- body observation
- calibration proposal
- rescue proposal drafting
- negotiation
- accept / reject / modify
- future budget overlay / plan mutation

### Main journeys
- F, F2, G, H, I

### Key system capabilities
- body observation ingestion
- calibration eligibility
- proposal lifecycle
- proposal state boundary
- rescue math / spread logic
- accepted overlay mutation
- chat negotiation semantics
- proposal inbox mirror

### Main deliverable spec
- future `V2_WAVE_2_DEEP_CAPABILITY_SPEC.md`

### Acceptance gates
- Wave 2 micro-suites
- rescue / calibration bundle(s)
- replay / founder review

---

## Wave 3 — Recommendation / Memory / Proactive Closure

### Product closure
- recommendation
- preference memory
- proactive trigger
- channel / modality expansion
- recommendation-to-intake handoff

### Main journeys
- L, M, N, O, P

### Key system capabilities
- recommendation candidate generation
- ranking / filtering
- preference memory write policy
- proactive trigger policy
- suppression / cooldown
- multimodal normalization
- channel capability ceilings

### Main deliverable spec
- future `V2_WAVE_3_DEEP_CAPABILITY_SPEC.md`

### Acceptance gates
- Wave 3 micro-suites
- recommendation / proactive bundle(s)
- replay / founder review

---

## Wave Files Strategy

### What should exist now
- whole-product overview docs
- foundation pack
- Wave 1 deep spec

### What should not be fully written now
- Wave 2 deep spec
- Wave 3 deep spec

原因：
- later-wave semantics 尚未穩定
- 過早寫深規格會增加過時與誤導風險
- current best practice 是：先有全局骨架，再只深挖 current wave

硬規則：
- all-wave overview 可現在就有
- all-wave deep spec 不應現在一次寫滿

---

## Coding Agent Reading Packs

## Wave 1 Implementation Pack

coding agent 在開始 Wave 1 implementation 前，應至少閱讀：

1. `AGENTS.md`
2. `APP_V2_IMPLEMENTATION_PLAN.md`
3. `app_v2_ideal_architecture_final.md`
4. `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`
5. `V2_FAILURE_TAXONOMY.md`
6. `V2_GRADING_RUBRIC.md`
7. `V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`

## Wave 1 Eval Pack

1. `V2_EVAL_BUNDLE_1_CASES.md`
2. `V2_EVAL_BUNDLE_2_CASES.md`
3. benchmark v1
4. benchmark v2
5. turn2 replay
6. Wave 1 micro-suites

---

## Test Layering Strategy

## Layer 1 — System-Capability Micro-Suites

角色：
- 驗證 system capabilities 是否 individually correct
- 支援 divide-and-conquer
- 優先使用 script-verifiable checks

Wave 1 例子：
- thread intent suite
- clarify mode suite
- evidence-path suite
- Tavily usage suite
- evidence normalization suite
- commit boundary suite
- correction integrity suite
- ledger sync suite
- macro visibility suite
- trace artifact suite

---

## Layer 2 — Bundle Acceptance Gates

角色：
- 驗收 product journeys 的 current-wave closure
- Bundle 不是 build order，而是 acceptance packaging

Wave 1 例子：
- Bundle 1
- Bundle 2

---

## Layer 3 — Replay / Benchmark Functional Layer

角色：
- 驗證現實感、覆蓋邊界、避免只對 bundle patch

例子：
- benchmark v1
- benchmark v2
- turn2 replay

---

## Layer 4 — Quality / Founder Fit Layer

角色：
- 驗證產品感、naturalness、product-fit
- ChatGPT baseline comparison 只作為 quality aid

例子：
- founder review
- baseline comparison
- response quality review

---

## Manager vs Tool vs Workflow Guidance

### Use manager reasoning when:
- 需要多意圖協調
- 需要決定 clarify posture
- 需要決定要不要 commit
- 需要選擇 evidence path

### Use tools when:
- 任務可以被狹義定義
- 輸入輸出可結構化
- 希望可測、可替換、可觀察

### Use bounded workflows when:
- 單一 domain 內部需要多步組合
- 但不想讓 manager 吞掉所有細節
- 又不希望太早升級成黑箱 subagent

### Only use true subagents when:
- domain complexity 已高到 manager 難以穩定調度
- tool chain 已過碎
- bounded workflow 已不夠
- 且你有足夠 tracing / eval / artifact controls

---

## Recommended Maturity Progression

### Stage 1
single manager + tool chain + guards

### Stage 2
single manager + bounded domain workflows + guards

### Stage 3
single manager + selected domain subagents + guards + strong traces

建議：
- Wave 1 停在 Stage 1~2
- 不要太早進 Stage 3

---

## How This Document Should Affect Existing Docs

### `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`
應保持 whole-product shallow map 角色，只需補 execution stance 摘要，不應變成執行細節文件。

### `V2_FAILURE_TAXONOMY.md`
應補 evidence-path selection 與 fake-pass / overfit 類型失敗。

### `V2_GRADING_RUBRIC.md`
應補 tool / evidence-path correctness checklist，作為 hard-gate 輔助檢查。

### `V2_WAVE_1_DEEP_CAPABILITY_SPEC.md`
應補 Wave 1 evidence-path selection 深規格，使 Tavily / DB / ask-user 的選路更清楚。

---

## Definition of Done for This Document

本文件完成，表示：

- manager style 與 domain workflow decomposition 的關係已清楚定義
- wave-by-wave build plan 已明確
- coding agent 的 reading pack 與 test layering 已明確
- foundation pack、wave docs、bundle eval docs 的分工已更清楚

本文件完成，不表示：

- Wave 2 / Wave 3 deep specs 已完成
- Wave 1 micro-suites 已完成
- 所有 overview 已同步寫回其他文件

---

## 下一步

1. 產出 Wave 1 capability micro-suites 設計稿
2. 小幅更新 foundation pack 與 Wave 1 spec
3. 讓 coding agent 以本文件 + Wave 1 spec 作為 implementation overview

---

## 歷史

- 2026-04-24: v1 初始版本，建立 execution architecture overview、wave build plan、test layering、coding agent reading pack
