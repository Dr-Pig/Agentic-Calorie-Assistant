# L6D LLM Pass Design Policy Spec

## 1. 目的

這份 spec 將 `各能力域如何決定 LLM pass graph` 正式化。

它回答：

- 哪些 layer 應完全不用 LLM pass
- 哪些 capability domain 應採固定 canonical graph
- 哪些 domain 可以 collapse
- 哪些 domain 不應預設使用 4-pass
- `logical model role` 應如何在 graph 已確定後才被分配

本文件是 `L3.x runtime shape` 與 `L6C model routing` 的共同治理規則。

---

## 2. 核心原則

### 2.1 Graph-First, Role-Second

先決定 capability domain 的最小必要 graph，再決定哪些 node 需要 LLM，以及該 node 對應哪個 `logical model role`。

禁止：

- 先假設所有 domain 都是 4-pass
- 因為已有 `fast_router_model / strict_reasoner_model / response_writer_model`，就反推每個 domain 都要有對應 node
- 把 deterministic math / retrieval / policy gate 假裝成 LLM reasoning pass

### 2.2 Deterministic-First

若某個 node 的核心真相來自：

- schema / enum
- 數學
- guardrail
- retrieval filtering
- state transition legality
- proposal eligibility threshold

則該 node 應優先由 deterministic layer 實作。

LLM 只可用於：

- 模糊語意 interpretation
- 候選間的軟性權衡
- 在 deterministic 約束內做 user-facing explanation / proposal framing

### 2.3 Expanded Mode Is Not Default Truth

某些 domain 可以保留 expanded decomposition 以利觀測、debug、或未來演進。

但 expanded mode 不等於 canonical default。

若 spec 同時存在：

- `canonical graph`
- `expanded pass decomposition`

則 agent 與 implementation 應優先遵守 `canonical graph`，expanded decomposition 只在明確需要時啟用。

### 2.4 L0-L2 / L4-L6 多數是治理層，不是 pass 層

L0、L1、L2、L3M、L3T、L4、L5、L6 多數文件定義的是：

- product semantics
- runtime ownership
- data truth
- typed contract
- retrieval / memory policy
- eval / benchmark / safety policy
- framework / routing / build governance

這些層通常不應被設計成 4-pass workflow。

---

## 3. Canonical Matrix

| L-layer | Capability domain | Canonical pass count | Optional collapsed mode | Deterministic-first parts | LLM-only parts | 4-pass default allowed |
|---|---|---:|---|---|---|---|
| L0 | Product capability framing | 0 | N/A | object model, product states, commit semantics | none | no |
| L1 | Runtime ownership / layer policy | 0 | N/A | ownership, legal transitions, proposal boundary, commit boundary | none | no |
| L2 | Data state / dictionary / contracts | 0 | N/A | schema, enums, canonical state, provenance, ledger fields | none | no |
| L3.1 | Meal Thread Resolution / Intake | 4 | boundary-first collapse only; keep `task_meal_link` isolated | occurred-at normalization, downstream macro derivation, commit validation, deterministic guards | fuzzy boundary interpretation, clarify decision under ambiguity, nutrition estimation with incomplete evidence, final wording | yes |
| L3.2 | Contextual Recommendation | 3 | 2-pass when candidate pool is already retrieved and filtered | candidate retrieval, hard constraint filtering, availability filtering, source joins | soft ranking, tradeoff synthesis, concise explanation | no |
| L3.3A | Body Calibration Model | 0-1 | 0-pass preferred | trend math, expenditure estimation, confidence scoring, mismatch attribution | optional narrative explanation only | no |
| L3.3B | Calibration Proposal Policy | 2 | 1-pass when option families are template-shaped | proposal eligibility gate, blocked family rules, effect math, budget delta computation | proposal shaping, negotiation framing, response wording | no |
| L3.4 | Rescue / Coaching | 2-3 | 2-pass default; 1-pass when rescue families are template-shaped | overshoot detection, spread math, horizon limits, viability scoring, cooldown checks | rescue family selection under soft tradeoffs, coaching phrasing, proposal presentation | no |
| L3.5 | Prompt contract / response surface | 0 | N/A | prompt schema, output contract, channel formatting rules | none at spec level | no |
| L3M | Guardrail math | 0 | N/A | nutrition invariants, bounds, consistency checks, safety floors | none | no |
| L3T | Typed runtime contract | 0 | N/A | typed payloads, required fields, validation envelopes | none | no |
| L4A | Memory model | 0-1 | 0-pass preferred | storage classes, retention, freshness, canonical vs derived memory | optional summarization | no |
| L4B | Retrieval policy | 0-1 | 0-pass preferred | trigger policy, source ordering, filtering, provenance, cache policy | optional rerank under ambiguity | no |
| L4C | Context packing | 1 | 0-pass when deterministic packing suffices | token budgeting, fixed inclusion rules, required slices | compression / summarization of overflow context | no |
| L5A | Eval | 0-1 | 0-pass for metric-only evals | metric computation, fixture execution, regression diffs | optional judge grading | no |
| L5B | Benchmark | 0-1 | 0-pass preferred | harness, benchmark cases, score aggregation | optional open-ended judge | no |
| L5C | Safety / Guardrails | 0-1 | 0-pass preferred | allow/deny gates, threshold checks, hard stops | optional explanation text | no |
| L6A | Framework selection | 0 | N/A | architecture tradeoffs in docs | none | no |
| L6B | Build strategy | 0 | N/A | rollout, migration, sequencing | none | no |
| L6C | Model routing / provider abstraction | 0 | N/A | role mapping, fallback policy, provider normalization | none in routing spec | no |

---

## 4. Domain-Specific Rules

### 4.1 Intake

`L3.1 intake` 是 v1 最接近正式 4-pass 的 domain。

原因：

- boundary splitting 與 meal linking 是獨立責任
- clarify / tool gating 與 nutrition resolution 不應混層
- `final_response_pass` 與 commit-ready payload 需要清楚分離

但 collapse 時必須遵守：

- `task_meal_link_pass` 的 boundary responsibility 不可被 nutrition/tool decision 污染
- simple mode 只能採 `boundary-first collapse`
- 不可直接把 `task_meal_link_pass` 與 nutrition resolution 合併成單次黑箱推理

### 4.2 Recommendation

`L3.2 recommendation` 的 canonical default 是 3-node graph：

1. context shaping
2. retrieval / candidate filtering plus ranking
3. response or UI presentation

若 candidate pool 已由 deterministic retrieval 組好，則可 collapse 成 2-pass：

1. ranking / selection
2. response

`candidate_generation_pass` 可存在於 expanded mode，但不得再被視為所有路徑的必要 LLM pass。

### 4.3 Calibration

`L3.3A` 的核心真相是 model / math，不是 LLM workflow。

`L3.3B` 的 canonical default 是 2-node graph：

1. proposal policy shaping on top of deterministic eligibility output
2. proposal presentation

只有在 option family 很多、且需要獨立 guardrail ranking 時，才可進入 expanded mode。

### 4.4 Rescue

`L3.4 rescue` 的 canonical default 是 2-node 或 3-node graph：

1. deterministic trigger / viability assessment
2. rescue option shaping
3. response presentation（若 channel 需要）

以下應視為 deterministic-first：

- overshoot amount
- spread horizon limits
- safety floor checks
- `recovery_viability`
- cooldown / suppression

`rescue_option_pass` 不得承擔本應由 deterministic rescue math 完成的責任。

---

## 5. Prohibited 4-Pass Default Domains

以下 domain 不得以 4-pass 作為預設設計姿勢：

- `L3.2 recommendation`
- `L3.3A calibration model`
- `L3.3B calibration proposal`
- `L3.4 rescue`
- `L3M guardrail math`
- `L3T typed contract`
- `L4A memory model`
- `L4B retrieval policy`
- `L4C context packing`
- `L5A eval`
- `L5B benchmark`
- `L5C safety`

若某文件需要保留 4-pass expanded decomposition，必須明確標註：

- canonical default graph
- expanded mode only
- collapse rule
- deterministic-first nodes

---

## 6. Relationship To L6C

`L6C` 只負責：

- logical model role vocabulary
- provider routing
- fallback / failover policy

`L6C` 不負責宣告所有 capability domain 的固定 pass count。

正式順序應為：

1. 先由本文件與各 `L3.x` runtime spec 決定 canonical graph
2. 再由 `L6C` 將 graph 內的 LLM-backed node 映射到 logical roles

---

## 7. Implementation Requirement

當 spec、task plan、或 implementation 需要描述某個 domain 的 pass 設計時，至少應寫明：

- `canonical graph`
- `expanded mode if any`
- `collapse rules`
- `deterministic-first nodes`
- `LLM-backed nodes only`

若缺少這五項，則該 pass design 視為未完整定義。
