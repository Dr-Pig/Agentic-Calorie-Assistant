# L6A Framework Selection Spec

## 1. 目的

這份 spec 定義：

- 我們是否應採用既有 agent runtime framework
- 若採用，應採到哪一層
- 若不採用，哪些能力仍可局部借用
- 哪些框架只適合作為參考，不適合作為系統根

本文件的目標不是列出框架清單，而是回答：

`以目前 L0-L5 已定義的產品 / runtime / memory / eval 契約來看，我們的 v1 應該選哪條技術路線。`

---

## 2. 選型前提

根據 L0-L5，這個系統已經有非常明確的非協商前提：

- `MealThread -> MealVersion -> MealItem[]` 是 canonical intake model
- `recommendation` 不得建立 implicit meal-intent / pending intake state
- calibration 與 rescue 有明確的 proposal / commit 邊界
- memory / retrieval / context packing 已有自定義分層
- benchmark / eval / safety 已有自定義 contract
- 產品北極星是：
  - 用最低摩擦的記錄
  - 持續校準總消耗估計
  - 用有感推薦與提醒提升 adherence
  - 穩定維持熱量赤字

因此，任何框架若要成為主 runtime，至少必須：

- 不偷偷引入 hidden state
- 不重寫 canonical ownership
- 不與既有 memory / eval / benchmark 契約衝突
- 能接受我們是 spec-first，而不是 framework-first

---

## 3. 評估標準

### 3.1 Primary Criteria

1. `Contract Fit`
   - 是否能服從 L1-L5，而不是要求我們改寫 L1-L5 來適配框架
2. `Deterministic Boundary Fit`
   - 是否允許強 deterministic domain core，而不把狀態決策藏進框架內部
3. `Hidden State Risk`
   - 是否容易偷偷帶入 session history、memory、handoff state、或 agent loop side effects
4. `Python / Pydantic Fit`
   - 是否順著目前的 FastAPI / Pydantic / app-domain-application 結構走
5. `Observability / Eval Fit`
   - 是否能與我們自定義 trace / benchmark / eval 系統對齊
6. `Operational Complexity`
   - 是否在 v1 就引入過重抽象與運維成本

### 3.2 Secondary Criteria

- provider flexibility
- human-in-the-loop support
- durable execution
- tool ecosystem
- long-running workflow support

---

## 4. 候選框架分類

### 4.1 Primary Runtime Candidates

- OpenAI Agents SDK
- LangGraph
- PydanticAI
- Google ADK
- AutoGen

### 4.2 Secondary / Partial-Fit Candidates

- Letta
- smolagents

### 4.3 Non-Primary Complements

- Mem0
- Langfuse
- GraphRAG
- LlamaIndex

### 4.4 Reference Systems, Not Direct Dependencies

- OpenClaw
- Claude Code leaks / `cc-haha`

---

## 5. Candidate Assessment

## 5.1 OpenAI Agents SDK

### 強項

- primitives 少，學習曲線相對低
- 內建 tracing、guardrails、handoffs、sessions
- Python-first
- 對 OpenAI 生態整合強

### 與本案的摩擦

- SDK 自帶 agent loop、session、handoff 與 guardrail pipeline，容易與我們的 L1 ownership 邊界重疊
- 若直接採用其 sessions / handoffs / agent-loop 作為主 runtime，容易引入 hidden state
- 我們的 pass contract 比 SDK 的一般 agent loop 更細、更強約束

### 結論

- `不建議作為本系統的主 runtime`
- `可作為局部能力參考或實驗性 tracing / guardrail integration 候選`

---

## 5.2 LangGraph

### 強項

- durable execution
- explicit state graph
- human-in-the-loop / interrupt / resume
- 適合長流程、background、可恢復型 orchestration

### 與本案的匹配

- 在所有外部 runtime 裡，LangGraph 是最接近我們未來 durability / proactive / long-running needs 的
- 若未來要做跨日 background maintenance、rescue / calibration durable workflows、interrupt / resume，LangGraph 有明顯優勢

### 與本案的摩擦

- v1 目前最核心的是 domain correctness，不是長流程 durability
- 若現在把 graph abstraction 當系統根，會提早承擔 orchestration 複雜度
- 會把 build 順序從「先把 domain runtime 跑對」變成「先把 graph engine 對齊」

### 結論

- `是最強的外部主 runtime 備選`
- `但不建議在 v1 直接作為系統根`
- `適合在 v2+ 或 durability phase 再引入`

---

## 5.3 PydanticAI

### 強項

- 與 Pydantic 型別系統高度對齊
- 結構化輸出、驗證、依賴注入、capabilities 設計成熟
- eval / observability 思路清楚
- 與我們的 Python repo 形狀相容度高

### 與本案的匹配

- 若我們想替每個 pass 找一個 typed LLM harness，PydanticAI 是非常自然的候選
- 它與我們現有 `schemas.py` / Pydantic models / typed outputs 的精神一致

### 與本案的摩擦

- 它較像 agent / workflow 開發框架，不直接等於我們要的 domain runtime root
- 即使採用，也不能取代 L1-L5 中已定義的 ownership、memory、benchmark、safety 契約

### 結論

- `是最適合作為 pass-level typed harness 的外部候選`
- `不建議作為系統根框架`
- `若後續需要高階 LLM call harness，優先考慮它，而不是把整個 runtime 交給更重的 agent framework`

---

## 5.4 Google ADK

### 強項

- workflow agents 與 deterministic orchestration 的分離很清楚
- 對 sequential / parallel / loop 這類流程控制有良好抽象

### 與本案的摩擦

- 生態與本 repo 現況並不自然貼合
- 會引入另一套 agent/runtime vocabulary
- 對我們目前 FastAPI / Pydantic / custom domain runtime 的直接槓桿有限

### 結論

- `可作為 workflow control 的參考架構`
- `不建議成為 v1 主選`

---

## 5.5 AutoGen

### 強項

- event-driven multi-agent core 強
- 可擴展、分布式、多 agent 實驗能力強

### 與本案的摩擦

- 本案不是多 agent 研究平台，而是單產品、強 domain-contract runtime
- 現在引入 AutoGen，得到的複雜度大於實際槓桿

### 結論

- `不適合作為本案 v1 主 runtime`
- `僅作 multi-agent research 參考`

---

## 5.6 Letta

### 強項

- memory-first
- 長期 agent memory / self-improving narrative 很強

### 與本案的摩擦

- 我們已明確定義自己的 L4 memory model
- 本案的系統真相在 canonical state，不在 memory engine

### 結論

- `不適合當主 runtime`
- `只適合作 memory product design 參考`

---

## 5.7 smolagents

### 強項

- 輕量
- 上手快
- code agent / tool-calling agent 簡單直接

### 與本案的摩擦

- 對我們這種強 state / strong guardrail / benchmark-heavy 產品，抽象太薄
- 比較像快速原型工具，不像整體系統根

### 結論

- `不適合本案主 runtime`

---

## 5.8 Dify

### 定位

- 更像 agent app platform / builder platform
- 不是我們這種 spec-first、repo-first、custom domain runtime 的適配解

### 結論

- `不作為主 runtime 候選`

---

## 5.9 Mem0 / GraphRAG / LlamaIndex / Langfuse

### 定位

- Mem0：memory subsystem
- GraphRAG：retrieval pattern
- LlamaIndex：data / retrieval framework
- Langfuse：observability

### 結論

- `都不是主 runtime`
- 未來可視局部需求做輔助整合，但不影響系統根選型

---

## 5.10 OpenClaw / Claude Code 類系統

### 價值

- 很有參考價值，尤其在：
  - selector / reranker
  - memory durability
  - context packing
  - runtime ops

### 限制

- 它們不是可以直接嫁接進本 repo 的通用框架
- 更適合作設計參考，而不是 dependency decision

### 結論

- `reference system only`

---

## 6. Final Selection

### 6.1 v1 Primary Decision

`v1 不採用任何單一 agent runtime framework 作為系統根。`

我們的主 runtime 應採：

- `self-built domain runtime`
- `thin provider integration`
- `spec-first orchestration`

也就是：

- canonical state
- commit / proposal boundary
- memory / retrieval / context packing
- benchmark / eval / safety

全部以本 repo 自建 contract 為準，不外包給框架。

### 6.2 Why

因為目前 L0-L5 已經定義得比任何現成框架都更細，而且更 domain-specific。  
若現在反過來把框架設成系統根，代價是：

- hidden state 風險上升
- ownership 邊界被框架稀釋
- benchmark / eval / safety 要重新反向適配
- build complexity 先上升，再來才補正確性

### 6.2A Why OpenClaw Is a Reference, Not the Base Runtime

OpenClaw 與本案確實有很多相似點：

- selector / reranker thinking
- memory durability / compaction
- context packing discipline
- runtime safety
- provider / connector abstraction

這代表它對本案是高價值參考系統，但仍不適合作為 base runtime，原因如下：

1. OpenClaw 的系統根更接近 `multi-channel AI gateway / extensible assistant platform`，而不是本案這種 `domain-first calorie-deficit product runtime`
2. 本案的第一性真相在：
   - `MealThread / MealVersion / MealItem`
   - `DayBudgetLedger`
   - `BodyPlan`
   - `ProposalContainer`
   這些 canonical domain objects，而不是 framework-native session / agent state
3. 若以 OpenClaw 當基底，我們會先承擔其 platform/runtime assumptions，再把本案 domain contract 疊上去，順序是反的
4. 本 repo 現況是 Python + FastAPI + Pydantic + spec-first domain layering；OpenClaw 的主體形態並不自然貼合這個技術基底

因此，OpenClaw 的正確角色應是：

- `reference architecture`
- `pattern source`
- `durability / selector / context discipline` 的設計靈感

而不是：

- canonical state root
- business runtime root
- proposal / commit truth engine

### 6.3 v1 Secondary Decision

若需要引入外部框架，優先順序如下：

1. `PydanticAI`
   - 作為 pass-level typed harness 候選
2. `OpenAI Agents SDK`
   - 作為 tracing / guardrail / limited workflow experimentation 候選
3. `LangGraph`
   - 等到 durability / long-running / interrupt-resume 真成為主需求時，再考慮升級為 orchestration layer

---

## 7. Selection Boundaries

### 7.1 什麼必須自建

- canonical state model
- commit / supersession logic
- `MealThread / MealVersion / MealItem` lifecycle
- ledger / rescue / calibration side effects
- memory model / retrieval policy / context packing
- benchmark / eval / safety rules

### 7.2 什麼可局部借用

- structured-output harness
- tracing sink / processor
- tool wrapper ergonomics
- human-approval tool mechanics
- durable background orchestration

### 7.3 什麼不應該借

- session truth
- hidden memory
- default agent loop as business logic
- implicit handoff state
- framework-native state object 取代 canonical domain object

---

## 8. v1 Recommendation

### 8.1 Recommended Architecture Posture

- 主 runtime：`self-built`
- provider integration：以 `adapter` 層承接，目前可先使用 BuilderSpace 作為 facade
- typed IO：沿用既有 Pydantic schema
- tracing：先用自有 trace envelope，必要時再外接 tracing backend
- framework integration：採 `adapter` 模式，不讓框架反客為主

### 8.1A BuilderSpace as Transitional Provider Facade

BuilderSpace 在 v1 的正確角色應是：

- `transitional provider facade`
- `current model gateway`
- `cost / speed / provider-switching convenience layer`

而不是：

- architecture root
- orchestration truth
- memory / state / proposal engine

採用 BuilderSpace 的好處：

- 目前已能提供多模型入口
- 已接入本 repo 的 [`builderspace_adapter.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/providers/builderspace_adapter.py)
- 可以在 v1 階段快速做成本 / 速度 /效果的實測迭代

但必須遵守以下邊界：

1. 不可把 BuilderSpace 內建 orchestrator 型模型當成本系統 orchestrator
2. 不可把 provider-specific payload 當成 runtime contract 真相
3. 不可讓 BuilderSpace 專屬能力反向污染 L3/L4/L5 的契約

因此，BuilderSpace 可先留在系統裡，但必須保持：

- `replaceable`
- `non-canonical`
- `adapter-scoped`

### 8.1B Logical Model Roles vs Provider Model IDs

v1 應先定 `logical model roles`，再由 provider adapter 映射到實際模型名稱。

建議的 logical roles：

- `fast_router_model`
- `strict_reasoner_model`
- `response_writer_model`
- `vision_parser_model`

目前在 BuilderSpace 上的預設映射可先採：

- `task_meal_link_pass` -> `fast_router_model`
- `decision_pass` -> `fast_router_model`
- `nutrition_resolution_pass` -> `strict_reasoner_model`
- `final_response_pass` -> `response_writer_model`

實際 provider model ID 則屬於 adapter 配置，不應直接寫死進核心 runtime。

這樣做的好處是：

1. 之後移除 BuilderSpace 時，不需改 L3 contract，只需改 adapter mapping
2. 可在不同階段做成本 / 品質 tradeoff，而不必重寫 orchestration
3. benchmark / eval / safety 可以圍繞 logical role 穩定運作，而不是圍繞單一 provider model 漂移

### 8.1C Current Empirical Default

基於目前 founder testing 結果，`grok-4-fast` 可作為 v1 的實測預設主力模型候選，原因如下：

- 速度快
- 成本相對可控
- 在目前任務上，主觀效果優於 `deepseek`
- `deepseek` 在目前測試中較容易帶入過多自帶推論或多餘想法

因此，在 BuilderSpace 階段可先採：

- `fast_router_model = grok-4-fast`
- `response_writer_model = grok-4-fast`

而 `strict_reasoner_model` 則保留為可替換位：

- 先用 `grok-4-fast` 跑通 v1
- 若 nutrition / calibration / rescue 的精度後續不足，再升級為更強 reasoning model

這個決策的本質是：

- v1 先優先考慮 founder-fit、速度、與成本
- 不是先追求理論最強模型
- 但保留之後替換 stricter reasoning model 的結構空間

### 8.2 What We Should Not Do in v1

- 不要把 LangGraph 當系統根再回頭適配 domain
- 不要把 OpenAI Agents SDK sessions 當成產品記憶真相
- 不要把 Letta / Mem0 當 canonical memory layer
- 不要把 Dify 當 backend runtime
- 不要為了「看起來比較 agentic」引入多 agent 抽象
- 不要把 BuilderSpace 的 provider model IDs 直接寫死成 L3 contract 真相
- 不要把 `supermind-agent-v1` 這類內建 orchestrator 模型當成本系統的業務邏輯中樞

---

## 9. Revisit Triggers

只有在以下條件成立時，才應重新打開主 runtime framework 選型：

1. 我們需要 durable background execution，且自建 checkpoint / resume 成本過高
2. proactive / rescue / calibration 需要真正長流程 interrupt-resume
3. human-in-the-loop approval flow 變成主系統負擔
4. provider / model routing 複雜度已超過自建 adapter 可承受範圍
5. tracing / eval / replay 已成熟，且可以安全接上外部 orchestration layer

若上述條件成立，下一個優先重評的主候選應是：

- `LangGraph` 作為 orchestration layer

---

## 10. 與前面 specs 的關係

### 對 L1-L5

L6A 的結論是：

- `L1-L5` 是系統真相
- framework 只能適配 `L1-L5`
- 不能反過來要求 `L1-L5` 為框架改寫

### 對 L6B

`L6B Build Strategy Spec` 必須建立在這個選型結論上：

- 先 build self-built core
- framework integration 只作 optional adapter
- durability / orchestration framework 留作後續 phase gate

---

## 11. v1 Final Decision

`v1 採 self-built domain runtime。`

不是因為現有框架都不好，而是因為：

- 我們的 domain contract 已經比框架更具體
- 我們真正要保護的是 state truth、proposal boundary、memory boundary、eval boundary
- 目前最有價值的是把正確性做穩，而不是先把 orchestration 抽象做大

若只用一句話總結：

`先自己做對，再選擇性借框架；不要先選框架，再努力把自己塞進去。`
