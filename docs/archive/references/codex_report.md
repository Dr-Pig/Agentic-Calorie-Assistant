# Codex Report: Text Meal Canary System Optimization

**Date**: 2026-03-31
**Subject**: Architectural Formalization & Observability Foundation (Phase 7 Completion)
**Status**: Ready for Regression Analysis

---

## 1. Executive Summary

我們已完成 `Text Meal Canary` 系統的 Phase 7 優化工作。本次更新的核心目標是**廢除補丁式邏輯 (Patch-logic)**，轉向**結構化觀測 (Structured Observability)** 與**通用型語意門控 (Generalized Identity Gate)**。系統現在能精確區分「模型能力不足」與「證據品質不佳」，並透過結構化指標驅動反饋迴路。

## 2. 關鍵架構變更 (Current Implementation)

### A. 結構化觀測指標 (The Metrics Dictionary)
在 `text_meal_trace_eval.py` 中，我們將原本過於依賴流程判斷的 `failed_layer` 重構為 `observable_metrics` 字典：
- **Boolean 指標**: 如 `is_intent_food_estimation_correct`, `local_evidence_identity_pass`。
- **Choice 指標**: 如 `LLM_followup_decision_quality` (`correctly_asked` / `blindly_guessed`)。
- **優勢**: 這讓後續的 Benchmarking 可以針對單一變因（如：Grounding 通過率）進行聚合分析，而非模糊的失敗歸因。

### B. 通用身份閘門 (Identity Gate 2.0)
針對「drink-002: 中杯拿鐵 vs 中杯珍奶」這類因修飾語高度重疊導致的幻覺匹配，我們實作了**非補丁式**的解決方案：
- **`get_clean_core` 邏輯**: 在 `knowledge_packets.py` 中，我們不再硬編碼品項清單，而是實作自動剝離品牌與 `modifiers` (大中杯、甜度) 的提取器。
- **核心比對**: 強制要求證據與輸入在「核心名詞」上有實質交集。這確保了系統能 amplify 模型對食物主體的理解，同時由確定性代碼封堵最危險的跨品項幻覺。

### C. 邏輯邊界對齊 (Logic Alignment)
優化了 `text_meal.py` 的 Prompt 工程與上下文注入：
- **證據優先權**: 明確 `Exact Item` 證據位階高於 `Meal Template`。
- **診斷建議注入**: 將 Risk Gate 發現的缺失，以 `High-value diagnostic suggestions` 的形式餵給 LLM，讓模型自主決定追問策略，而非由代碼強制攔截（除了紅線區）。

## 3. 重要發現 (Key Findings)

1.  **修飾語噪音**: 許多 Grounding 失敗並非因為搜尋沒搜到，而是因為常見修飾語（如：中杯、去冰）在向量或字串比對中佔權重過高。透過「核心名詞提取」可大幅提升 Branded Items 的匹配精度。
2.  **LLM 診斷能力**: 當我們給予模型明確的「診斷建議」而非「錯誤阻斷」時，模型在 `clarify_before_estimate` 的決策上表現更為自然，減少了生硬的系統回覆感。
3.  **觀測成本**: 結構化指標增加了單次追蹤的維護成本，但大幅降低了分析 Benchmarking 失敗原因的人力開發成本。

## 4. 給 Codex 的後續執行建議 (Next Steps)

1.  **反饋迴路維護**: 執行 `python run_val.py` 時，應重點關注 `north_star_evaluation` 中的 `observable_metrics`。
2.  **Modifiers 擴充**: `knowledge_packets.py` 中的 `modifiers` 目前僅包含常見飲料與杯量，未來擴展到 `meal-001` (如：加飯、加麵) 時需同步更新。
3.  **Zero-Kcal Guard**: 目前救援層 (Rescue Layer) 已與 metrics 對接，若 `rescue_reason` 出現 `zero_kcal_candidate` 頻率過高，需檢視 Layer 3 的推理強度。

---
> [!IMPORTANT]
> **北極星方針提醒**: 
> 所有的優化都必須符合 `agent.md` 中的「耐用架構 (Durable Architecture)」原則。避免為了修正單一模型在特定品項上的弱點而增加代碼複雜性。

**報告完畢。系統已準備好進行下一波擴展。**
