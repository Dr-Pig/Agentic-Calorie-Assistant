# Memory Architecture: 記憶機制設計決策文件

> 本文件紀錄了在多輪對話熱量估算建置過程中，對於系統記憶機制的分析、判斷與結論。
> 所有架構選擇皆遵循 [SOURCE_OF_TRUTH.md](./SOURCE_OF_TRUTH.md) 的減法原則與 Prompt-over-Code 精神。

---

## 1. 記憶層級定義

### L1 — 行為紀錄 (MealLog)

**用途**：儲存每一筆飲食估算的結構化結果。

MealLog 是系統中唯一的「事實來源」。不論一筆紀錄是「資訊不全的草稿」還是「已完成的正本」，
它本質上都是同一張表中的同一種實體，只是狀態不同。

- `draft`：資訊不全，系統正在等待用戶補充（例如還沒告知份量）。
- `completed`：估算完成，已落地。
- `superseded`：被後續的修正紀錄覆蓋，保留作為歷史溯源。

**版本鏈 (Version Chain)**：每筆 MealLog 可透過 `parent_log_id` 指向它所取代的前一筆紀錄，
形成一條可審計的修正歷史。

### Message Buffer — 對話脈絡

**用途**：儲存最近 N 輪的原始對話訊息（用戶說了什麼、系統回了什麼）。

這是 Planner 判斷意圖的核心依據。MealLog 存的是結構化的估算結果，
但 Planner 需要看到的是「對話過程」才能做出正確的意圖判斷。

例如：
- 系統問：「大碗還是小碗？」
- 用戶答：「大碗」
- → 如果 Planner 只看到 MealLog `{title: "滷肉飯", kcal: 0}`，它無法理解「大碗」的語義。
- → 如果 Planner 同時看到 Message Buffer 中的對話，它能正確判斷「大碗」是在回答系統的追問。

**設計原則**：
- 極簡結構：`(user_id, role, content, timestamp)`。
- 有限長度：只保留最近 10 條訊息。超過自動丟棄最舊的。
- 唯讀注入：每次 Planner 執行前打包為文字注入 system prompt。
- 不做解析：純原始文字。所有語義判斷交給 LLM。

### L3 — 用戶畫像 (MemorySignal / Hypothesis)

**用途**：跨天際線的長期偏好與行為模式（例如：不吃牛、正在減脂、習慣不喝含糖飲料）。

參考 `line-liff-calorie-helper-main` 的 `MemorySignal` 與 `MemoryHypothesis` 設計。
此層級在多輪估算建置階段暫不實作，待核心路徑穩定後加入。

---

## 2. 廢除的概念：L2 (ActiveContext)

### 結論：不需要獨立的 L2 層

經過分析，原本的 `ActiveContext`（用於儲存「正在進行中的對話解析狀態」）是架構上的冗餘：

1. **MealLog 已能覆蓋其功能**：一筆 `status="draft"` 的 MealLog 就等同於 ActiveContext。
   它記錄了「已解析的組件」與「還缺什麼資訊」。
2. **對話脈絡由 Message Buffer 提供**：Planner 判斷意圖不需要結構化的「解析中間態」，
   它只需要看到原始對話歷史就能自行推斷。
3. **減少資料同步問題**：維護 MealLog 與 ActiveContext 兩張表的一致性是不必要的複雜度。

### 遷移策略

- 刪除 `ActiveContext` 模型與所有相關資料庫函式。
- 在 `MealLog` 中新增 `status`, `parent_log_id`, `pending_question` 欄位。
- 在 `text_meal.py` 的持久化邏輯中，統一使用 MealLog 處理所有狀態。

---

## 3. 多輪估算的運作流程

```
用戶訊息 ──→ [Message Buffer 寫入]
                │
                ▼
         [Context Injection]
         打包：最近 10 條 Message Buffer
              + 最新 MealLog (若有)
                │
                ▼
         [Planner LLM]
         判定意圖：new_intake / refinement / modification
                │
                ▼
         [Primary LLM 解析]
         基於意圖 + 歷史 MealLog + 新輸入，產出結構化 JSON
                │
                ▼
         [MealLog 持久化]
         ├─ 資訊不全 → 寫入 draft MealLog
         ├─ 資訊完整 → 寫入 completed MealLog
         └─ 修正舊紀錄 → 舊的標記 superseded，新的寫入 completed
                │
                ▼
         [Message Buffer 寫入系統回覆]
```

---

## 4. 與 Main Repository 的對應關係

| Canary (本專案) | Main Repo (`line-liff-calorie-helper-main`) | 說明 |
|:---|:---|:---|
| `MealLog` (status: draft) | `MealDraft` | 資訊不全的草稿 |
| `MealLog` (status: completed) | `MealLog` | 已完成的正式紀錄 |
| `Message Buffer` | `ConversationTrace` | 原始對話歷史 |
| _(未來)_ `MemorySignal` | `MemorySignal` | L3 行為信號 |
| _(未來)_ `MemoryHypothesis` | `MemoryHypothesis` | L3 偏好假說 |

---

*本文件是記憶機制的設計決策紀錄，進行相關修改時請以此為參考。*
