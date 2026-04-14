# L4B Retrieval Policy Spec

## 1. 目的

這份 spec 定義各 runtime flow 如何從 memory 與 canonical state 中取回需要的資訊。

它回答：

- 不同 flow 應優先查哪些來源
- retrieval 的分層與 fallback 順序
- 何時該查 derived summary，何時該查 raw history
- 何時允許 transcript fallback
- 哪些任務需要 typed retrieval，哪些需要 semantic retrieval

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
4. recent transcript
5. semantic fallback

規則：

- intake 不應先查全量 transcript
- 若有 active thread candidate，優先走 typed linkage

---

## 5. Recommendation Retrieval Policy

優先順序：

1. `CurrentBudgetView`
2. `ActiveBodyPlanView`
3. `PreferenceProfileSummary`
4. `GoldenOrderSummary`
5. source pool（favorites / nearby / defaults）
6. transcript fallback

規則：

- recommendation 優先讀偏好摘要，不讀全量 meal history
- location 可用時再啟用 nearby retrieval

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

---

## 9. Retrieval Fallback Policy

### 9.1 transcript fallback

只有在：

- typed source 不足
- summary 無法回答
- 使用者明顯指向歷史對話內容

時才應使用。

### 9.2 semantic fallback

只有在：

- 需要 long-range historical recall
- 需要找相似 past pattern
- 沒有更可靠 typed key

時才應使用。

### 9.2A second-stage selection

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

### 9.3 freshness-aware retrieval

retrieval 應優先較新的 pattern / summary，但不能完全忽略已確認的長期偏好。

也就是：

- fresh pattern memory 優先
- confirmed memory 權重更穩
- stale pattern 若與當下口頭聲明衝突，應降權

### 9.4 當下口頭聲明的優先權

若使用者在當前 turn 明確表示：

- 我最近不喝這個了
- 我現在不想吃這種
- 我今天不想被提醒

則 retrieval / ranking 應讓當下口頭聲明優先於歷史統計。

---

## 10. v1 Default Decisions

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

## 11. v1 Second-Stage Selector 選擇表

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
