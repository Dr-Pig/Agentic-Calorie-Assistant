# V2 Whole-Product Capability Lattice

## 目的

本文件定義 **V2 的全產品能力骨架**。

它回答：

- 整個產品有哪些 capability families
- 每個 capability family 主要操作哪些 shared product objects
- 每個 capability family 對應哪些 UX journeys
- 哪些能力屬於 current wave，哪些屬於 later wave
- 當前 deep capability spec 應該切在哪裡，而不是把局部 workflow 誤當成整體產品架構

本文件是 **whole-product, shallow map**。
它不是某一條 workflow 的深層 implementation spec。

---

## 非目標

本文件不定義：

- tool schema
- prompt 設計
- runner 實作
- benchmark oracle 常數
- database schema 細節
- 單一 bundle 的完整 case list

這些分別由 implementation plan、bundle eval packs、runner、quality docs 負責。

---

## 與其他 canonical docs 的關係

### 1. 與 `L0_PRODUCT_CAPABILITY_SPEC.md` 的關係

- `L0_PRODUCT_CAPABILITY_SPEC.md` 定義產品的核心物件、產品互動模型、能力域與高階狀態
- **本文件** 將這些能力域整理成可直接用於 execution / slicing / eval planning 的 capability lattice

### 2. 與 `UX_JOURNEY_TO_SLICE_MAP.md` 的關係

- `UX_JOURNEY_TO_SLICE_MAP.md` 是動態旅程劇本與驗證地圖
- **本文件** 是靜態能力骨架
- Journey 會引用 capability；capability 不直接等於 journey

### 3. 與 `app_v2_ideal_architecture_final.md` 的關係

- canonical architecture truth 仍以 business-domain-first modular monolith 為準
- **本文件不是架構真理的替代品**
- 本文件只能幫助切 execution / eval / ownership，不可反向主導整體 architecture

### 4. 與 `V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md` 的關係

- 本文件定義 whole-product capability families
- `V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md` 定義 execution stance、wave sequencing、manager/workflow/tool 分工與 coding-agent reading pack
- 若兩者重疊，本文件應保持產品能力骨架；execution 細節應留在 execution architecture overview

---

## Target Execution Stance（摘要）

V2 的目標執行樣貌是：

> **single manager orchestration + domain-owned workflows / tools + shared truth owners + guards / trace / sidecar governance**

這代表：

- manager 是外層動態協調者，負責多意圖判斷、workflow/tool 調度、state boundary awareness 與 final response planning
- domain workflows / tools 是內層可測能力單位，負責 nutrition、intake、budget、body、rescue、recommendation 等 domain-owned work
- shared product objects 是 truth anchors，不得由 channel、renderer、sidecar 或 eval fixture 形成平行 truth
- guards / trace / sidecar 是治理層，負責防 fake pass、artifact linkage、shared-truth visibility 與 regression auditability

本節只是 stance 摘要；完整執行架構見 `V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md`。

---

## Build-Order Principle

本文件定義的是 **product capability map**，不是 implementation order。

硬規則：

- product capabilities 決定 build scope 與 acceptance targets
- system capabilities 決定 implementation order 與 micro-suites
- bundles 是 acceptance gates，不是施工順序本身
- current-wave deep specs 才負責把 whole-product families 展開成可建置、可測的 system capabilities

因此，不應直接以 journey 或 bundle 名稱作為 coding agent 的施工順序。coding agent 應先看 current-wave deep capability spec 與 capability micro-suites，再回到 bundle eval packs 做 acceptance。

---

## 核心 shared product objects

全產品主要共享的 product objects 為：

- `meal_thread`
- `day_budget_ledger`
- `body_plan`
- `proposal`
- `proactive_trigger`

所有 capability family 都必須最終落到這些 shared objects，而不是各自長出平行 truth。

---

## Capability Families 總覽

| Capability Family | Primary Product Objects | Primary Owner Domains | Related Journeys | Current Wave |
|---|---|---|---|---|
| F1 Plan Bootstrap & Fallback | `body_plan`, `day_budget_ledger` | `body`, `budget`, `runtime` | A, J | yes |
| F2 Meal Thread Resolution | `meal_thread` | `intake`, `nutrition`, `runtime` | B, C, D, K, O, P | yes |
| F3 Budget & Cross-Surface Sync | `day_budget_ledger`, `meal_thread`, `body_plan` | `budget`, `runtime`, `intake` | B, E, G, H, J | yes |
| F4 Rescue & Proposal Negotiation | `proposal`, `day_budget_ledger` | `rescue`, `budget`, `runtime` | F, F2 | later |
| F5 Body Observation & Calibration | `body_plan`, `proposal` | `body`, `runtime`, `budget` | G, H, I | later |
| F6 Recommendation & Preference Learning | `meal_thread`, `body_plan`, `day_budget_ledger`, preference memory | `recommendation`, `memory`, `runtime` | L, M | later |
| F7 Proactive Triggering | `proactive_trigger`, `proposal`, recommendation objects | `runtime`, `recommendation`, `rescue`, `memory` | N | later |
| F8 Cross-Channel / Cross-Surface Experience | all shared objects | `runtime` + all owning domains | A-P (cross-cutting) | yes |

---

## Family Definitions

## F1. Plan Bootstrap & Fallback

### 目標

建立或缺省處理使用者的初始 body / budget truth，使產品在有 onboarding 與沒 onboarding 的情況下都能工作。

### 核心責任

- 建立初始 `body_plan`
- 建立初始 `day_budget_ledger`
- 定義 onboarding 完成後 Today / body-plan 的 shared truth
- 定義 skip onboarding 時的 degraded behavior

### 主要 owner

- `body`
- `budget`
- `runtime`

### 不負責

- meal estimation 細節
- recommendation ranking
- rescue proposal negotiation

### 關聯 journeys

- A Onboarding 完整流程
- J 跳過 Onboarding 的降級行為

### Current-wave notes

這是 current wave 的必要 foundation，否則後續 intake / remaining budget journey 會失真。

---

## F2. Meal Thread Resolution

### 目標

把使用者的飲食輸入轉成可追問、可修正、可 commit、可跨 surface 同步的 `meal_thread`。

### 核心責任

- new meal logging
- multi-turn clarification
- same-meal refinement
- same-meal correction
- commit / supersede / remove item
- multimodal / voice intake 最終收斂到同一個 `meal_thread`

### 主要 owner

- `intake`
- `nutrition`
- `runtime`

### 不負責

- body calibration proposal
- long-horizon rescue planning
- long-term recommendation ranking

### 關聯 journeys

- B 單回合錄入
- C 珍珠奶茶 clarify
- D 家常菜 clarify
- K item-level correction
- O 照片錄入
- P 語音錄入

### Current-wave notes

這是 current wave 的產品心臟。
深層 capability spec 應以此 family 為主體展開。

---

## F3. Budget & Cross-Surface Sync

### 目標

維持 `day_budget_ledger`、`body_plan`、`meal_thread` 在 chat / UI / quick actions 之間的一致 truth。

### 核心責任

- consumed / remaining / overshoot truth
- meal commit 後 ledger 更新
- body update 後目標同步
- UI 與 chat 數字一致
- warning / status 的 shared truth

### 主要 owner

- `budget`
- `runtime`
- `intake`

### 不負責

- intake identity resolution
- recommendation candidate generation

### 關聯 journeys

- B 單回合錄入 + 預算同步
- E 超標後的 UI 警告與對話回覆
- G / H 體重更新後同步
- J 無 onboarding 時的 degraded budget behavior

### Current-wave notes

current wave 不能只做 intake，不做這層。因為產品要求所有關鍵旅程都要同時驗證 chat 與 UI。

---

## F4. Rescue & Proposal Negotiation

### 目標

在超標或預期超標時，以 `proposal -> negotiate -> confirm -> commit` 模式協助使用者調整未來幾天。

### 核心責任

- rescue proposal creation
- spread calculation
- proposal negotiation in chat
- acceptance / rejection / modification
- future budget overlay

### 主要 owner

- `rescue`
- `budget`
- `runtime`

### 關聯 journeys

- F 當日超標救援
- F2 預期大餐救援

### Current-wave notes

later wave，但 current wave 的 overshoot messaging 需要為未來 rescue 保留邊界：
- rescue 是獨立互動，不應嵌進 intake reply
- proposal 與 committed state 不可混淆

---

## F5. Body Observation & Calibration

### 目標

以體重觀測和長期趨勢修正使用者的 `body_plan` 與每日目標。

### 核心責任

- body observations
- trend interpretation
- calibration candidate detection
- calibration proposal
- confirmed recalibration commit

### 主要 owner

- `body`
- `runtime`
- `budget`

### 關聯 journeys

- G 體重更新（chat）
- H 體重更新（UI）
- I 校準提案

### Current-wave notes

later wave，但 current wave 的 capability design 不能把 `body_plan` 視為靜態不動資料；它是會改變 downstream budget truth 的 product object。

---

## F6. Recommendation & Preference Learning

### 目標

在當前目標、預算、偏好與歷史模式下，協助使用者決定下一餐或下一步。

### 核心責任

- contextual recommendation
- preference read / write
- ranking / filtering
- recommendation to intake handoff

### 主要 owner

- `recommendation`
- `memory`
- `runtime`

### 關聯 journeys

- L 食物推薦
- M 偏好記憶

### Current-wave notes

later wave，但 meal thread / budget / body truth 都會被 recommendation 消費，因此 current-wave docs 不應把它們設計成 intake-only local state。

---

## F7. Proactive Triggering

### 目標

在適合的時機主動發起提醒、推薦、rescue 或補記互動，但保持 explainable、suppressible、可控。

### 核心責任

- trigger eligibility
- cooldown / suppression
- push / channel trigger
- trigger targeting (`meal_thread`, `proposal`, recommendation, reminder)

### 主要 owner

- `runtime`
- `recommendation`
- `rescue`
- `memory`

### 關聯 journeys

- N Proactive nudges
- location-triggered recommendation related flows

### Current-wave notes

later wave。
但現在的 shared objects 設計必須可被 proactive targeting，而不是只能支援 user-initiated flow。

---

## F8. Cross-Channel / Cross-Surface Experience

### 目標

讓 Native App / Web / LINE / LIFF 在不同能力上共享同一 product truth，而不是各自獨立行為。

### 核心責任

- chat-first interaction model
- UI as dashboard / confirm surface
- cross-surface sync invariants
- channel capability downgrade rules

### 主要 owner

- `runtime`（coordination）
- 各 domain（truth ownership）

### 關聯 journeys

- all journeys A-P

### Current-wave notes

這是 cross-cutting family，不應被當成單一 bundle。但所有 current-wave eval 都應至少驗證：
- chat correctness
- UI correctness
- shared truth alignment

---

## Current Wave Deep-Spec Boundary

目前建議 deep capability spec 只展開以下 families：

1. F1 Plan Bootstrap & Fallback
2. F2 Meal Thread Resolution
3. F3 Budget & Cross-Surface Sync

這三者構成 current wave 的真正產品閉環：

- 先有目標或 degraded mode
- 再能記錄 / clarify / correction
- 最後 chat / UI / ledger truth 同步

current wave 不需要先把 F4-F7 完整展開成 deep spec，但 whole-product lattice 必須先保留它們的位置，避免之後 taxonomy 與 ownership 重切。

---

## 文件治理規則

- 本文件是 whole-product capability 骨架，不是 bundle eval 文件
- 任何 workflow-level deep spec 都不得聲稱取代 whole-product capability lattice
- 當 UX Journey 新增或產品物件語義改變時，應先更新本文件，再更新 downstream deep spec / eval docs
- 當 canonical architecture truth 與本文件衝突時，以 canonical architecture truth 為準

---

## 下一步

1. 基於本文件產出 current-wave deep capability spec
2. 產出 whole-product failure taxonomy
3. 產出 grading rubric（functional gate + quality rubric + founder review）
4. bundle-by-bundle 擴張 eval packs

---

## 歷史

- 2026-04-24: 補充 Target Execution Stance 與 Build-Order Principle，明確區分 product capability、system capability、bundle acceptance 與 implementation order
