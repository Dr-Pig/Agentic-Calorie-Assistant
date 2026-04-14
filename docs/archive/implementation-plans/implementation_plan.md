# OpenClaw-style Tool Calling for Canary Planner

這份計畫的目標是在 Canary 環境中，實體化我們討論的「B. Canary 實作 (微縮版 OpenClaw 工具鏈)」。
透過賦予 Planner 主動呼叫 `search_history` 的能力，我們可以直接在真實的對話情境中驗證 Tool Calling 與 Hybrid Context 組合的效能，藉此作為日後推廣到 Main Repo 的堅實基礎。

## User Review Required

> [!IMPORTANT]  
> 目前 Canary 依賴 `BuilderSpaceAdapter` 介接 LLM (`grok-4-fast` 或其他模型)。我們將需要修改 Adapter 來支援原生的 Tool Calling (Function Calling API)，並在 Planner 中實作一個簡易的 Agent Loop 來處理 `finish_reason == "tool_calls"`。
> 請問您目前的 `BUILDERSPACE_PLANNER_MODEL` 模型是否完整支援標準的 OpenAI/Gemini Tool Calling 格式？如果支援度不佳，我們可能需要做適當的降級（例如透過純 Prompt 讓模型輸出特定 JSON 指令來觸發工具）。

## Proposed Changes

---

### API Provider 擴充 (Tool Calling Support)

我們需要讓與 LLM 互動的底層支援 Function Calling。

#### [MODIFY] app/providers/builderspace_adapter.py
- 為 `complete_with_trace` 增加 `tools: list[dict] | None = None` 參數。
- 在 `request_payload` 中帶入 `tools` 欄位（如果有的話）。
- 當 LLM 回傳的 `finish_reason` 是 `"tool_calls"` 時，將原始的 tool call 指令作為例外或特殊封包回傳，讓上層知道需要執行工具。

---

### Function 定義與實作

將系統既有的查詢歷史功能封裝給 Planner 使用。

#### [NEW] app/application/tools.py
- **新增檔案**，定義 `search_history_tool` 的 JSON Schema，描述這項工具的功能：「調用此工具可獲取使用者最近的飲食紀錄與卡路里估算狀態，用於解決多輪對話的意圖」。
- 將原先寫在 `routes.py` 或 `database.py` 裡的 `get_meal_log_history` 結果格式化為給 LLM 看的文字或精簡 JSON。

---

### Planner Agent Loop (Tool Orchestration)

這是最核心的架構改動，將原本單次請求的 Planner 變成一個具備反思與操作能力的 Loop。

#### [MODIFY] app/usecases/text_meal.py
在處理 `planner_pass` 的流程中：
1. **第一次調用**：發送 System Prompt + User Payload，並帶上 `tools=[search_history_tool]`。
2. **條件判斷**：檢查 Planner 輸出的 `finish_reason`。
   - 如果是 `stop`，表示 Planner 不需要工具，直接給出 `TurnIntentResult` 就可以繼續。
   - 如果是 `tool_calls`，表示 Planner 想查歷史紀錄！
3. **工具執行與二次調用**：
   - 提取 Planner 指定的工具參數（例如要查幾筆）。
   - 呼叫 `database.py` 裡的 `get_meal_log_history`。
   - 將「歷史紀錄結果」串成 `role="tool"` 的對話紀錄放回 Context。
   - **發送第二次 Planner 調用**，此時 Planner 將能依照歷史軌跡，精準判定使用者說的「那改成雞肉好了」是在指哪一餐。

## Open Questions

> [!WARNING]  
> 1. **時間衰退 (Time Decay) & MMR 的複雜度**：在這個先鋒實驗中，您希望我們只使用基礎的 SQL Query (找最近 N 筆)，還是馬上引入 Vector Database 的 Hybrid Search 邏輯？建議先從「最近 N 筆的關聯式資料庫查詢」起步來驗證 Tool Calling 流程，之後再來替換大腦檢索演算法。
> 2. **Token 使用量估算**：如果每一次對話 Planner 都要去檢索歷史，Token 消耗可能會飆升。我們要不要讓 Planner 只有在判定「意圖似乎延續，但缺乏主體」時才發動 Tool？

## Verification Plan

### Automated Tests
- 新增/修改單元測試，模擬模型回傳 `tool_calls` 的 Payload，驗證 `text_meal.py` 是否會正確攔截並發動第二輪 Planner 呼叫。

### Manual Verification
- 使用純文字 UI 發起對話：「昨天晚上的牛肉拉麵」。系統回答熱量後，再次發送：「改成吃豚骨拉麵好了，然後不喝湯」。
- 在 Canary Insight Dashboard 觀察 Planner 的 Trace，確認是否有「Step 1: Planner 工具呼叫」、「Step 2: 查詢歷史」、「Step 3: Planner 正確輸出 modification 意圖並包含上下文」的三段式軌跡。
