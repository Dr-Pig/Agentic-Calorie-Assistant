# Workflow Dependency & Context Ordering Spec

## 1. 目的

本文件定義專案**「能力建置順序 (Capability Build Order)」的唯一真相來源 (Source of Truth)**。

我們的建置哲學是 **「核心相依性網路 (Core Dependency Network) 與 漸進式脈絡密度 (Context Density)」**，即：必須先擁有最基底的運算與資料真相，才能在上層疊加依賴這份真相的高階代理能力與 UI 介面。

所有執行計畫 (`implementation_plan.md`、`Master Build Map`、`Current Execution Plan`、`Re-plan Log` 等) 都只是這份藍圖在當下的「施工切片」，不具備最高決策權力。

它不取代施工控制工件；它只決定：

- 哪些 workflow 應先做
- 哪些 workflow 不可跳級
- 哪些 UI / memory / proactive 能力必須晚於哪些前置條件

---

## 2. 核心功能依賴建置順序 (Canonical Ordering)

系統建置必須嚴格依照以下順序由內而外擴展，不得跳級：

### 2.1 單回合錄入 (Single-turn Intake)
**定位：系統的最底層核心，所有資料的活水源頭。**
*   **前提：完全不需要依賴歷史記憶或其他模組。**
*   **內部 Lane 優先級**：
    1.  Simple provisional estimate (最簡單的粗略估算)
    2.  Exact DB item lane (精確的資料庫食物對比)
    3.  Clarify-required lane (無法辨識時的單次澄清)
    4.  Cannot-estimate lane (拒絕估算)
    5.  Web-search fallback lane (聯網搜索)

### 2.2 多回合與時態修正 (Multi-turn Intake + Correction)
**定位：強化單回合錄入的連續性。**
*   **依賴**：必須建立在 2.1 的單回合解析能力之上。
*   **包含**：
    *   Active meal continuation (一餐分多次紀錄)
    *   Historical correction (針對特定 `MealItem` 的事後修改)
    *   Cross-midnight attribution (跨午夜歸帳的處理)

### 2.3 今日狀態儀表板與讀取模型 (Today UI / Read Models)
**定位：錄入資料的視覺化呈現，以及 Ledger 真實性的初步檢驗。**
*   **依賴**：必須建立在 2.1 與 2.2 的 `MealThread` 與 `DayBudgetLedger` 穩定產出後。
*   **策略**：先做極粗糙的 UI (Low-Fi)，只要能將 Canonical Read Models 精準反映即可。

### 2.4 體重與身體觀測持久化 (Weight / Body Observation UI + Persistence)
**定位：啟動後續熱量校準與推薦引擎的第二資料源。**
*   **依賴**：與 2.1-2.3 平行，但必須優先於 Calibration 完成。
*   **策略**：讓體重資料能進系統，並被 Today/Summary UI 正確看見。

### 2.5 救援機制 (Rescue Mechanism)
**定位：發生爆卡時的數學與策略兜底。**
*   **依賴**：依賴 2.3 的 `DayBudgetLedger` 以及 15% 上限規則。
*   **特性**：先做純粹 deterministic (算數決定) 的 rescue overlay 與 safety floor，**絕對不依賴**完整的記憶系統。

### 2.6 校準系統 (Calibration Core)
**定位：透過觀察體重趨勢與熱量攝取，重新分配基底預算。**
*   **依賴**：強烈依賴 2.4 (體重穩定持久化) + 2.1 (攝取足夠完整) + 2.3 (Ledger 穩定)。這三大條件未滿前，不准開發校準。

### 2.7 記憶與檢索深化 (Memory / Retrieval Deepening)
**定位：為 Agent 的進階決策引入時間軸上下文。**
*   **依賴**：依賴前述所有的資料庫產出作為種子。
*   **包含**：
    *   Preference memory (偏好記憶)
    *   Negative memory (負面偏好與過敏紀錄)
    *   Golden orders (黃金常規餐點)
    *   Selector/Reranker (AI 選擇與重排序引擎)

### 2.8 推薦系統 (Recommendation)
**定位：依據記憶與現有餘額的主動建議。**
*   **依賴**：**被大幅延後。** 必須在 2.7 (Memory-aware) 與 2.5 (Rescue/Budget) 均完備後才可進場。這能保證推薦絕不會超越可用預算。

### 2.9 主動介入機制 (Proactive Nudges)
**定位：最強大的 Agentic 表現層。**
*   **依賴**：必須在所有功能 (含 UI) 就位後最後開發。不允許把 Proactive 提前混入 Intake 開發階段。
*   **包含**：Reminder、Rescue nudge、Recommendation nudge、Calibration nudge。

---

## 3. UI 策略正式化 (UI Strategy Rule)

UI 開發的唯一鐵律：**「UI 絕對不超前 Backend State，且永遠採粗入細出。」**

1.  **無預建 UI**：UI 不必等所有 AI 能力完備才一次出場，但 UI 只能以「反映後端 State Truth 與對應的 Read Model」為唯一目的被加入。
2.  **進場時機表**：
    *   `Today UI`：在 2.1 單回合 / 2.2 多回合 / Ledger 穩妥後才加。
    *   `Weight UI`：在 2.4 持久化穩妥後才加。
    *   `Recommendation UI`：在 2.8 Memory-aware 計算就緒後才加。
    *   `Proactive UI / Control Surface`：在 2.9 完備時才加。

---

## 4. 外部參考文獻使用規則 (External Reference Rules)

位在桌面環境 (`C:\Users\User\Desktop\agent runtime`) 中的各種開源 Agent Framework (OpenClaw, Claude Code etc.)，已被正式列為 **Reference Source**，但必須遵守以下界線：

1.  **僅限借鏡架構**：只允許參考其 Framework Selector、Runtime Architecture、Memory Packing 或 Failover Patterns。
2.  **Reference, not Truth**：外部資料夾永遠是參考書，不是法典。Repo 內的 Canonical Specs (L0-L6 與本文件) 永遠擁有最終否決權。
3.  **衍生決策必回寫**：若 Agent 因為外部參考而決定變更現有的實作架構，**不可直接寫程式**，必須先修改對應的 Repo Source of Truth 文件，通過審核後才能實作。

---

## 5. 真相來源同步鐵律 (Source-of-Truth Sync Rule)

這是一條針對所有接手本專案之 AI Agent 的硬性約定 (Hard Constraint)：

*   **當 Agent 在開發中遭遇以下情況時**：
    1.  改變了 Workflow 的優先順序或相依性理解 (Capability dependency)。
    2.  因外部參考 (External reference) 產生新的架構判斷。
    3.  發現 implementation planning 原始假設有誤。
*   **Agent 的唯一合法行動**：
    *   必須、立刻同步更新 `docs/specs/` 中對應的 Canonical Document (含本檔案)。
    *   **不允許** 只修改程式碼 / 執行計畫 (`task.md`) 而放任真相文件腐敗。
    *   **不允許** 下一個工作回合依賴「口頭或對話裡的約定」前進。所有共識必須落地成為 Spec 的文字。

*(此規則將被註記於 `agent.md` 及全局導航中。)*
