# V2 Wave 1 Deep Capability Spec

## 目的

本文件定義 **V2 Wave 1 的 deep capability spec**。

Wave 1 不是單一 bundle，也不是整個產品的永久總規格。
它描述的是：**目前這一波要真正建成的產品閉環**，以及這一波的能力邊界、依賴關係、guardrails、harness contract、allowed write surface 與 anti-overfit discipline。

本文件直接服務於：

- current-wave implementation
- Bundle 1 / Bundle 2 execution
- benchmark v1 / benchmark v2 / turn2 replay 的重整與對位
- 後續 capability micro-suites 設計
- 防止 agent 以 fake pass、hardcoded patch、架構失真、延遲失控的方式把案例「弄綠」

---

## 本文件在文件系統中的位置

### 上游依據

本文件必須服從以下 canonical docs：

1. `L0_PRODUCT_CAPABILITY_SPEC.md`
2. `app_v2_ideal_architecture_final.md`
3. `APP_V2_IMPLEMENTATION_PLAN.md`
4. `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`
5. `V2_FAILURE_TAXONOMY.md`
6. `V2_GRADING_RUBRIC.md`

### 下游依附

本文件應被以下文件引用：

- `docs/quality/V2_EVAL_BUNDLE_1_CASES.md`
- `docs/quality/V2_EVAL_BUNDLE_2_CASES.md`
- Wave 1 capability micro-suites
- benchmark v1 / v2 mapping docs
- turn2 hybrid replay mapping docs

---

## 為什麼是 Wave 1，不是 Bundle 2

Wave 1 描述的是 **目前這一波的產品閉環**，而不是某一個驗收包。

- **Wave** = 建置波次 / product closure
- **Bundle** = 驗收分包 / eval gate

Bundle 2 雖然是目前最重要的驗收包之一，但它依賴 Bundle 1 的 foundation，且實際跨越：

- onboarding / fallback truth
- meal-thread resolution
- budget / overshoot / cross-surface sync
- trace / artifact governance

因此，Bundle 2 不能單獨代表整個 current wave。

---

## Wave 1 的產品閉環（Product Closure）

Wave 1 的目標不是「做出 intake demo」，而是完成以下最小但完整的產品閉環：

1. 使用者在 **有 onboarding** 的情況下，可透過 chat 完成單回合錄入、clarify、correction，並看到 chat / UI 一致的結果
2. 使用者在 **沒有 onboarding** 的情況下，仍可完成 intake logging，但 budget 相關回答必須誠實降級
3. 系統能把 intake 相關輸入正確落到 `meal_thread`
4. committed intake 會正確更新 `day_budget_ledger`
5. chat、UI、later query、trace 反映同一組 shared truth
6. overshoot 在 Wave 1 只做 **display / awareness**，不偷渡 rescue proposal negotiation
7. correction 必須保留 non-target items，並能建立可追溯版本關係

一句話：

> Wave 1 = `plan-or-fallback + meal-thread resolution + ledger sync + same-truth surfaces`

---

## Wave 1 覆蓋的 Journeys

### In-scope journeys

- A Onboarding 完整流程
- B 單回合錄入 + 預算同步
- C 珍珠奶茶 clarify
- D 家常菜 clarify
- E 超標後的 UI 警告與對話回覆
- J 跳過 onboarding 的降級行為
- K 餐點修正（item-level）

### Out-of-scope journeys（Wave 2+）

- F / F2 救援提案與談判
- G / H / I 體重更新與校準提案的完整閉環
- L / M 推薦與偏好記憶
- N proactive nudges
- O / P multimodal / voice 完整體驗

注意：
- out-of-scope 不代表可以忽略其未來存在
- Wave 1 的設計必須為這些 later-wave capabilities 保留正確邊界

---

## Wave 1 對應的 Capability Families

Wave 1 主要深挖以下 whole-product families：

- **F1 Plan Bootstrap & Fallback**
- **F2 Meal Thread Resolution**
- **F3 Budget & Cross-Surface Sync**
- **F8 Cross-Channel / Cross-Surface Experience**（只取 current-wave 必要 invariant）
- **CF9 Trace / Eval Governance Surface**（execution evidence 必要部分）

---

## Wave 1 必做能力（Must-Deliver Capabilities）

以下是 Wave 1 一定要建出的能力，缺任一項都不能算 current-wave 完成。

### W1-C1. Onboarding bootstrap
- 建立 active `body_plan`
- 建立初始 `day_budget_ledger`
- chat / UI 對 target truth 一致

### W1-C2. No-plan degraded intake mode
- 無 onboarding 仍可 intake
- 但不得假裝知道 remaining budget
- 必須能在適當時機引導設定 plan

### W1-C3. Single-turn meal logging
- 能解析單回合輸入
- 能建立或更新 `meal_thread`
- 能輸出可 commit 的 nutrition result

### W1-C4. Clarify mode selection
- 區分：
  - `estimate_with_followup`
  - `clarify_before_estimate`
  - `direct_commit/direct_estimate`

### W1-C5. Draft vs commit boundary
- 資訊不足時停在 draft
- 資訊足夠時 commit
- draft 不得污染 committed ledger truth

### W1-C6. Correction / removal / versioning
- item-level correction
- item removal
- new version / supersede semantics
- non-target preservation

### W1-C7. Budget sync
- intake commit 後更新 `day_budget_ledger`
- correction 後同步更新 ledger
- overshoot truth 來自 ledger，不由 response layer重算

### W1-C8. Macro visibility control
- `canonical_commit == false` 時不顯示 macro
- macro 對齊失敗時不顯示 macro
- uncertainty / identity 信心不足時不顯示 macro

### W1-C9. Chat / UI / later query same-truth
- chat 說的數字 = UI 顯示的數字
- correction 後 later query 必須讀到更新後 truth

### W1-C10. Trace / artifact contract
- request_id linkage
- eval artifact completeness
- no pass claim without evidence

---

## Wave 1 明確不做的能力（Must-Not-Sneak-In）

以下能力在 Wave 1 中不可偷渡成正式 committed semantics：

### W1-O1. Rescue proposal negotiation
- intake reply 不得夾帶 rescue proposal
- 不得在 overshoot reply 中直接建立 rescue committed overlay

### W1-O2. Full calibration semantics
- 不得因為 body observation 就 silently rewrite body plan
- calibration proposal / acceptance 留到 Wave 2

### W1-O3. Recommendation ranking / memory writes
- 不得把 Wave 1 intake flow 擴張成 recommendation semantics

### W1-O4. Proactive outreach
- Wave 1 不定義主動提醒 / rescue push / recommendation push 的正式產品行為

### W1-O5. Native-only modality promises
- Wave 1 不可在 unsupported channel 假裝支援 background/location semantics

---

## Shared Product Objects in Wave 1

Wave 1 主要操作以下 objects：

### 1. `meal_thread`
Wave 1 primary product object。

Wave 1 必須支援：
- create
- attach followup
- clarify draft
- commit
- correction
- supersede
- remove item

### 2. `day_budget_ledger`
Wave 1 daily truth object。

Wave 1 必須支援：
- bootstrap
- commit intake delta
- correction delta
- remaining / overshoot query
- shared UI / chat projection

### 3. `body_plan`
Wave 1 只需要支援：
- onboarding bootstrap result
- no-plan degraded behavior decision basis

### 4. `proposal`
Wave 1 只需保留邊界：
- proposal ≠ committed state
- rescue / calibration proposal 不在 Wave 1 內生效

### 5. `proactive_trigger`
Wave 1 只需保留未來可用的 object 邊界，不做正式 workflow

---

## Domain Ownership（Wave 1）

### `intake` owns
- meal-thread lifecycle
- followup attachment
- correction / removal / supersede semantics
- commit candidacy boundary

### `nutrition` owns
- grounding
- estimation
- exactness / uncertainty posture
- macro output plausibility source

### `budget` owns
- ledger truth
- remaining / overshoot truth
- budget mutation semantics

### `body` owns
- onboarding result input to active body plan
- body-plan bootstrap truth

### `runtime` owns
- orchestration
- response realization
- surface sync presentation contract
- trace / sidecar / artifact linkage
- guard enforcement

硬規則：
- runtime 協調，不吸走 business semantics
- ledger truth 不得被 renderer / LLM response layer重算
- intake 不得自己擁有 budget final truth

---

## Wave 1 Deep Capability Decomposition

## F1 Plan Bootstrap & Fallback

### F1.1 Onboarding Bootstrap

#### Purpose
建立 active body plan 與初始 day budget truth。

#### Inputs
- onboarding form data
- user goal parameters

#### Outputs
- active `body_plan`
- initial `day_budget_ledger`
- queryable target numbers

#### Invariants
- chat / UI target values 必須一致
- onboarding success 不可只停在 response text

#### Related journeys
- A

#### Typical failure families
- `FAM-BOOT-02`
- `FAM-BOOT-04`
- `FAM-SYNC-01`

---

### F1.2 No-Plan Fallback

#### Purpose
讓沒有 active body plan 的使用者仍可 logging，但 budget answer 誠實降級。

#### Inputs
- intake request without active plan
- budget question without active plan

#### Outputs
- intake allowed
- budget query degraded honestly
- onboarding guidance surfaced when appropriate

#### Invariants
- 不得 hallucinate remaining kcal
- degraded mode 也必須 chat / UI 一致

#### Related journeys
- J, B (when no plan)

#### Typical failure families
- `FAM-BOOT-01`
- `FAM-BOOT-03`
- `FAM-SYNC-04`

---

## F2 Meal Thread Resolution

### F2.1 Intake Routing / Thread Intent Detection

#### Purpose
判斷輸入是否屬於新 meal、same-meal followup、correction、query，並定位正確 thread。

#### Inputs
- user utterance
- recent meal-thread context

#### Outputs
- thread action intent
- target thread reference or new-thread candidacy

#### Invariants
- same-meal補充優先 attach 到 existing thread
- correction 不得誤判為新 meal

#### Related journeys
- B, C, D, K

#### Typical failure families
- `FAM-THREAD-01`
- `FAM-THREAD-02`
- `FAM-THREAD-03`

---

### F2.2 Clarify Mode Selection

#### Purpose
決定該走：
- `estimate_with_followup`
- `clarify_before_estimate`
- direct estimate / direct commit

#### Inputs
- parsed meal intent
- food identity confidence
- composition completeness

#### Outputs
- clarify mode
- followup need
- whether provisional range is allowed

#### Invariants
- 珍珠奶茶類可先給範圍再追問
- 家常菜 / 滷味 / 合菜類在不知道組成時不可先報 kcal

#### Related journeys
- C, D

#### Typical failure families
- `FAM-CLARIFY-01`
- `FAM-CLARIFY-02`
- `FAM-CLARIFY-03`
- `FAM-CLARIFY-04`

---

### F2.3 Grounding / Estimation Posture

#### Purpose
在 exact lookup、anchored estimate、heuristic estimate 之間做正確 posture 決定。

#### Inputs
- food identity signals
- brand signals
- modifiers / quantity / cup size / sugar level

#### Outputs
- exactness posture
- estimate range or exact value
- uncertainty metadata

#### Invariants
- 不可把 heuristic 假裝 exact
- uncertainty 必須被保留，而非被 response layer 消音

#### Related journeys
- B, C, D

#### Typical failure families
- `FAM-GROUND-01`
- `FAM-GROUND-02`
- `FAM-GROUND-03`
- `FAM-GROUND-04`

---

### F2.4 Draft vs Commit Candidacy

#### Purpose
決定當前 thread 是否可進 committed truth。

#### Inputs
- clarify state
- exactness / uncertainty posture
- required fields completeness

#### Outputs
- `canonical_commit` true/false
- commit payload or draft continuation

#### Invariants
- clarify draft 不得進 ledger
- 資訊足夠時不應無限停在 draft

#### Related journeys
- C, D, B

#### Typical failure families
- `FAM-THREAD-04`
- `FAM-STATE-02`

---

### F2.5 Correction / Removal / Supersede

#### Purpose
支援 item-level correction、item removal、version lineage。

#### Inputs
- correction utterance
- target meal thread
- target item reference

#### Outputs
- new meal version
- item updated / removed
- supersede relation

#### Invariants
- correction 不得破壞 non-target items
- version lineage 必須可追溯

#### Related journeys
- K

#### Typical failure families
- `FAM-CORR-01`
- `FAM-CORR-02`
- `FAM-CORR-03`
- `FAM-CORR-04`

---

### F2.6 Intake Response Realization

#### Purpose
將已決定的 product truth 轉成符合 Wave 1 的 chat reply。

#### Inputs
- exactness / uncertainty
- commit state
- budget state
- macro visibility state

#### Outputs
- user-facing reply only

#### Invariants
- 不得在 intake reply 中嵌入 rescue proposal
- 不得把 draft 說成已完整記錄
- macro visible policy 必須 obey shared truth，不由 wording 自由發揮

#### Related journeys
- B, C, D, E, K, J

#### Typical failure families
- `FAM-UX-01`
- `FAM-UX-02`
- `FAM-UX-03`
- `FAM-RESCUE-01`

---

## F3 Budget & Cross-Surface Sync

### F3.1 Ledger Mutation

#### Purpose
把 committed intake / correction 變成正確的 ledger delta。

#### Inputs
- committed meal payload
- correction delta
- active body-plan context

#### Outputs
- updated `day_budget_ledger`

#### Invariants
- draft 不得進 ledger
- correction 必須正確覆蓋 target item delta

#### Related journeys
- B, E, K

#### Typical failure families
- `FAM-SYNC-02`
- `FAM-STATE-02`
- `FAM-CORR-04`

---

### F3.2 Overshoot Presentation

#### Purpose
在 overshoot 發生時，以 ledger truth 呈現 chat / UI warning。

#### Inputs
- updated ledger

#### Outputs
- overshoot status
- remaining / exceeded amount
- warning presentation contract

#### Invariants
- overshoot 數字來自 ledger，不由 LLM 自行重算
- intake reply 可提示超標，但不得偷渡 rescue proposal

#### Related journeys
- E

#### Typical failure families
- `FAM-SYNC-03`
- `FAM-RESCUE-01`

---

### F3.3 Macro Visibility Policy

#### Purpose
決定何時顯示 macro，何時只顯示 kcal。

#### Inputs
- `canonical_commit`
- macro alignment result
- uncertainty level
- identity confidence

#### Outputs
- `show_macro` true/false

#### Invariants
- draft 不顯示 macro
- 對齊失敗不顯示 macro
- 高不確定時不顯示 macro

#### Related journeys
- C, D, E, K

#### Typical failure families
- `FAM-GROUND-05`
- `FAM-SYNC-01`

---

### F3.4 Same-Truth Read Path

#### Purpose
確保 later query（例如「我今天吃了多少？」）讀到 committed latest truth。

#### Inputs
- user query
- current ledger / latest meal-thread version

#### Outputs
- read response aligned with current truth

#### Invariants
- correction 後 later query 不得回舊數字
- chat / UI / later query 必須一致

#### Related journeys
- B, K, E

#### Typical failure families
- `FAM-SYNC-01`
- `FAM-CORR-04`

---

## F8 Minimal Cross-Surface Invariants for Wave 1

Wave 1 不做完整 channel expansion，但以下 invariants 必須成立：

1. chat is the primary agent-driven interaction surface
2. UI is mirror / dashboard / confirm surface
3. 任何 committed truth 在 chat 與 UI 必須可對齊
4. 不得讓某個 surface 形成獨立 state fork

Typical failure families:
- `FAM-CHANNEL-01`
- `FAM-SYNC-01`

---

## CF9 Trace / Harness / Governance Surface

### T9.1 Request / Artifact Linkage

#### Purpose
讓每個 eval case 都能追到 artifact。

#### Invariants
- no bundle pass claim without request-linked artifact
- case execution should carry `request_id`

#### Typical failure families
- `FAM-TRACE-01`
- `FAM-TRACE-02`

---

### T9.2 State Delta Visibility

#### Purpose
讓 evaluator 能判斷 draft / commit / correction / ledger mutation 是否真的發生。

#### Required observable fields (conceptual)
- `canonical_commit`
- `show_macro`
- `uncertainty_level`
- `identity_confidence`
- `ledger_delta`
- `meal_version_delta`

---

## Legal / Illegal State Transitions (Wave 1)

### Legal transitions

#### Meal thread
- `open -> needs_clarification`
- `open -> committed`
- `needs_clarification -> committed`
- `committed -> corrected`
- `corrected -> superseded`

#### Budget truth
- `bootstrapped -> updated_by_commit`
- `updated_by_commit -> updated_by_correction`
- `updated -> overshoot_displayed`

#### Macro visibility
- `hidden -> visible` only if:
  - `canonical_commit == true`
  - macro alignment acceptable
  - uncertainty / identity confidence acceptable

### Illegal transitions

- `needs_clarification -> committed ledger mutation` without sufficient info
- `draft -> visible macro`
- `overshoot -> rescue overlay committed` in Wave 1
- `correction -> overwrite without lineage`
- `no_plan -> concrete remaining budget answer`

---

## Execution Guard Rules (Wave 1)

### Guard G1 — No-plan honesty
沒有 active body plan 時，不得回答具體 remaining budget truth。

### Guard G2 — Draft isolation
當 `canonical_commit == false` 時，不得：
- mutate committed ledger
- mutate consumed totals
- show macro

### Guard G3 — Overshoot source truth
overshoot / remaining / exceeded values 必須以 ledger 為準，不得由 response layer自行重算為新真相。

### Guard G4 — Correction non-target preservation
item-level correction 不得破壞 unrelated items。

### Guard G5 — Macro visibility discipline
macro 對齊失敗或高不確定時，不得展示 macro。

### Guard G6 — No rescue sneak-in
intake / overshoot reply 不得夾帶 rescue proposal semantics。

### Guard G7 — No pass without artifacts
無 request-linked trace / runner artifact，不得 claim bundle pass。

---

## Harness Contract (Wave 1)

Wave 1 harness 不只是看最後一句話，而是必須能看見以下層級：

### H1. Observable state contract
每個 case 至少能觀察：
- whether committed
- whether draft
- whether ledger changed
- whether meal version changed
- whether macro is shown

### H2. Shared-truth contract
至少能交叉驗證：
- chat numbers
- UI numbers
- later query numbers
- trace / artifact linkage

### H3. Bundle-evidence contract
bundle 完成 claim 需要：
- runner output
- request-linked artifact
- case-level verdicts

### H4. Anti-fake-pass contract
以下情況不得視為通過：
- 只有 response text 綠，但 state 無證據
- 只有某個 shard 綠，但 full integration 未驗
- 只有 case-by-case wording 命中，沒有 shared truth 成立

---

## Anti-Overfit Rules (Wave 1)

### AO1. No benchmark-id patching
不得直接針對單一 case id / phrase 寫專屬 shortcut，除非它代表一整個 capability family rule。

### AO2. Family-first fix explanation
每次修某個失敗，必須能說清楚：
- primary failure family 是什麼
- generalized rule 是什麼
- 這個修法應一起改善哪些 sibling cases

### AO3. No fake green by hidden layers
不得為了過測試而新增無法解釋的中介層、黑箱 rewrite 層、或責任混亂的大 service。

### AO4. No performance-indifferent pass
不得以極端多輪、極端重 call、或明顯不合理 latency 換取測試綠。

### AO5. No surface-only success
若 UI 正確但 chat 錯，或 chat 正確但 UI 錯，不算通過。

---

## Allowed Write Surface Guidance (Wave 1)

本節提供 Wave 1 的建置導向，而不是逐檔硬編譯規則。
具體 write surface 仍應與實際 repo 結構對齊。

### Preferred ownership zones
- `app/intake/` for meal-thread lifecycle / correction semantics
- `app/nutrition/` for grounding / estimation / exactness
- `app/budget/` for ledger truth / remaining / overshoot
- `app/runtime/` for orchestration / rendering / guard / trace
- `app/body/` only for onboarding/bootstrap truths needed by Wave 1

### Protected behavior rules
- root facades should stay thin
- runtime should not absorb nutrition or intake business semantics
- renderer should not become truth owner
- guard should validate / block / downgrade, not silently invent new product meaning

### Smell indicators
若某一檔案同時做了以下 3 種以上責任，視為高風險：
- tool orchestration
- business policy
- persistence mutation
- rendering
- trace formatting
- benchmark-specific patching

---

## Latency / Efficiency Guidance (Wave 1)

Wave 1 尚未定義最終數字級 SLA，但必須建立 lane-aware budget 觀念。

至少區分：
- exact/simple intake lane
- clarify lane
- correction lane
- later query lane

硬規則：
- 不可為了過 case 而把 clarify / correction 變成任意堆疊多輪黑箱
- 不可讓 renderer 再做 heavy semantic recomputation
- 不可用 latency 極差但語義上「終於過了」的方案宣稱 bundle ready

---

## Mapping to Existing Eval Assets

### Bundle 1 covers mainly
- F1.1 Onboarding Bootstrap
- F1.2 No-Plan Fallback
- F2.1 basic intake routing
- F2.4 commit candidacy (simple)
- F3.1 ledger mutation
- F3.4 same-truth read path
- T9.1 request / artifact linkage

### Bundle 2 covers mainly
- F2.2 clarify mode selection
- F2.3 grounding / estimation posture
- F2.4 draft vs commit
- F2.5 correction / removal / supersede
- F2.6 intake response realization
- F3.2 overshoot presentation
- F3.3 macro visibility policy
- F3.4 same-truth read path
- T9.1 / T9.2 artifact & state visibility

### benchmark v1 / v2 should be remapped into
- exact / direct commit families
- generic estimate families
- correction integrity families
- budget truth / later query families

### turn2 hybrid replay should be remapped into
- multi-turn attach integrity
- clarify completion
- estimate refinement
- correction follow-through

---

## Wave 1 Completion Conditions

Wave 1 才可被視為完成，若以下條件都成立：

1. Journeys A/B/C/D/E/J/K 有對應 implementation closure
2. Bundle 1 / Bundle 2 P0 cases 皆通過
3. Wave 1 deep capabilities 至少有對應的 script-verifiable micro-suites 設計
4. no known unresolved P0 in:
   - no-plan honesty
   - clarify mode
   - draft/commit boundary
   - correction non-target preservation
   - chat/UI numeric mismatch
   - missing trace linkage
5. current-wave product closure 已成立，不靠 later-wave proposal semantics 補洞

---

## Big-Picture Wave Roadmap (Draft)

### Wave 1
- plan bootstrap / fallback
- intake / clarify / correction
- ledger sync / overshoot display
- same-truth surfaces

### Wave 2
- body observation
- calibration proposal
- rescue proposal negotiation
- accepted overlays / confirmed plan change

### Wave 3
- recommendation
- preference memory
- proactive trigger
- expanded channels / multimodal entrypoints

這個 roadmap 是 build-sequencing guide，不是永久 frozen truth；若產品方向調整，應先更新 whole-product lattice，再調整 wave roadmap。

---

## Definition of Done for This Document

本文件完成，表示：

- Wave 1 的產品閉環已清楚定義
- Wave 1 must-deliver / must-not-sneak-in capabilities 已明確
- current-wave sub-capabilities、guardrails、harness contract、anti-overfit rules 已成形
- 後續可直接進入：
  - Wave 1 capability micro-suites 設計
  - bundle-to-capability mapping 精化
  - coding agent execution pack 建立

本文件完成，不表示：

- Wave 1 已實作完成
- all micro-suites 已存在
- all eval packs 已重寫

---

## 下一步

1. 產出 Wave 1 capability micro-suites 設計稿
2. 將現有 benchmark v1 / v2 / turn2 replay 對位到本文件的 sub-capabilities
3. 建立 coding agent 的 Wave 1 reading pack
4. 讓 Bundle 1 / Bundle 2 不只驗 end-to-end，也驗 sub-capability contracts

---

## 歷史

- 2026-04-24: v1 初始版本，定義 Wave 1 deep capability closure、sub-capabilities、guardrails、harness contract、anti-overfit discipline
