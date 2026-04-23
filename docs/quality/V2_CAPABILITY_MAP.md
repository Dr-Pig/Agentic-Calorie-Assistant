# V2 Capability Map

## 目的

本文件定義系統的能力邊界（Capability Boundaries），將龐大的攝取記錄功能拆解為可獨立開發現、可獨立測試的 Capability Bundles。

每個 Bundle 有明確的：
- 目標與責任
- 輸入與輸出
- 與其他 Bundle 的介面
- 可測試的 Functional Checks
- 可測試的 Quality Checks
- 典型失敗模式

---

## 設計原則

1. **Outcome-first** - 每個 Bundle 以「使用者最終得到什麼」為導向
2. **Interface清晰** - Bundle 之間透過結構化資料溝通，不是自由文字
3. **可測試性** - Functional Checks 可用程式自動判定，Quality Checks 可用 LLM Judge 或人工判定
4. **分層而非重疊** - 每個 Bundle 有明確的「負責」與「不負責」

---

## Bundle 總覽

| Bundle ID | Bundle 名稱 | 核心職責 | 依賴 |
|-----------|-------------|----------|------|
| B1 | Routing / Decision | 判斷輸入應該走哪條 lane | 無 |
| B2 | Exact Item Grounding | 在知識庫中找到精確匹配 | B1 |
| B3 | Generic Estimation | 對無精確匹配的食物進行熱量估計 | B1, B2 |
| B4 | Clarify / Follow-up Decision | 判斷是否需要追問使用者 | B1, B2, B3 |
| B5 | Retrieval / Search | 搜尋知識庫找到相關參考資料 | B1 |
| B6 | Nutrition Math + State Sync | 計算熱量並同步狀態到資料庫 | B2, B3, B4 |
| B7 | Final Response Rendering | 生成最終回覆給使用者 | B6 |

---

## Bundle 詳細定義

### B1: Routing / Decision

#### 目的
根據使用者輸入，判斷應該走哪條處理 lane（exact_lookup, estimate_with_followup, ask_followup_only, direct_estimate）。

#### 輸入
```json
{
  "user_input": "string",
  "conversation_context": {
    "previous_turns": [],
    "current_thread_id": "string"
  },
  "user_profile": {
    "has_onboarded": "boolean"
  }
}
```

#### 輸出
```json
{
  "route": "exact_lookup | estimate_with_followup | ask_followup_only | direct_estimate",
  "confidence": "high | medium | low",
  "reasoning": "string",
  "extracted_items": [
    {
      "name": "string",
      "quantity": "number",
      "unit": "string",
      "modifiers": []
    }
  ],
  "uncertainty_signals": ["string"]
}
```

#### 責任範圍
- 解析使用者輸入中的食物名稱、數量、修飾詞
- 判斷是否有足夠資訊進行估計
- 識別不確定性信號（模糊詞彙、範圍描述）

#### 非責任範圍
- 不負責熱量計算
- 不負責知識庫搜尋
- 不負責生成回覆文字

#### 與其他 Bundle 的介面
- 輸出 `extracted_items` 給 B2, B3
- 輸出 `uncertainty_signals` 給 B4

#### Functional Checks
- [ ] 輸入「星巴克冰那堤大杯」→ route = exact_lookup
- [ ] 輸入「珍珠奶茶」→ route = estimate_with_followup 或 ask_followup_only
- [ ] 輸入「滷味」→ route = ask_followup_only
- [ ] 輸入「我吃滷味點了王子麵、豆皮、甜不辣」→ route = direct_estimate
- [ ] confidence 等級與輸入資訊完整度匹配

#### Quality Checks
- [ ] reasoning 是否有清楚解釋為何選擇該 route
- [ ] extracted_items 是否正確解析食物名稱
- [ ] uncertainty_signals 是否捕捉到模糊描述

#### 典型失敗模式
- 把需要追問的輸入當成可估計（overclaim）
- 把可精確查找的輸入當成需要估計（underclaim）
- 數量解析錯誤（把「兩碗」解析成「一碗」）
- 遺漏修飾詞（糖度、杯型、大小）

---

### B2: Exact Item Grounding

#### 目的
在知識庫中找到與使用者輸入完全匹配的食物項目，驗證是否為同品項。

#### 輸入
```json
{
  "extracted_items": [
    {
      "name": "string",
      "quantity": "number",
      "unit": "string",
      "modifiers": []
    }
  ],
  "preferred_evidence_tier": "tier_1_exact_verified | tier_2_anchored | tier_3_heuristic"
}
```

#### 輸出
```json
{
  "grounded_items": [
    {
      "original_name": "string",
      "matched_name": "string",
      "calories": "number",
      "macros": {
        "protein": "number",
        "fat": "number",
        "carbs": "number"
      },
      "evidence_tier": "string",
      "is_exact_match": "boolean",
      "rejection_reason": "string | null"
    }
  ],
  "unmatched_items": [
    {
      "name": "string",
      "reason": "string"
    }
  ]
}
```

#### 責任範圍
- 搜尋本地知識庫（exact_item_cards_tw.json）
- 驗證匹配是否為同品項（不是 sibling variant）
- 區分 exact match 與 anchored match

#### 非責任範圍
- 不負責估計未匹配的項目
- 不負責決定是否需要追問

#### 與其他 Bundle 的介面
- 接收 B1 的 extracted_items
- 輸出 grounded_items 給 B6
- 輸出 unmatched_items 給 B3

#### Functional Checks
- [ ] 輸入「星巴克冰那堤大杯」→ 找到 189 kcal（台灣星巴克官方值）
- [ ] 輸入「大麥克」→ 找到 503.17 kcal（台灣麥當勞官方值）
- [ ] 輸入「星巴克冰那堤」→ 不應回覆 exact，應回傳需要追問杯型
- [ ] 輸入「Subway火腿潛艇堡」→ 不應匹配到照燒雞肉版本
- [ ] 輸入「松屋特盛牛丼」→ 找到 1237 kcal

#### Quality Checks
- [ ] 是否優先使用本地知識庫
- [ ] 是否正確區分 exact 與 anchored
- [ ] 是否正確拒絕 sibling variant 作為 exact match

#### 典型失敗模式
- 用 sibling variant 替代（用中杯數值回覆大杯輸入）
- 遺漏本地知識庫中的品項
- 把 anchored 當成 exact 標記

---

### B3: Generic Estimation

#### 目的
對無法精確匹配的項目，根據結構化錨點進行熱量估計。

#### 輸入
```json
{
  "unmatched_items": [
    {
      "name": "string",
      "quantity": "number",
      "unit": "string",
      "modifiers": []
    }
  ],
  "context": {
    "is_shared_meal": "boolean",
    "meal_type": "breakfast | lunch | dinner | snack"
  }
}
```

#### 輸出
```json
{
  "estimated_items": [
    {
      "name": "string",
      "calories": {
        "min": "number",
        "max": "number",
        "center": "number"
      },
      "exactness": "anchored | heuristic",
      "anchor_basis": "string",
      "uncertainty_preserved": "boolean"
    }
  ]
}
```

#### 責任範圍
- 根據常見營養資料進行 anchored estimate
- 提供合理的熱量範圍而非單一數字
- 保留不確定性（不假裝精準）

#### 非責任範圍
- 不負責精確查找
- 不負責決定是否需要追問

#### 與其他 Bundle 的介面
- 接收 B2 的 unmatched_items
- 輸出 estimated_items 給 B6

#### Functional Checks
- [ ] 輸入「珍珠奶茶半糖去冰」→ 範圍 480-500 kcal，center 490
- [ ] 輸入「水餃10顆」→ 範圍 520-600 kcal，center 560
- [ ] 輸入「拉麵」→ 範圍 450-1100 kcal，並追問
- [ ] 輸入「鷹流拉麵2929豚骨拉麵」→ 範圍 1250-1300 kcal（利用品牌訊號）
- [ ] 輸入「咖哩飯」→ 範圍 700-850 kcal，並追問配料

#### Quality Checks
- [ ] 是否保留不確定性（不說死單一數字）
- [ ] 範圍是否合理（不過窄也不過寬）
- [ ] 是否利用可用訊號（品牌、類型）做錨定

#### 典型失敗模式
- 假裝 exact（回覆單一數字而非範圍）
- 範圍過窄（忽略品類差異）
- 不利用品牌訊號（鷹流拉麵估成一般拉麵）

---

### B4: Clarify / Follow-up Decision

#### 目的
判斷是否需要向使用者追問更多資訊，以獲得更準確的估計。

#### 輸入
```json
{
  "grounded_items": [],
  "estimated_items": [],
  "uncertainty_signals": ["string"],
  "user_input": "string"
}
```

#### 輸出
```json
{
  "should_ask_followup": "boolean",
  "followup_type": "required | optional | none",
  "followup_questions": [
    {
      "question": "string",
      "target_field": "string",
      "priority": "high | medium | low"
    }
  ],
  "can_proceed_without_followup": "boolean"
}
```

#### 責任範圍
- 評估現有資訊是否足夠進行合理估計
- 決定追問的時機與內容
- 區分「必須追問」與「可選追問」

#### 非責任範圍
- 不負責實際搜尋知識庫
- 不負責計算熱量

#### 與其他 Bundle 的介面
- 接收 B1 的 uncertainty_signals
- 接收 B2 的 grounded_items
- 接收 B3 的 estimated_items
- 輸出 should_ask_followup 給 B7

#### Functional Checks
- [ ] 輸入「珍珠奶茶」→ should_ask_followup = true（需要糖度、杯型）
- [ ] 輸入「滷味」→ should_ask_followup = true（需要具體品項）
- [ ] 輸入「星巴克冰那堤大杯」→ should_ask_followup = false
- [ ] 輸入「我吃高麗菜一碗、豆皮兩片、甜不辣三塊」→ should_ask_followup = false
- [ ] 輸入「拉麵」→ should_ask_followup = true（需要湯底、份量）

#### Quality Checks
- [ ] 追問是否針對高影響變因（糖度、杯型、份量）
- [ ] 是否避免過度追問（已足夠資訊時不追問）
- [ ] 追問內容是否具體可回答

#### 典型失敗模式
- 應該追問卻不追問（直接給出過窄範圍）
- 不該追問卻追問（已足夠資訊仍追問）
- 追問內容過於開放（問「請問有什麼要補充？」而非具體問題）

---

### B5: Retrieval / Search

#### 目的
搜尋知識庫找到相關參考資料，供後續決策使用。

#### 輸入
```json
{
  "query": "string",
  "search_type": "exact | fuzzy | category",
  "filters": {
    "source": "string",
    "category": "string"
  }
}
```

#### 輸出
```json
{
  "results": [
    {
      "name": "string",
      "calories": "number",
      "source": "string",
      "relevance_score": "number"
    }
  ],
  "search_metadata": {
    "total_found": "number",
    "search_time_ms": "number"
  }
}
```

#### 責任範圍
- 搜尋本地知識庫
- 排序搜尋結果相關性
- 快取常用搜尋結果

#### 非責任範圍
- 不負責決定使用哪個搜尋結果
- 不負責熱量計算

#### 與其他 Bundle 的介面
- 被 B2, B3 呼叫
- 輸出 results 給呼叫者

#### Functional Checks
- [ ] 搜尋「珍珠奶茶」→ 返回相關結果
- [ ] 搜尋「星巴克」→ 返回星巴克相關品項
- [ ] 模糊搜尋「漢堡」→ 返回多種漢堡變體

#### Quality Checks
- [ ] 搜尋結果是否包含正確項目
- [ ] 排序是否合理（exact match 優先）
- [ ] 搜尋時間是否可接受

#### 典型失敗模式
- 搜尋結果過少（漏掉相關項目）
- 搜尋結果過多（不相關項目混入）
- 排序錯誤（exact match 排在後面）

---

### B6: Nutrition Math + State Sync

#### 目的
計算熱量並同步狀態到資料庫，確保 UI 與 Chat 一致。

#### 輸入
```json
{
  "grounded_items": [],
  "estimated_items": [],
  "user_id": "string",
  "meal_time": "datetime"
}
```

#### 輸出
```json
{
  "total_calories": "number",
  "total_macros": {
    "protein": "number",
    "fat": "number",
    "carbs": "number"
  },
  "budget_status": {
    "remaining": "number",
    "is_over": "boolean",
    "percentage": "number"
  },
  "db_commit": {
    "intake_record_id": "string",
    "ledger_entry_id": "string",
    "committed_at": "datetime"
  }
}
```

#### 責任範圍
- 加總所有項目的熱量
- 計算剩餘預算
- 寫入資料庫（intake_records, ledger_entries）
- 觸發 UI 更新訊號

#### 非責任範圍
- 不負責決定估計方式
- 不負責生成回覆文字

#### 與其他 Bundle 的介面
- 接收 B2 的 grounded_items
- 接收 B3 的 estimated_items
- 輸出 total_calories, budget_status 給 B7

#### Functional Checks
- [ ] 摩斯豬排堡 + 4塊雞塊 + 冰紅茶 = 640.3 kcal
- [ ] 記錄後 Today 頁面數字同步更新
- [ ] 超過預算時 budget_status.is_over = true
- [ ] 運動量輸入後有效預算增加

#### Quality Checks
- [ ] 熱量計算是否正確（加總無誤）
- [ ] 預算計算是否正確
- [ ] DB 寫入是否成功
- [ ] UI 同步是否及時

#### 典型失敗模式
- 熱量加總錯誤
- 預算計算錯誤（未考慮運動量）
- DB 寫入失敗
- UI 同步延遲或失敗

---

### B7: Final Response Rendering

#### 目的
生成最終回覆給使用者，包含適當的資訊壓縮與不確定性表達。

#### 輸入
```json
{
  "route": "string",
  "grounded_items": [],
  "estimated_items": [],
  "budget_status": {},
  "should_ask_followup": "boolean",
  "followup_questions": []
}
```

#### 輸出
```json
{
  "response": "string",
  "response_metadata": {
    "includes_calories": "boolean",
    "includes_range": "boolean",
    "includes_followup": "boolean",
    "uncertainty_expressed": "boolean"
  }
}
```

#### 責任範圍
- 根據 route 決定回覆格式
- 適當壓縮資訊（不把所有分析過程給使用者）
- 表達不確定性
- 決定是否夾帶追問

#### 非責任範圍
- 不負責計算熱量
- 不負責決定 route

#### 與其他 Bundle 的介面
- 接收 B6 的計算結果
- 接收 B4 的 followup 決定

#### Functional Checks
- [ ] exact_lookup → 回覆單一數字
- [ ] estimate_with_followup → 回覆範圍 + 追問
- [ ] ask_followup_only → 只追問，不先估
- [ ] 超過預算 → 回覆包含警告
- [ ] 運動量輸入 → 回覆包含新的有效預算

#### Quality Checks
- [ ] 回覆是否簡潔（不過長）
- [ ] 回覆是否自然（像聊天）
- [ ] 不確定性是否適當表達
- [ ] 數字是否與 UI 一致

#### 典型失敗模式
- 回覆過長（把完整分析給使用者）
- 回覆過短（漏掉必要資訊）
- 不確定性表達不當（過度自信或過度保守）
- 數字與 UI 不一致

---

## Bundle 依賴關係圖

```
         ┌─────────────────────────────────────────────────────────────┐
         │                         B1: Routing                         │
         └─────────────────────────────────────────────────────────────┘
                    │                    │                    │
                    ▼                    ▼                    ▼
         ┌──────────────┐      ┌────────────────┐      ┌──────────────┐
         │ B2: Exact    │      │ B5: Retrieval  │      │ B4: Clarify  │
         │ Grounding    │◄─────┤ / Search       │      │ Decision     │
         └──────────────┘      └────────────────┘      └──────────────┘
                    │                    │                    │
                    ▼                    │                    ▼
         ┌────────────────┐              │            ┌──────────────┐
         │ B3: Generic    │              │            │ B7: Response │
         │ Estimation     │              │            │ Rendering    │
         └────────────────┘              │            └──────────────┘
                    │                    │                    ▲
                    └────────┬───────────┘                    │
                             ▼                                │
         ┌──────────────────────────────────────────────────────┐
         │            B6: Nutrition Math + State Sync           │
         └──────────────────────────────────────────────────────┘
```

---

## 測試案例對應

### Benchmark Test Set v1 (18 cases) → Bundle 映射

| Case | Input | Expected Route | Bundle |
|------|-------|----------------|--------|
| 001 | 星巴克冰那堤大杯 | exact_lookup | B1, B2, B6, B7 |
| 002 | 星巴克冰那堤 | estimate_with_followup | B1, B2, B4, B7 |
| 003 | 大麥克 | exact_lookup | B1, B2, B6, B7 |
| 004 | 麥香雞 | exact_lookup | B1, B2, B6, B7 |
| 005 | 原味麥脆雞腿2塊 | exact_lookup | B1, B2, B6, B7 |
| 006 | 松屋特盛牛丼 | exact_lookup | B1, B2, B6, B7 |
| 007 | 吉野家大碗牛丼 | exact_lookup | B1, B2, B6, B7 |
| 008 | Subway火腿潛艇堡 | exact_lookup | B1, B2, B6, B7 |
| 009 | Subway照燒雞肉潛艇堡 | exact_lookup | B1, B2, B6, B7 |
| 010 | 珍珠奶茶 | estimate_with_followup | B1, B3, B4, B7 |
| 011 | 珍珠奶茶半糖去冰 | direct_estimate | B1, B3, B6, B7 |
| 012 | 滷肉飯 | estimate_with_followup | B1, B3, B4, B7 |
| 013 | 咖哩飯 | estimate_with_followup | B1, B3, B4, B7 |
| 014 | 水餃10顆 | direct_estimate | B1, B3, B6, B7 |
| 015 | 鹹酥雞有雞排甜不辣四季豆米血 | direct_estimate | B1, B3, B6, B7 |
| 016 | 自助餐主餐是滷排骨然後只有吃一碗飯 | estimate_with_followup | B1, B3, B4, B7 |
| 017 | 拉麵 | estimate_with_followup | B1, B3, B4, B7 |
| 018 | 鷹流拉麵2929豚骨拉麵 | direct_estimate | B1, B3, B6, B7 |

### Benchmark Test Set v2 (18 cases) → Bundle 映射

| Case | Input | Expected Route | Bundle |
|------|-------|----------------|--------|
| 001 | 摩斯豬排堡 | exact_lookup | B1, B2, B6, B7 |
| 002 | 摩斯日式豬排三明治 | exact_lookup | B1, B2, B6, B7 |
| 003 | 摩斯豬排堡、4塊雞塊跟中杯冰紅茶 | exact_lookup | B1, B2, B6, B7 |
| 004 | 7-11 雙蔬鮪魚飯糰 | exact_lookup | B1, B2, B6, B7 |
| 005 | 7-11 燻雞總匯鮮蔬三明治 | exact_lookup | B1, B2, B6, B7 |
| 006 | 7-11 一鍋燒滑蛋嫩雞親子丼 | exact_lookup | B1, B2, B6, B7 |
| 007 | 全家大口義式香草雞腿排飯糰 | exact_lookup | B1, B2, B6, B7 |
| 008 | 全家香腸腿排雙拼便當 | exact_lookup | B1, B2, B6, B7 |
| 009 | 全家健身G肉餐盒 | exact_lookup | B1, B2, B6, B7 |
| 010 | 剛剛跟朋友去熱炒店吃合菜 | ask_followup_only | B1, B4, B7 |
| 011 | 熱炒我自己大概吃半碗白飯、三杯雞... | direct_estimate | B1, B3, B6, B7 |
| 012 | 我剛剛吃了一碗 poke | estimate_with_followup | B1, B3, B4, B7 |
| 013 | 鮭魚poke，白飯，有毛豆、海帶芽、酪梨... | direct_estimate | B1, B3, B6, B7 |
| 014 | 我剛吃炸醬麵 | estimate_with_followup | B1, B3, B4, B7 |
| 015 | 大碗炸醬麵，不是韓式的 | direct_estimate | B1, B3, B6, B7 |
| 016 | 鮭魚親子丼 | direct_estimate | B1, B3, B6, B7 |
| 017 | 晚餐吃滷味 | ask_followup_only | B1, B4, B7 |
| 018 | 滷味點了王子麵、豆皮、甜不辣、高麗菜 | direct_estimate | B1, B3, B6, B7 |

### Turn2 Hybrid Replay Pack (10 cases) → Bundle 映射

| Case | Turn1 Input | Turn2 Input | Expected Flow | Bundle |
|------|-------------|-------------|---------------|--------|
| 001 | 我晚餐吃滷味 | 高麗菜、豆皮、甜不辣、王子麵 | ask → completion | B1, B4, B6, B7 |
| 002 | 我剛剛吃合菜 | 三杯雞、高麗菜、白飯 | ask → completion | B1, B4, B6, B7 |
| 003 | 我剛跟家裡吃 | 白飯、鮭魚、高麗菜、滷豆腐 | ask → completion | B1, B4, B6, B7 |
| 004 | 我中午吃喜酒 | 油飯、炸蝦、清蒸魚、烏骨雞湯 | ask → completion | B1, B4, B6, B7 |
| 005 | 我剛剛喝珍珠奶茶 | 大杯、半糖、正常冰 | estimate → refinement | B1, B3, B4, B6, B7 |
| 006 | 我吃炸醬麵 | 一般碗、醬正常、半顆滷蛋 | estimate → refinement | B1, B3, B4, B6, B7 |
| 007 | 我吃牛丼 | 吉野家並盛、溫泉蛋 | estimate → refinement | B1, B2, B4, B6, B7 |
| 008 | 我吃雞腿便當 | 炸雞腿、白飯、配菜 | estimate → refinement | B1, B3, B4, B6, B7 |
| 009 | 我中午吃炒麵跟魚 | 炒麵一大盤、鱈魚一塊150克 | estimate → refinement | B1, B3, B4, B6, B7 |

---

## 失敗模式對應表

| 失敗模式 | 可能發生在 | 檢測方式 |
|----------|------------|----------|
| Route 錯（該 exact 卻估計） | B1 | 程式檢查：輸入明確品項時 route 是否為 exact_lookup |
| Route 錯（該估計卻 exact） | B1 | 程式檢查：輸入模糊描述時 route 是否非 ask_followup_only |
| Exact match 錯 sibling | B2 | 程式檢查：回覆數值是否為正確品項的數值 |
| 應該追問卻沒追問 | B4 | 程式檢查：輸入缺少關鍵資訊時 should_ask_followup 是否為 true |
| 不該追問卻追問 | B4 | 程式檢查：輸入足夠資訊時 should_ask_followup 是否為 false |
| 熱量計算錯誤 | B6 | 程式檢查：加總是否正確 |
| 預算同步錯誤 | B6 | 程式檢查：UI 數字是否與計算一致 |
| 回覆過長 | B7 | LLM Judge：回覆字數是否合理 |
| 回覆漏資訊 | B7 | LLM Judge：必要資訊是否包含 |
| 不確定性表達不當 | B7 | LLM Judge：是否過度自信或過度保守 |

---

## 下一步

1. **驗證本文件** - 確認 Bundle 切分是否合理
2. **產出 Failure Taxonomy v1** - 基於本文件定義常見錯誤
3. **建立 Tiny Golden Set** - 每個 Bundle 挑 5-10 個代表性 cases
4. **設計 Grading Rubric** - 定義如何判定 pass/fail

---

## 歷史

- 2025-04-23: v1 初始版本
