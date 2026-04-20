# L6E LLM Pass Design Policy Spec

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

### 2.2A Decision Mode Rule

是否使用 LLM，不應以整個 domain 的偏好決定，而應以每個 `decision point` 的輸入性質決定。

判斷原則：

- 輸入主要是自然語言、語義歧義、或不完整 evidence 時，`decision_mode` 應為 `llm`
- 輸入主要是數字、閾值、布林 gate、公式、或明確 state transition 時，`decision_mode` 應為 `deterministic`
- 合法性與 guardrail 由 deterministic layer 固定，但多個合法選項之間仍需權衡時，`decision_mode` 可為 `hybrid`
- 只在 deterministic result 已確定、剩餘工作僅為 user-facing explanation / wording 時，`decision_mode` 應為 `llm`

禁止：

- 因為某個 flow 整體偏 LLM-heavy，就把其中的 threshold / formula step 交給 LLM
- 因為某個 flow 整體偏 deterministic-heavy，就把其中的 semantic interpretation step 規則化

### 2.2B Required Step Annotation

從本 spec 起，凡是 `L3.x runtime shape` 中具有獨立責任的關鍵 step，應明確標示：

- `decision_mode: llm | deterministic | hybrid | llm_fallback_only`
- `decision_reason: <為何該 step 採此模式>`

目的：

- 防止 agent 將 domain-level slogan 過度泛化成所有 step 的執行模式
- 讓後續 collapse / expansion 時，仍能維持 decision ownership 不漂移
- 讓 trace 與 eval 可以直接檢查「哪個 decision point 本來就不應交給 LLM」

### 2.2C Product Posture And Experiment Rule

本產品的正式治理預設為：`LLM-first with deterministic carve-outs`。

這代表：

- 預設應先保留模糊語義 interpretation、contextual tradeoff、與 proactive / contextualized orchestration 的 LLM 空間
- 不允許因為方便 formalize，就提前把模糊語義決策規則化成 deterministic hardwork
- 也不允許把明確公式、閾值、布林 gate、legality、或 guardrail truth 留在 LLM 黑箱裡

`pass count`、`step split`、與某些 gray-zone node 的 `decision_mode` 應視為 runtime design hypothesis，而不是先驗真理。

正式規則：

- runtime graph / pass split changes 必須由 evaluation 或 benchmark 支撐，不得只憑 style preference 決定
- 每次改某個 domain 的 canonical graph 前，至少應比較：current graph、collapsed variant or expanded variant、correctness、stability、latency、token cost
- gray-zone step 應保留：
  - `decision_mode`
  - `decision_reason`
  - `candidate_for_future_determinization`
  - `candidate_for_future_collapse`

### 2.2D Routing vs Response Boundary Rule

pass design 不只要決定 `LLM or deterministic`，還要決定某個 distinction 到底屬於：

- primary routing
- workflow-specific structured reasoning
- response realization

正式規則：

> 不要把本來應由 LLM 在回應時自然決定的差異，提前硬編成 primary routing taxonomy。

只有在某個 distinction 會改變下列之一時，才允許升成 primary routing taxonomy：

- target object attachment
- workflow ownership
- state mutation intent
- proposal / commit disposition
- whether a new workflow should open
- whether the system should act, wait, or remain no-op

預設屬於 response realization、而非 primary routing 的差異包括：

- inquiry vs explain
- tone
- style
- reluctance wording
- explanation density
- gentle vs blunt framing
- coaching style

若需要更完整的 cross-product 治理邊界，應再對照：

- `docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md`

### 2.2E Deterministic Gate Boundary Rule

每一個 LLM 輸出後方可以存在 deterministic gate。

但 deterministic gate 的責任只限於：

- schema validation
- allowed action validation
- object availability
- persistence legality
- safety / legality
- bounded repair only

禁止：

- 重新解讀 user intent
- 創造新的 semantic judgment
- 將合法的 LLM routing / planning result silent override 成另一個語意結果

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
| L3.2 | Contextual Recommendation | 5 | 4-pass when candidate spec already exists; 3-pass when candidate spec and candidate pool are both already assembled | candidate retrieval, hard constraint filtering, availability filtering, source joins | context understanding, candidate spec generation, soft ranking, tradeoff synthesis, concise explanation | no |
| L3.3A | Body Calibration Model | 0-1 | 0-pass preferred | trend math, expenditure estimation, confidence scoring, mismatch attribution | optional narrative explanation only | no |
| L3.3B | Calibration Proposal Policy | 2-3 | `deterministic gate -> proposal response` when option families are template-shaped | proposal eligibility gate, blocked family rules, effect math, budget delta computation | proposal shaping, negotiation framing, response wording | no |
| L3.4 | Rescue / Coaching | 4 expanded / 2 default | 2-pass default when response-only rescue posture is enough | overshoot detection, spread math, horizon limits, viability scoring, cooldown checks, option generation | proposal shaping, coaching phrasing, proposal presentation | no |
| L3.5 | Body Observation / Exercise | 2 chat / 1 structured UI | answer-only paths should collapse into `general_chat` | TDEE recompute, MET math, ledger bonus writeback, canonical object create legality | observation extraction, exercise extraction, response wording | no |
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
- `Pass 1 + Pass 2` 不可合併
- 唯一可壓縮的是 response 表現形式或 channel-specific inline response，不是 boundary gate
- 不可直接把 `task_meal_link_pass` 與 nutrition resolution 合併成單次黑箱推理

### 4.2 Recommendation

`L3.2 recommendation` 的 canonical default 是 5-node graph：

1. `recommendation_context`
2. `candidate_spec_generation`
3. `candidate_retrieval`
4. `ranking_and_synthesis`
5. `recommendation_response`

正式規則：

- `recommendation_context` 應為 `llm`
- `candidate_spec_generation` 應為 `llm`
- `candidate_retrieval` 應為 deterministic
- `ranking_and_synthesis` 應為 `llm`
- `recommendation_response` 應為 `llm`

理由：

- 若缺少 `candidate_spec_generation`，則 deterministic retrieval 只是在做 dumb SQL / hard-filter 查詢，candidate universe 從一開始就可能錯
- recommendation 的 agentic 核心不是讓 LLM 直接亂選，而是先由 LLM 把自然語言偏好語義化，再由 deterministic retrieval 執行該 blueprint，最後再由 LLM 進行 contextual ranking and synthesis

collapse 規則：

- 若 `candidate_spec` 已由前段 surface 或 proactive handoff 明確提供，可 collapse 成 4-node
- 若 `candidate_spec` 與 `candidate_pool` 皆已確定，才可進一步 collapse 成 3-node
- `candidate_spec_generation` 不得被重新降格為 expanded-only helper

### 4.3 Calibration

`L3.3A` 的核心真相是 model / math，不是 LLM workflow。

`L3.3B` 的 canonical default 是：

1. deterministic proposal gate
2. proposal policy shaping
3. proposal presentation（若 surface 需要）

只有在 option family 很多、且需要獨立 guardrail ranking 時，才可進入 expanded mode。

### 4.4 Rescue

`L3.4 rescue` 的 canonical default 應以 expanded 4-node graph 定義責任：

1. `trigger_and_viability_assessment`
2. `option_generation`
3. `proposal_shaping`
4. `response_presentation`

decision ownership：

- `trigger_and_viability_assessment` 應為 deterministic
- `option_generation` 應為 deterministic
- `proposal_shaping` 應為 `llm`
- `response_presentation` 應為 `llm`

以下必須留在 deterministic：

- overshoot amount
- spread horizon limits
- safety floor checks
- `recovery_viability`
- cooldown / suppression
- recovery-option math / days / cap mode generation

以下不得被硬規則化回 deterministic：

- proposal family shaping
- coaching framing
- user-facing proposal condensation

default collapse 規則：

- 當 rescue 只需要 deterministic assessment + single response surface 時，可 collapse 為 2-node
- 但 expanded 4-node 仍是 owner truth，避免 `option_generation` 與 `proposal_shaping` 再次混責

### 4.5 Body Observation / Exercise

`L3.5 body_observation / exercise` 採 thin workflow，不應誤標成 deterministic extraction。

正式規則：

- observation extraction / create path 應為 `llm`
- exercise extraction / create path 應為 `llm`
- TDEE recompute、MET math、ledger bonus writeback 應為 deterministic
- pure answer path 應優先走 `general_chat + answer_only`，而不是重開 heavy workflow

### 4.6 Proactive

`L3.6 proactive` 現在就定義，不再延後為未來 bundle placeholder。

canonical layering：

1. deterministic trigger gate
2. LLM contextual send / skip decision
3. chat-first delivery

正式規則：

- schedule / event check、cooldown、suppression、quiet hours、onboarding gate 應為 deterministic
- 是否真的送出、如何 contextualize、以及 `skip_reason` 應由 LLM 決定
- proactive delivery 應進對應 workflow family surface，不在 scheduler 層直接做高影響 mutation

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
- `decision_mode` and `decision_reason` for any new or controversial step

若缺少這些欄位，則該 pass design 視為未完整定義。
