# L4B Retrieval Policy Spec

## 1. 目的

這份 spec 定義各 runtime flow 如何從 memory 與 canonical state 中取回需要的資訊。

它回答：

- 不同 flow 應優先查哪些來源
- retrieval 的分層與 fallback 順序
- 何時該查 derived summary，何時該查 raw history
- 何時允許 transcript fallback
- 哪些任務需要 typed retrieval，哪些需要 semantic retrieval

**關於 Promotion 與 Demotion 規則**：請參閱 [L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md](./L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md)。

---

## 2. 核心原則

### 2.1 先 typed，後 semantic

若有明確 object / view 可讀，應先讀 typed source。  
不要一開始就用語意搜尋亂撈。

### 2.1A Metadata-First, Semantic-Second

retrieval 應優先採：

- metadata / typed filters 先縮小候選
- semantic retrieval 再補足模糊 recall 或長尾案例

不建議把固定百分比權重寫死成單一演算法。

### 2.2 先 summary，後 raw

若已有可靠 derived summary，先用 summary。  
只有當 summary 不足時，才回頭抓 raw history。

### 2.2A `sources.jsonl` Metadata-First Lookup

`sources.jsonl` 是 provenance / audit surface，不是一般 Manager prompt 的全文 RAG corpus。

Allowed lookup path:

1. `source_ref` / scope / record id / source kind metadata filter.
2. bounded evidence span read when the current tool path is review, debug, or why-memory.
3. return compact source metadata and evidence snippets with source refs.

Forbidden default behavior:

- general Manager retrieval may not dump raw transcript text into context.
- recommendation / rescue / proactive may not treat `sources.jsonl` as a free-form semantic search pool before reading `MemoryRecord` and compact surfaces.
- prompt-like text inside source evidence cannot issue instructions or create memory by itself.

Raw/full source drilldown is only for review/debug/why-memory flows and must be separately labeled in traces.

### 2.3 retrieval 必須 task-specific

不同 flow 的 retrieval policy 應不同。  
intake、recommendation、calibration、rescue 不應共享同一套亂序檢索。

### 2.4 先 scope，再檢索

retrieval candidates 應先依：

- user
- surface
- session / run type
- relevant task scope

收斂範圍，而不是把所有來源當成單一 global pool。

### 2.5 Selector / Reranker Layer

retrieval 不應預設把大量候選直接交給主模型。

建議採：

- first-stage retrieval
- second-stage selector / reranker
- final context pack

第二階段可採的形式包括：

- `rule-based reranker`
- `embedding reranker`
- `micro-LLM selector`

這三者都屬合法設計；是否使用哪一種，應依 bucket、延遲、成本、與資料型態決定，而不是在本層先寫死。

---

## 3. Retrieval Source Classes

### 3.1 Canonical State Retrieval

直接讀 `L2` canonical objects。

### 3.2 Derived View Retrieval

讀 memory / runtime summary views。

### 3.3 Transcript Retrieval

讀最近對話摘要或必要片段。

### 3.4 Semantic Retrieval

只有在 typed linkage 不夠時，才用於：

- historical recall
- similar pattern lookup
- long-range conversation fallback

---

## 4. Intake Retrieval Policy

優先順序：

1. `ActiveMealView`
2. `RecentCommittedMealsView`
3. selected typed meal records
4. `PersonalMealTemplateSummary` / `ReusablePersonalMealView`（future）
5. recent transcript
6. semantic fallback

規則：

- intake 不應先查全量 transcript
- 若有 active thread candidate，優先走 typed linkage
- `PersonalMealTemplateSummary` 只應在使用者範圍、且目前 utterance 合理地像是在指向「以前那份固定餐」時才進入候選。
- `PersonalMealTemplateSummary` 的角色是提供 reuse / confirm / re-estimate 候選，不是直接 commit authority。
- 若存在較新的 canonical meal thread、active draft、pending correction target，應優先用目前 turn / current-day typed context，而不是跳到 cross-session personal meal reuse。
- personal meal template 不得覆蓋 exact FoodDB evidence；若 current turn 明顯在說品牌 exact item，仍應先走 evidence / packet 路徑。

---

## 5. Recommendation Retrieval Policy

優先順序：

1. `CurrentBudgetView`
2. `ActiveBodyPlanView`
3. `PreferenceProfileSummary`
4. `GoldenOrderSummary`（從 canonical history materialized 的 derived view，見 L4D）
5. source pool（favorites / nearby / defaults）
6. transcript fallback

規則：

- recommendation 優先讀偏好摘要，不讀全量 meal history
- location 可用時再啟用 nearby retrieval
- **Golden Order**：是 materialized view，不是 promotion 結果，用於硬約束過濾 + 高優先候選
- **Temporary Preference**：需檢索並在 context 中呈現，過期後不返回

---

## 6. Calibration Retrieval Policy

優先順序：

1. `ActiveBodyPlanView`
2. `BodyObservation` window summary
3. `IntakeCompletenessSummary`
4. `AdherenceSummary`
5. `CalibrationHistorySummary`
6. recent rescue history

規則：

- calibration 不應優先吃 transcript
- calibration 判斷以 structured history 為主

---

## 7. Rescue Retrieval Policy

優先順序：

1. `CurrentBudgetView`
2. `RecentCommittedMealsView`
3. `RescueHistorySummary`
4. `AdherenceSummary`
5. `OpenProposalsView`

規則：

- rescue 是短期操作層，不應讀過長歷史
- 只需最近幾日的 relevant posture

---

## 8. Proactive Retrieval Policy

優先順序：

1. `ProactiveStatusView`
2. `SuppressionSummary`
3. task-specific summary
4. recent outcome history

規則：

- proactive 一定要先查 suppression / cooldown
- **Temporary Preference**：需檢索 active 的 temporary preference，過期的不返回

---

## 9. Negative Preference Filtering

所有 retrieval 之後，應進行負面偏好過濾：

### 9.1 過濾優先級

1. **Confirmed Negative**（最高權重）
   - 使用者明確說「不吃牛肉」「對花生過敏」
   - 必須過濾，無例外

2. **Inferred Avoidance**
   - 系統從行為推斷（連續拒絕 3 次奶茶推薦）
   - 應過濾

3. **Temporary Constraint**
   - 帶 valid_until 的 временный 限制
   - 只在有效期內過濾

### 9.2 過濾時機

- Recommendation：生成候選後、最終回覆前
- Proactive：觸發前檢查
- Intake：記錄時檢查（避免記錄使用者明確不要的）

---

## 10. Retrieval Fallback Policy

### 10.1 transcript fallback

只有在：

- typed source 不足
- summary 無法回答
- 使用者明顯指向歷史對話內容

時才應使用。

### 10.2 semantic fallback

只有在：

- 需要 long-range historical recall
- 需要找相似 past pattern
- 沒有更可靠 typed key

時才應使用。

### 10.2A second-stage selection

當 first-stage retrieval 已經縮出候選集合後，若候選仍過多，應允許 second-stage selection。

目標是：

- 讓主模型只看到少量高相關結果
- 降低 context 汙染
- 提高 prompt 專注度

規則：

- `rule-based reranker` 適合高 precision metadata / policy-driven case
- `embedding reranker` 適合 similarity-heavy case
- `micro-LLM selector` 適合需要語意判斷但不想直接讓主模型吃全部候選的 case

不應一開始就讓主模型看到 50-100 筆混雜記憶。

### 10.3 freshness-aware retrieval

retrieval 應優先較新的 pattern / summary，但不能完全忽略已確認的長期偏好。

也就是：

- fresh pattern memory 優先
- confirmed memory 權重更穩
- stale pattern 若與當下口頭聲明衝突，應降權

### 10.4 當下口頭聲明的優先權

若使用者在當前 turn 明確表示：

- 我最近不喝這個了
- 我現在不想吃這種
- 我今天不想被提醒

則 retrieval / ranking 應讓當下口頭聲明優先於歷史統計。

---

## 11. v1 Default Decisions

1. semantic retrieval 最小適用場景：
   - phrase mismatch 明顯
   - 使用者提到模糊歷史偏好
   - 需要從 transcript / long-tail memory 補回弱結構化資訊
   - 純 typed exact lookup 可解決時，不應優先走 semantic retrieval
2. transcript fallback 最大時間窗：
   - 預設僅看最近 `14` 天
   - 若有明確 historical correction / long-memory task，可再擴到 `30` 天，但需先經 typed / summary retrieval 失敗
3. recommendation source pool 檢索上限：
   - first-stage candidate pool 預設上限 `25`
   - second-stage selector / reranker 輸入上限 `12`
   - 主模型最終 context 中的 recommendation candidate 預設不超過 `5`

---

## 12. v1 Second-Stage Selector 選擇表

second-stage selector / reranker 的形式應依 flow 特性選擇，不應全局統一。

| Flow | 建議 selector 形式 | 理由 |
|------|-------------------|------|
| `intake` | rule-based reranker | intake 的 evidence 選擇以 typed linkage 為主，policy-driven 優先；不需要語意相似度 |
| `recommendation` | embedding reranker | candidate 排序需要偏好相似度，embedding 適合 soft preference matching |
| `calibration` | rule-based reranker | calibration 的 retrieval 以 structured summary 為主，policy gate 決定優先序 |
| `rescue` | rule-based reranker | rescue 的 retrieval 範圍窄且 policy-driven，不需要語意搜尋 |
| `proactive` | rule-based reranker | suppression / cooldown 是 deterministic policy，不需要語意排序 |

補充規則：

- `micro-LLM selector` 保留為 recommendation flow 的 optional upgrade path，當 embedding reranker 無法處理複雜 soft preference tradeoff 時才啟用
- v1 不預設啟用 `micro-LLM selector`，避免增加延遲與成本
- 若某 flow 的 first-stage retrieval 結果已足夠少（≤ 5 筆），可跳過 second-stage，直接進 context pack

---

## 13. Web Search Retrieval Policy（search_official_nutrition）

`search_official_nutrition` 是特殊的 retrieval tool，需要額外的 policy：

### 13.1 搜尋策略

1. **先抓候選**：一次搜尋，取 top 5 結果
2. **做 evidence policy gate**：對每個候選做以下判斷：
   - `evidence_tier`：`exact` / `near-exact` / `generic` / `unusable`
   - `source_type`：`official` / `menu` / `nutrition blog` / `user forums`
   - `serving_basis`：`每份` / `每 100g` / `一杯` / `一份套餐`
   - `identity_confidence`：`high` / `medium` / `low`
   - `customization_slots_present`：糖量、冰量、杯型、加料
3. **分類候選**：
   - `exact`：直接當 exact 證據
   - `near-exact`：當 anchor prior，需標記 `identity_confidence`
   - `generic`：當 high-variance family，需特別處理
   - `unusable`：忽略

### 13.2 搜尋結果處理

**不應該**：
- 只看第一個看起來可信的來源就收
- 直接把搜尋結果當 exact 證據
- 忽略 serving size 的差異（如「每份」vs「每 100g」）

**應該**：
- 先抓候選做 identity/applicability gate
- 標記 `evidence_tier` 和 `identity_confidence`
- 對 high-variance food family 做特別處理
- 資訊不足時，讓 manager ask followup 而不是 finalize

### 13.3 搜尋失敗處理

如果搜尋結果：
- 全部是 `unusable`：讓 manager ask followup
- 全部是 `generic`：讓 manager ask followup 或用 high-variance policy
- 有 `near-exact` 但 `identity_confidence=low`：讓 manager ask followup

### 13.4 搜尋頻率限制

- 單次 request 最多 2 次搜尋（1 次初始 + 1 次 refine）
- 超過 2 次代表 identity resolution 不收斂，應該 ask followup

---

## 14. Memory Tool Facade And Retrieval Selection

Long-term memory retrieval 應透過產品擁有的 tool facade，而不是直接暴露外部 framework API。Hermes、OpenClaw、Mem0、Hindsight、Graphiti、Letta、memU 的 search / recall / provider / graph 實作只能作為 reference。

V1 tool facade 至少包含：

| Tool | 主要用途 | 必要 guardrail |
|---|---|---|
| `memory.search` | 查 promoted memory 與可用於產品行為的 scoped summaries | scope keys 必填；先 metadata/typed filter；不得回傳 raw transcript |
| `memory.get` | 依 memory id 或 source ref 讀單筆記憶與 provenance | 必須帶 source refs、freshness、validity；不得把 memory 當 canonical truth |
| `conversation_recall.search` | 查過去對話摘要、atomic blocks、source refs | 只做 recall context；不是 durable memory promotion；raw transcript 預設禁止 |
| `memory.propose` | 從 runtime trace、user statement、dogfood replay 建立 candidate | 建立候選，不完成 promotion |
| `memory.review` | 對 candidate 做 promote/reject/delete/forget decision | 需符合 L4D；LLM 不可單獨完成 promotion |

Default retrieval pipeline:

1. `scope_filter`：先依 user/workspace/project/surface/session/run/task 收斂。
2. `canonical_state_first`：若問題可由 MealThread、FoodDB、BodyBudget、ledger、ProposalContainer 回答，先讀 canonical state。
3. `memory_surface_lookup`：讀 `user.md` / `memory.md` / `sources.jsonl` / `daily` / `review` 的 structured summaries。
4. `keyword_or_typed_retrieval`：對 exact ids、store/item aliases、negative blockers、golden order、source refs 先走 deterministic path。
5. `semantic_or_vector_retrieval`：僅在 typed/keyword 不足、需要 fuzzy recall 或 long-tail pattern 時啟用。
6. `selector_or_reranker`：依 flow 選 rule-based、embedding、或 micro-LLM selector。
7. `context_pack`：只輸出 L4C context pack，不直接改 Manager decision 或 canonical state。

`sources.jsonl` selection rule:

- `memory_surface_lookup` may read `sources.jsonl` metadata, source refs, confidence, freshness, validity, and bounded evidence spans.
- The default output to Manager is a `MemoryRecord` / compact surface / source-ref packet, not raw source text.
- Full evidence drilldown must be explicitly requested by a review/debug/why-memory tool path and must preserve redaction and scope checks.

Lab branch rule:

- 在 isolated advanced product lab 中，以上 tools 可以註冊、被 Manager/lab runner 呼叫、並參與完整 recommendation/rescue/proactive/memory E2E。
- 合回 main/self-use V1 時，tool facade 必須可保持 dormant，除非有明確 activation PR。

Selection rule:

- V1 不預設大型 RAG 或 graph retrieval。只有當 fixture、simulated dogfood、或 live lab traces 證明 recall failure 是瓶頸，而不是 canonical state、packet policy、或 prompt synthesis 的問題，才升級到 vector/graph-heavy retrieval。
