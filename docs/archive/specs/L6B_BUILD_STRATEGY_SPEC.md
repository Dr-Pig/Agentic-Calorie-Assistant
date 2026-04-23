# L6B Build Strategy Spec

## 1. 目的

這份 spec 定義：

- v1 應如何依照 L0-L6A 的結論落地實作
- 實作順序應如何安排
- 哪些模組先做、哪些後做
- 哪些能力可以暫時 stub / fake，哪些不行
- BuilderSpace 在不同 build phase 的角色
- 何時才應考慮引入更重的 external framework

如果 L6A 回答的是：

`用什麼`

那 L6B 回答的就是：

`先做什麼，再做什麼，做到什麼程度才進下一階段`

---

## 2. Build Strategy 前提

這份 build strategy 建立在以下已確定結論上：

- v1 採 `self-built domain runtime`
- canonical state 與 business truth 以 L1-L5 為準
- BuilderSpace 只是 `transitional provider facade`
- provider model IDs 不是 architecture truth
- benchmark / eval / safety 不能留到最後才補

因此 v1 的 build order 必須遵守：

1. `先做 domain truth`
2. `再做 runtime path`
3. `再做 memory / retrieval / context`
4. `再做 benchmark / eval / safety closure`
5. `最後才擴 provider / durability / orchestration sophistication`

---

## 3. Build Philosophy

### 3.1 Correctness Before Cleverness

v1 優先順序：

- domain correctness
- state transition correctness
- guardrail correctness
- traceability

高於：

- agentic sophistication
- multi-agent abstraction
- complex provider routing
- fancy orchestration

### 3.2 Spec-First, Adapter-Second

所有 runtime / provider / framework 相關實作都必須服從既有 spec：

- 先有 contract
- 再有 adapter
- 不允許 adapter 反向定義 contract

### 3.3 Thin-Waist Architecture

v1 應把真正穩定的窄腰定在：

- canonical domain models
- pass contracts
- commit / proposal contracts
- trace envelope
- benchmark case schema

外部模型、provider、甚至部分框架整合都應掛在這個窄腰外圍。

---

## 4. v1 Build Layers

### Layer A. Canonical Domain Core

先做：

- `MealThread / MealVersion / MealItem`
- `DayBudgetLedger / LedgerEntry`
- `BodyObservation / BodyPlan`
- `ProposalContainer / ProposalOption`
- `ProactiveTrigger`

這一層必須先達成：

- schema / persistence shape 穩定
- version chain 正確
- basic supersession 正確
- ledger side effects 可重算

### Layer B. Pass Runtime Core

再做：

- `L3.1 intake`
- `L3.2 recommendation`
- `L3.3A / L3.3B calibration`
- `L3.4 rescue`

這一層必須先達成：

- pass input/output contract 跑得通
- deterministic gate 有效
- commit / no-commit / proposal boundary 正確
- logical model roles 已接入 pass routing，但仍不與單一 provider model ID 綁死

### Layer C. Memory / Retrieval / Context Core

再做：

- `L4A memory model`
- `L4B retrieval policy`
- `L4C context packing`

這一層必須先達成：

- active summary views 可組
- retrieval path task-specific
- context pack 可 replay、可 trace、可節流

### Layer D. Eval / Benchmark / Safety Closure

再做：

- `L5A eval`
- `L5B benchmark`
- `L5C safety`

這一層必須先達成：

- Tier 1 benchmark 可跑
- safety guardrail 有 enforcement
- release gate 可阻擋不合格 runtime

### Layer E. Provider / Ops / Optional Framework Adapters

最後再補：

- BuilderSpace provider hardening
- direct provider fallback
- tracing backend integration
- optional framework adapters

---

## 5. Recommended Phase Plan

## Phase 0. Foundation Hardening

目標：

- repo / spec / encoding / editing discipline 穩定
- benchmark supporting docs 與 trace discipline 穩定

完成條件：

- encoding / spec editing protocol 穩定
- L0-L6A 對齊
- L6B 確立

## Phase 1. Domain Persistence Skeleton

目標：

- 把 L2 的 canonical objects 落成可用 schema / persistence skeleton
- 先建立最小可用 trace container，避免 Phase 2 盲飛

Phase 1 的資料策略預設採：

- `clean reset allowed`
- 不以舊 canary schema compatibility 為優先

但必須先做：

- 舊資料 export
- schema / sample snapshot
- 明確標記本階段為 `breaking schema transition`

至少包含：

- tables / models / repositories
- version chain basics
- ledger recompute basics
- proposal / trigger 基本 lifecycle
- trace envelope schema
- trace write path（至少支援 request / stage / provider / model / status / timestamps）

可暫時 stub 的：

- 完整 retrieval selector
- advanced preference memory

不可 stub 的：

- canonical state shape
- commit / supersession correctness
- trace container 基本可寫入能力

## Phase 2. Intake Vertical Slice

目標：

- 先打通最重要的端到端：
  - text intake
  - multi-turn correction
  - ledger update
  - trace recording

至少包含：

- `task_meal_link_pass`
- `decision_pass`
- `nutrition_resolution_pass`
- `final_response_pass`
- `fast_router_model / strict_reasoner_model / response_writer_model` 的 adapter mapping
- deterministic macro derivation
- `commit_request_candidate`
- ledger sync

完成條件：

- founder-fit intake benchmark 可跑
- correction 不破壞 version chain
- macro failure 可 graceful degrade

Phase 2 應額外產出：

- 至少 `10` 個 founder-fit `benchmark seed cases`
- 來自開發過程中遇到的刁鑽 intake / correction / ambiguity 實例
- 這些 seed cases 應進入 benchmark seed pool，而不是只留在臨時筆記

## Phase 3. Recommendation Vertical Slice

目標：

- recommendation 在 active budget / preference 下可產生合法 candidate
- explicit intake handoff 正確

至少包含：

- preference summary seed
- candidate generation
- ranking
- response / quick action
- explicit handoff to intake
- `fast_router_model / strict_reasoner_model / response_writer_model` 對 recommendation path 的映射

完成條件：

- 不建立 implicit state
- recommendation -> intake handoff 正確
- negative preference 生效

## Phase 4. Calibration Core

目標：

- 讓系統能從體重與 intake history 推出 operating expenditure / bias posture

至少包含：

- `BodyObservation` ingest
- trend window construction
- `operating_expenditure_estimate`
- `intake_estimation_bias_posture`
- proposal gate
- `strict_reasoner_model` 對 calibration model / proposal path 的映射

完成條件：

- insufficient-data / logging-quality-first / calibration-candidate 可正確區分
- active `BodyPlan` 可被 proposal accept 更新

## Phase 5. Rescue Core

目標：

- overshoot 後能產生合法 rescue options 並同步 recommendation posture

至少包含：

- rescue trigger
- rescue assessment
- `same_day_soft_cap`
- `short_horizon_spread`
- `next_meal_protection`
- overlay commit
- `fast_router_model / strict_reasoner_model / response_writer_model` 對 rescue path 的映射

完成條件：

- 不低於 floor
- `15%` guardrail 生效
- non-viable escalation 正確

## Phase 6. Memory / Retrieval Deepening

目標：

- 補齊 pattern memory / negative memory / selector layer / context packing discipline

至少包含：

- consolidation job
- freshness / staleness
- negative preference memory
- retrieval selector / reranker
- atomic context packing

## Phase 7. Eval / Benchmark / Safety Hardening

目標：

- 建立 release-capable quality gate

至少包含：

- Tier 1 benchmark set
- founder golden set
- general sanity set
- regression promotion
- release gate automation

## Phase 8. Provider Hardening / Migration Readiness

目標：

- 降低 BuilderSpace lock-in

至少包含：

- direct provider adapters 補齊
- logical model roles 可映射到非 BuilderSpace provider
- provider failover / fallback policy

---

## 6. What Must Be Built Before Others

### 6.1 Hard Dependencies

- `L2 canonical state` 先於 `L3 runtime`
- `L3.1 intake` 先於 `L3.2 recommendation`
- `L3.3A` 先於 `L3.3B`
- `L3.3B` 與 `L3.4` 先於完整 recommendation / rescue / calibration sync
- `L4 summaries` 先於成熟 recommendation personalization
- `L5B benchmark cases` 先於可信的 `L5A eval`

### 6.2 Soft Dependencies

- negative preference memory 可在 recommendation v1 後補強
- selector / reranker layer 可在 retrieval v1 後補強
- direct provider fallback 可在 BuilderSpace 跑穩後補

---

## 7. BuilderSpace Strategy by Phase

### 7.1 Early Phases

在 Phase 1-5，BuilderSpace 可作為：

- 單一 provider facade
- 快速測模型效果與成本的實驗入口
- stage-model mapping 的暫時承載層

### 7.2 Required Boundary

即使在早期階段，也必須保證：

- pass runner 不依賴 BuilderSpace 特有 orchestrator 行為
- domain logic 不依賴 BuilderSpace 內建手工具流程
- provider-specific quirks 只留在 adapter

### 7.3 Late Phases

進入 Phase 8 後，BuilderSpace 應逐步被降級成：

- one provider option among many

而不是：

- 唯一 provider truth

---

## 8. What Can Be Stubbed in v1

可以先 stub / fake：

- advanced recipe recommendation
- generalized multi-user preference adaptation
- long-horizon proactive sophistication
- rich UI preference editing
- multi-provider smart routing

不可以先 stub：

- canonical state correctness
- proposal / commit boundary
- rescue / calibration guardrails
- ledger correctness
- trace envelope
- benchmark replayability

---

## 9. Build Output Artifacts

每個 phase 至少應產出：

1. runnable code path
2. benchmark cases
3. trace examples
4. failure matrix delta
5. rollout note / known limitations

這樣 build 才不是只交 code，而是交一個可驗證增量。

---

## 10. Exit Criteria for v1

v1 不以「功能列表很多」為完成，而以以下條件為完成：

1. founder-fit intake / correction / recommendation / calibration / rescue 主流程可跑通
2. Tier 1 benchmark buckets 達到 L5A / L5B 門檻
3. L5C hard fail guardrails 有 enforcement
4. BuilderSpace 可被替換而不破壞 domain contract
5. trace / replay / regression 能支持後續持續迭代

---

## 11. What We Should Not Do

- 不要先做完整 agent platform 再補產品
- 不要先做多 provider router 再補 canonical state
- 不要先做花哨 proactive 再補 rescue / calibration correctness
- 不要把 benchmark / eval 放到 build 尾聲才做
- 不要讓 BuilderSpace orchestration feature 變成 business logic dependency

---

## 12. 與 L6A 的關係

L6B 直接繼承 L6A 的結論：

- 系統根是 `self-built domain runtime`
- framework 只作 optional adapter
- BuilderSpace 是 transitional provider facade

因此，build sequence 必須優先保護：

- domain truth
- runtime contract
- benchmark / safety closure

而不是優先保護某個 framework integration。

---

## 13. v1 Final Build Posture

若只用一句話總結：

`v1 先做可驗證的 domain runtime 垂直切片，再逐步補 memory、eval、provider 可替換性；不要先做通用 agent 平台。`
