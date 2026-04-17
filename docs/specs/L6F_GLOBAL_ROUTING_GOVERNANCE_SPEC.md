# L6F Global Routing Governance Spec

## 1. 目的

本文件定義全產品 chat-first agent 的 **routing 治理規範**。

它回答：

- 什麼算第一層 routing responsibility
- 什麼屬於 workflow-specific middle reasoning
- 什麼屬於 final response realization
- deterministic gate 的責任到哪裡為止
- semantic-routing eval 什麼可以當 primary oracle，什麼只能留在 secondary rubric

本文件的定位是：

- **治理規範**
- 不是某個 workflow 的 runtime contract
- 不是新的 shared runtime module
- 不是 production router implementation spec

它用來約束後續 slice，特別是 `2.7 Memory / Retrieval Deepening` 的 semantic-routing 工作，避免把本來應由 LLM 在回應時自然決定的差異，提前硬編成 primary routing taxonomy。

---

## 2. 適用範圍與非目標

### 2.1 適用範圍

本文件適用於所有 chat-driven workflow family，包括但不限於：

- intake
- rescue
- calibration
- recommendation
- body observation
- general chat / new workflow entry

### 2.2 非目標

本文件不直接定義：

- production shared head router implementation
- production shared tail response pass implementation
- concrete cross-product runtime graph
- durable memory write behavior
- retrieval selector / reranker runtime
- style-personalization runtime

### 2.3 與 intake 4-pass 的關係

目前 intake 的 canonical 4-pass 仍由：

- `L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
- `L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`
- `L6E_LLM_PASS_DESIGN_POLICY_SPEC.md`

共同治理。

本文件**不能**被解讀為：

- intake 4-pass 的直接泛化實作
- shared head router 取代 `task_meal_link_pass`
- shared response layer 取代各 domain 的既有 response pass

本文件只定義 **跨產品共用的責任邊界**，不強迫各 workflow 與 intake 完全同構。

### 2.4 Repo-Level Decision Freeze Rule

在 routing / taxonomy / benchmark work 中，必須遵守：

> 未拍板產品語意，不得寫進 eval pack、oracle、taxonomy、或 pass/fail rubric。

允許：

- evidence collection
- ambiguity clustering
- recording competing interpretations

禁止：

- silently promoting unresolved product semantics into canonical eval truth
- using benchmark pass/fail to back-solve product semantics that have not been explicitly decided

---

## 3. 核心治理原則

### 3.1 Routing 與 Response 必須分層

全產品的 chat agent 至少應區分：

1. first-layer routing responsibility
2. workflow-specific structured reasoning
3. response realization
4. deterministic gate validation

這四層是**抽象責任層**，不是固定 pass count 規定。

### 3.2 Shared Principles, Not Shared Runtime

可以定義：

- 全產品都應有 conceptual first-layer routing responsibility
- 全產品都應有 conceptual response realization responsibility

但不能因此宣告：

- repo 已存在 shared head router implementation
- repo 已存在 shared tail response implementation

如果未來要落成 shared runtime，必須由更晚的 runtime spec 與 workflow evidence 支撐。

### 3.2A Workflow Family V1

v1 workflow family 先收：

- `intake`
- `rescue`
- `calibration`
- `recommendation`
- `body_observation`
- `general_chat`

`new_workflow` 不作獨立 workflow family。  
topic switch 由：

- `disposition = open_new_workflow`

表達。

### 3.2B Active Object Family V1

canonical object truth 仍由 `L2 Data State Spec` 管。  
本文件不建立平行的 canonical object inventory。

routing 層只定義 **L2 canonical objects 的精簡投影**，作為 v1 可被對話直接命中的 active object families：

- `meal_thread`
- `proposal`
- `body_observation`
- `none`

明確不在 v1 routing object family 層拆分：

- `pending_intake_followup`
- `open_rescue_proposal`
- `open_calibration_proposal`
- `open_recommendation_proposal`

這些要嘛是 `meal_thread` 的狀態，要嘛是 `proposal` 的型別屬性，不是獨立 object family。

### 3.3 Anti-Premature-Taxonomy Rule

正式硬規則：

> 不要把本來應由 LLM 在回應時自然決定的差異，提前硬編成 primary routing taxonomy。

只有在某個差異會改變下列之一時，才允許升成 primary routing taxonomy：

- target object attachment
- workflow ownership
- state mutation intent
- proposal / commit disposition
- whether to open a new workflow
- whether the system should act, wait, or remain no-op

預設**不得**升成 primary routing taxonomy 的差異包括：

- inquiry vs explain
- tone
- style
- reluctance wording
- explanation density
- gentle vs blunt framing
- coaching style

### 3.4 LLM-Led, Deterministic-Carve-Out

本產品延續 `AGENTS.md` 與 `L6E` 的正式姿態：

- 模糊語意 interpretation 應由 LLM 主導
- deterministic code 只負責：
  - guardrails
  - allowed actions
  - object availability
  - persistence legality
  - safety / legality
  - bounded repair only

deterministic layer 不得：

- 重新解讀 user intent
- 創造新的 semantic judgment
- silent override 合法的 LLM routing result

---

## 4. 全產品責任分層

### 4.1 First-Layer Routing Responsibility

第一層 routing responsibility 應由 LLM 主導。

它至少回答：

- 目前 utterance 最可能作用於哪個 active object
- 哪個 workflow family 應接手
- 對該 object 的 disposition 是什麼

這一層是 cross-product 共用責任，但不代表所有 workflow 必須使用相同 pass 或相同 typed schema。

### 4.2 Workflow-Specific Structured Reasoning

第二層是 workflow-specific 的 structured reasoning。

這一層負責把 routing 結果轉成各 domain 內部需要的 structured planning / decision / proposal / resolution。

例子：

- intake：
  - `task_meal_link_pass`
  - `decision_pass`
  - `nutrition_resolution_pass`
- rescue：
  - proposal shaping
  - action planning
- calibration：
  - observation interpretation
  - proposal shaping
- recommendation：
  - candidate selection
  - proposal eligibility / ranking

規則：

- 各 workflow 的 middle graph 可以不同
- 各 workflow 的 pass count 可以不同
- 不得因為需要抽象治理，就強迫所有 workflow 複製 intake 4-pass

### 4.3 Conceptual Response Realization Responsibility

最終自然語言回覆應由 LLM 主導。

這一層負責：

- 自然語言回覆
- explanation depth
- style / tone
- reluctance handling
- conversational framing
- future `sour.md` / `conversation_style_profile` 類延伸

預設規則：

- 內容 vs 理由
- 語氣
- 說明密度
- 人性化措辭

都屬於 response realization，而不是 primary routing taxonomy。

這裡的 `conceptual` 指的是治理原則共享，不是要求 shared implementation。

### 4.4 Deterministic Gate Responsibility

每一個 LLM 輸出後方都應有小型 deterministic gate。

它可以做：

- schema validation
- allowed action validation
- object availability check
- persistence legality
- safety / legality
- bounded repair only

它不可以做：

- semantic rerouting
- user-intent reinterpretation
- silent substitution of a valid LLM result

---

## 5. Disposition Vocabulary Governance

### 5.1 定位

`disposition` 的治理定位是：

- user-to-object 的系統處置意圖
- cross-product 可重用 vocabulary
- 粒度應比 response nuance 粗
- 必須直接影響 workflow effect 或 state transition

### 5.2 Candidate Vocabulary

v1 core disposition 先收：

- `create`
- `continue`
- `correct`
- `accept`
- `reject`
- `defer`
- `adjust`
- `answer_only`
- `open_new_workflow`

明確不屬於 first-layer disposition：

- `uncertain`
- `no_action_soft_hold`

其中：

- `uncertain` 是 confidence / ambiguity 問題
- `no_action_soft_hold` 是 response posture

### 5.3 Eligibility Matrix V1

v1 eligibility 先定為：

- `meal_thread`
  - `create`
  - `continue`
  - `correct`
  - `answer_only`
- `proposal`
  - `accept`
  - `reject`
  - `defer`
  - `adjust`
  - `answer_only`
- `body_observation`
  - `create`
  - `answer_only`
- `none`
  - `answer_only`
  - `open_new_workflow`

### 5.4 邊界

本文件只把它定義成 **governance candidate vocabulary**。

它目前不是：

- production-wide enforced enum
- existing typed contracts 的強制替換方案

如需正式落地到某個 domain 的 typed contract，必須由對應 `L3.x / L3T` spec 額外批准。

---

## 6. Eval Governance Rule

### 6.1 Primary Oracle 應評估什麼

semantic-routing eval 的 primary oracle 應優先評估：

- target object
- workflow ownership
- disposition
- workflow effect

### 6.1A Confidence / Ambiguity Contract

第一層 routing 的不確定與模糊不放進 disposition。

正式治理 contract 應包含：

- `routing_confidence`
- `ambiguity_posture`

### 6.2 Secondary Rubric 才能放什麼

下列差異若保留在 eval 中，預設只能作 secondary rubric：

- inquiry vs explain
- reluctance posture
- tone / style
- explanation density
- conversational coaching shape

除非 canonical spec 明確說這些差異會改變 disposition 或 workflow effect，否則不得把它們升成 primary routing labels。

### 6.3 Anti-Split Rule

若兩個 label 的：

- target object 相同
- workflow effect 相同
- state mutation semantics 相同

則它們不得被拆成兩個 primary routing labels，除非 canonical spec 明確要求。

---

## 7. 與既有真相文件的關係

### 7.1 與 `L6E`

`L6E` 定：

- graph-first, role-second
- deterministic-first
- decision-mode annotation

本文件補的是：

- routing vs response 的治理分界
- anti-premature-taxonomy rule
- cross-product disposition governance

### 7.2 與 `L3T`

`L3T` 定 typed output contract。

本文件不直接發明新的 production typed contract，只定：

- 哪一類 distinction 有資格成為 first-layer routing output
- 哪些應留在 response-layer or secondary eval rubric

### 7.3 與 `LLM_OWNERSHIP_RULE`

`LLM_OWNERSHIP_RULE` 定義 deterministic code 不可偷走 semantic judgment。

本文件補充：

- 不只 deterministic post-processing 不可偷走 semantic judgment
- eval taxonomy / routing schema 也不得過早把 response-side 差異硬編成 primary routing family

### 7.4 與 `2.7d`

`2.7d` 仍是：

- semantic-routing prompt/state-pack hardening

本文件的效果是：

- 約束 `2.7d`
- 但不擴張 `2.7d` scope
- 不把 `2.7d` 變成全產品 runtime reset

---

## 8. Workflow Graph Mapping Guidance

### 8.1 Intake

必須明寫：

- intake 是目前唯一成熟的 4-pass canonical graph
- conceptual first-layer routing responsibility **不是** `task_meal_link_pass` 的替代物
- `task_meal_link_pass` 仍是 intake domain-specific graph 的一部分

### 8.2 Rescue

rescue 在全局治理規範中可先寫到 subpass 粒度，因為已有較成熟 runtime truth。  
但這只作治理對照，不在本文件中重寫 `L3.4` rescue runtime contract。

### 8.3 Calibration / Recommendation

calibration 與 recommendation 先只定：

- 存在 workflow-specific middle reasoning

但不在本文件中定死 canonical graph，避免 premature abstraction。

### 8.4 Body Observation

`body_observation` 在全局治理規範中視為獨立 workflow family，採 thin graph：

- conceptual first-layer routing
- body_observation-specific middle
- conceptual response realization

這裡的 `conceptual` 仍然表示治理層共享，不等於共用程式碼元件。

---

## 9. Future Extension Note

`sour.md` / `conversation_style_profile` 類概念目前只應視為 response-layer extension point。

未來它可以影響：

- explanation density preference
- direct vs gentle framing
- user-specific phrasing tendency

但目前不得：

- 進入 active routing taxonomy
- 成為 production mandatory runtime component

---

## 10. Implementation Rule

當後續 slice 涉及：

- semantic routing
- workflow ownership
- response-layer distinction
- eval label design

至少應對照本文件檢查：

1. 這個 distinction 是否真的改變 workflow effect
2. 如果沒有，它是否應留在 response realization
3. deterministic gate 是否只做合法性 / 結構性責任
4. 是否存在 premature taxonomy overreach

若未完成此檢查，則該 slice 的 routing design 視為未完整定義。

---

## 11. Workflow Routing Pass 架構決定

### 11.1 Intake Pass 1 與全局 routing 的關係

目前 intake 的 `task_meal_link_pass`（Pass 1）負責：

- 判斷 utterance 是否為 intake-related
- 連結到哪個 MealThread
- 解析 occurred_at 語意
- 拆分多個 intake units

這個 pass 的設計假設輸入已經是 intake。它不是全局 router，不應被擴充成全局 router。

### 11.2 正式決定：加一層薄的 `workflow_routing_pass`

在 intake Pass 1 之前，加一個輕量的 `workflow_routing_pass`，作為全局 first-layer routing。

**它只做一件事**：判斷這個 utterance 屬於哪個 workflow family，輸出 `target_workflow_family` 和 `disposition`。

**它不做的事**：

- 不做 intake 內部的 boundary 判斷（那是 intake Pass 1 的工作）
- 不做 nutrition resolution
- 不做 proposal shaping
- 不做任何 state mutation

**Input**：

- `raw_user_input`
- `active_open_rescue_proposal`（若有）
- `pending_intake_followup`（若有）
- `active_body_plan_summary`
- `recent_message_summary`（最近 2-3 則）

**Output**（`WorkflowRoutingResult`）：

- `target_workflow_family`：`intake` / `rescue` / `calibration` / `recommendation` / `body_observation` / `general_chat`
- `disposition`：`create` / `continue` / `accept` / `reject` / `defer` / `adjust` / `answer_only` / `open_new_workflow`
- `routing_confidence`：`high` / `medium` / `low`
- `ambiguity_posture`：`none` / `allow_uncertain`

**Logical model role**：`fast_router_model`

**Decision mode**：`llm`

### 11.3 各 workflow 的 Pass 1 保持不變

`workflow_routing_pass` 輸出後，各 workflow 的 Pass 1 接手：

- `intake` → `task_meal_link_pass`（現有 Pass 1，不變）
- `rescue` → `rescue_trigger_pass`（現有，不變）
- `calibration` → `observation_ingest` 或 `proposal_gate`（現有，不變）
- `recommendation` → `recommendation_context_pass`（現有，不變）
- `general_chat` → 直接進 `response_writer_model`（1 pass，讀 `CurrentBudgetView` + `ActiveBodyPlanView`）
- `body_observation` → 直接寫入，0 pass

### 11.4 General Chat Workflow

`general_chat` 是一個 1-pass workflow，使用 `response_writer_model`。

它可以回答：

- 「我今天還能吃多少」→ 讀 `CurrentBudgetView`
- 「我的目標是什麼」→ 讀 `ActiveBodyPlanView`
- 「這個 APP 怎麼用」→ 讀 product knowledge

它不做：

- 不 commit 任何 canonical state
- 不觸發 intake、rescue、calibration flow
- 不建立 proposal

### 11.5 與 2.7d semantic routing 的關係

`2.7d` 的 prompt/state-pack hardening 工作就是在強化 `workflow_routing_pass` 的準確性。

`workflow_routing_pass` 是 `2.7e` slice 的實作目標，不是 intake Pass 1 的延伸。
