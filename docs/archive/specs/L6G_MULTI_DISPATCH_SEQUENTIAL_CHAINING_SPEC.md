# L6G Multi-Dispatch and Sequential Chaining Governance Spec

## 1. 目的

本文件定義全產品 chat-first agent 在單一 utterance 觸發多個 workflow 時的 **dispatch 治理規範**。

它回答：

- 什麼情況下一個 utterance 可以觸發多個 workflow
- 哪些 workflow 組合可以 parallel dispatch
- 哪些 workflow 組合必須 sequential（有 data dependency）
- 哪些 workflow 組合必須先確認再執行（confirm-then-chain）
- unified response pass 的責任邊界在哪裡
- 哪些差異不應該被升成 multi-dispatch，而應留在 response realization

本文件的定位是：

- **治理規範**
- 不是 production runtime contract
- 不是 multi-dispatch 的 implementation spec
- 不是對 L6F 的替換，而是 L6F 的延伸

它用來約束後續 slice（特別是 `2.7e workflow_routing_pass` 實作），避免把本來應由 response pass 自然處理的情況，過早硬編成 multi-dispatch 路徑。

---

## 2. 適用範圍與非目標

### 2.1 適用範圍

本文件適用於所有可能觸發多個 workflow 的 chat utterance，包括：

- compound utterance（一句話裡有兩個獨立意圖）
- sequential trigger（一個 workflow 完成後，狀態變化觸發下一個）
- confirm-then-chain（需要使用者確認才執行下一個 workflow）

### 2.2 非目標

本文件不直接定義：

- production multi-dispatch runtime implementation
- unified response pass 的 prompt contract
- workflow-specific pass graph 的內部結構
- proactive nudge 的觸發機制（屬於 2.9 Proactive Nudges）
- 跨 session 的 workflow chaining

### 2.3 與 L6F 的關係

L6F 定義了：

- 單一 workflow 的 routing 責任分層
- disposition vocabulary
- anti-premature-taxonomy rule
- deterministic gate 責任邊界

本文件補充的是：

- 當 router 識別出多個 intent 時，如何治理 dispatch 決策
- 哪些 workflow 組合允許 parallel，哪些必須 sequential
- unified response pass 的治理原則

本文件**不能**被解讀為：

- 允許繞過 L6F 的 anti-premature-taxonomy rule
- 允許 deterministic layer 決定 dispatch 模式
- 允許 response-side 差異升成 dispatch taxonomy

---

## 3. 核心治理原則

### 3.1 Dispatch 模式分類

全產品的 multi-intent utterance 只允許三種 dispatch 模式：

1. **Parallel Dispatch**：兩個 workflow 同時執行，各自完成業務邏輯，最後由 unified response pass 合併回覆
2. **Sequential Dispatch**：第二個 workflow 必須等第一個完成後才能執行，因為有 data dependency
3. **Confirm-then-Chain**：第一個 workflow 完成後，response pass 生成確認問句，等使用者確認後才觸發第二個 workflow

### 3.2 Parallel Dispatch 的合法條件

兩個 workflow 可以 parallel dispatch，當且僅當：

1. **寫入不同的 canonical object**：兩個 workflow 寫入的 canonical object 沒有重疊
2. **無 data dependency**：第二個 workflow 的輸入不依賴第一個 workflow 的輸出
3. **兩個都是 state-mutating 或兩個都是 read-only**：不允許一個 read-only workflow 讀取另一個 state-mutating workflow 尚未完成的 canonical state

違反上述任一條件，必須改用 Sequential Dispatch 或 Confirm-then-Chain。

### 3.3 Sequential Dispatch 的觸發條件

當以下任一條件成立時，必須使用 Sequential Dispatch：

- 第二個 workflow 需要讀取第一個 workflow 寫入的 canonical object
- 第二個 workflow 的 trigger condition 依賴第一個 workflow 的結果（例如：budget 超標後才觸發 rescue）
- 兩個 workflow 寫入同一個 canonical object（例如：兩個 intake 寫入同一個 MealThread）

Sequential Dispatch 的執行順序由 data dependency 決定，不由 router 的 disposition 決定。

### 3.4 Confirm-then-Chain 的觸發條件

當以下任一條件成立時，必須使用 Confirm-then-Chain，不得自動 chain：

- 第二個 workflow 涉及高影響力的 state mutation（例如：修改 BodyPlan 目標、建立 rescue proposal）
- 第二個 workflow 的觸發需要 threshold 判斷（例如：超標 X% 才觸發 rescue）
- 使用者的 utterance 沒有明確表達對第二個 workflow 的 intent（例如：只說「我體重掉了 1 公斤」，沒有說「幫我重新計算目標」）

Confirm-then-Chain 的確認問句由 response pass 生成，不由 deterministic layer 生成。

### 3.5 Anti-Auto-Chain Rule

正式硬規則：

> 不得在使用者未明確表達 intent 的情況下，自動 chain 到涉及高影響力 state mutation 的 workflow。

允許：

- 在 response 裡提示使用者「是否要重新計算目標」
- 在 response 裡提示使用者「是否要建立救援計畫」

禁止：

- 自動觸發 calibration（除非使用者明確說「幫我重新計算」）
- 自動觸發 rescue proposal 建立（除非使用者明確說「幫我建立計畫」）
- 自動觸發 recommendation（除非使用者明確說「幫我推薦」）

### 3.6 Immediate Feedback Rule

正式治理原則：

> 使用者說完話，必須立即有回應。不得因為等待 secondary workflow 完成而延遲主要回覆。

這意味著：

- Parallel Dispatch 的 unified response pass 可以等兩個 workflow 都完成後再回覆
- Sequential Dispatch 的第一個 workflow 完成後，必須立即有部分回覆，不得等第二個 workflow
- Confirm-then-Chain 的確認問句必須在第一個 workflow 完成後立即出現

---

## 4. Workflow 組合合法性矩陣

### 4.1 Parallel Dispatch 合法組合（V1）

| Primary | Secondary | 合法？ | 原因 |
|---|---|---|---|
| `intake` | `body_observation` | ✅ | 寫入不同 object（MealLog vs BodyObservation），無 dependency |
| `intake` | `general_chat`（讀 body plan）| ✅ | general_chat 讀 ActiveBodyPlanView，不依賴 intake 結果 |
| `body_observation` | `intake` | ✅ | 同上，對稱 |
| `intake` | `general_chat`（讀 budget）| ❌ | general_chat 需要 intake 後的 budget，有 dependency |
| `intake` | `rescue` | ❌ | rescue 依賴 intake 後的 budget，且需要 threshold 判斷 |
| `intake` | `calibration` | ❌ | calibration 需要 confirm-then-chain |
| `rescue` | `calibration` | ❌ | 兩個都是高影響力 state mutation，需要分別確認 |

### 4.2 Sequential Dispatch 合法組合（V1）

| First | Second | 觸發條件 |
|---|---|---|
| `intake` | `general_chat`（讀 budget）| intake 完成後，budget 更新，general_chat 才能讀到正確數字 |
| `body_observation` | `general_chat`（讀 body plan）| body_observation 完成後，如果 body plan 有更新，general_chat 才能讀到 |

### 4.3 Confirm-then-Chain 合法組合（V1）

| First | Second | 確認問句觸發條件 |
|---|---|---|
| `body_observation` | `calibration` | 使用者沒有明確說「幫我重新計算目標」 |
| `intake`（超標）| `rescue` | 超標比例超過 threshold，且使用者沒有明確說「幫我建立計畫」 |
| `intake` | `recommendation` | 使用者沒有明確說「幫我推薦」 |

### 4.4 不允許作為 Secondary Intent 的 Workflow

以下 workflow 不允許作為 secondary intent，只能作為 primary intent：

- `calibration`：高影響力 state mutation，必須獨立觸發
- `rescue`（proposal 建立）：需要 threshold 判斷 + 使用者確認
- `recommendation`：需要使用者明確表達 intent

---

## 5. Router 輸出擴充治理

### 5.1 Router 輸出的擴充

`workflow_routing_pass`（定義於 L6F §11.2）的輸出需要擴充以支援 multi-dispatch：

**擴充後的 `WorkflowRoutingResult`**：

- `routing_mode`：`single` / `compound`
- `primary_workflow`：原有的 `WorkflowRoutingResult`（target_workflow_family + disposition + routing_confidence + ambiguity_posture）
- `secondary_intents[]`：只在 `routing_mode = compound` 時有值
  - `family`：workflow family
  - `disposition`：disposition
  - `dispatch_type`：`parallel` / `sequential` / `confirm_then_chain`
  - `dependency_on_primary`：`none` / `budget` / `body_plan`（說明 dependency 的來源）

### 5.2 Router 的 compound 識別規則

Router 識別 compound utterance 的條件：

- utterance 裡有兩個明確的、語意上獨立的 intent
- 兩個 intent 分別對應不同的 workflow family
- 兩個 intent 都有足夠的 routing_confidence（不得在 ambiguity 狀態下識別 compound）

Router 不得識別 compound 的情況：

- 其中一個 intent 的 routing_confidence 是 `low`
- 兩個 intent 對應同一個 workflow family（例如：兩個 intake）
- utterance 只是語氣上帶有兩個動詞，但語意上只有一個 intent

### 5.3 Router 的 dispatch_type 決定規則

Router 決定 `dispatch_type` 的規則：

1. 先查 §4.1 合法性矩陣，確認是否允許 parallel
2. 如果不允許 parallel，查 §4.3 是否需要 confirm-then-chain
3. 如果不需要 confirm-then-chain，使用 sequential
4. 如果組合不在矩陣裡，預設使用 confirm-then-chain（保守原則）

---

## 6. Unified Response Pass 治理

### 6.1 定位

Unified Response Pass 是 multi-dispatch 模式下的最終回覆生成層。

它的責任是：

- 讀取所有已完成 workflow 的結果
- 讀取更新後的 canonical context（budget、body plan 等）
- 生成一個自然、連貫的回覆，涵蓋所有 intent 的結果
- 在 confirm-then-chain 模式下，生成確認問句

它不做：

- 不重新執行任何 workflow 的業務邏輯
- 不做 state mutation
- 不決定 dispatch 模式（那是 router 的責任）

### 6.2 Unified Response Pass 的 context 讀取規則

- Parallel Dispatch：等所有 workflow 完成後，讀取最新的 canonical context
- Sequential Dispatch：等 primary workflow 完成後，讀取更新後的 canonical context，再執行 secondary workflow，最後生成回覆
- Confirm-then-Chain：只讀取 primary workflow 的結果，生成確認問句，不讀取 secondary workflow 的結果

### 6.3 Unified Response Pass 的回覆原則

- 回覆必須自然連貫，不得像是兩個獨立回覆的拼接
- 回覆必須反映最新的 canonical state（intake 後的 budget，而不是 intake 前的）
- 確認問句必須清楚說明「如果確認，系統會做什麼」
- 不得在確認問句裡預設使用者會同意

---

## 7. Threshold Governance

### 7.1 Rescue Threshold

Rescue 的 confirm-then-chain 觸發 threshold 由 canonical spec 定義，不由本文件定義。

本文件只定義：

- threshold 必須是 deterministic 計算，不得由 LLM 判斷
- threshold 超過時，response pass 生成確認問句，不自動建立 proposal
- threshold 未超過時，不得在 response 裡提示 rescue

### 7.2 Calibration Trigger

Calibration 的 confirm-then-chain 觸發條件：

- 使用者明確說了體重變化（body_observation 寫入）
- 且使用者沒有明確說「幫我重新計算目標」

此時 response pass 可以提示「是否要根據新體重重新計算目標」，但不自動執行。

---

## 8. 與既有真相文件的關係

### 8.1 與 L6F

L6F 定義了單一 workflow 的 routing 治理。

本文件補充了多 workflow 的 dispatch 治理。

兩份文件共同構成完整的 routing 治理規範。

L6F 的所有規則（anti-premature-taxonomy、LLM-led、deterministic-carve-out）在 multi-dispatch 模式下同樣適用。

### 8.2 與 L6E

L6E 定義了 graph-first、decision-mode annotation。

本文件的 dispatch 模式決定（parallel / sequential / confirm-then-chain）屬於 router 的 decision，decision mode 是 `llm`，不是 deterministic。

### 8.3 與 2.7e

`2.7e` slice 是 `workflow_routing_pass` 的 production implementation。

本文件定義的 router 輸出擴充（§5.1）是 `2.7e` 的實作目標之一。

本文件不強迫 `2.7e` 同時實作所有 dispatch 模式。`2.7e` 可以先實作 single dispatch，再逐步擴充 compound dispatch。

### 8.4 與 2.9 Proactive Nudges

本文件的 confirm-then-chain 模式是 **使用者主動觸發** 的 chaining。

Proactive Nudges（2.9）是 **系統主動觸發** 的 chaining，屬於不同的治理範疇。

兩者不得混用。

---

## 9. Implementation Rule

當後續 slice 涉及：

- multi-intent utterance 的 routing
- workflow chaining 或 sequential execution
- unified response 的生成

至少應對照本文件檢查：

1. 這個組合是否在 §4 的合法性矩陣裡
2. dispatch_type 是否正確（parallel / sequential / confirm-then-chain）
3. unified response pass 是否只做回覆生成，不做業務邏輯
4. 是否違反 §3.5 的 anti-auto-chain rule
5. 是否違反 §3.6 的 immediate feedback rule

若未完成此檢查，則該 slice 的 multi-dispatch 設計視為未完整定義。

---

## 10. Open Questions（待後續 slice 決定）

以下問題目前尚未拍板，不得寫進 eval pack 或 runtime contract：

- Parallel Dispatch 的最大 secondary intent 數量（v1 建議限制為 1）
- Sequential Dispatch 的 timeout 處理（primary workflow 超時時，secondary 如何處理）
- Compound utterance 的 routing_confidence threshold（低於多少時，降級為 single dispatch）
- Unified Response Pass 是否需要獨立的 LLM pass，還是可以由 primary workflow 的 response pass 承擔
