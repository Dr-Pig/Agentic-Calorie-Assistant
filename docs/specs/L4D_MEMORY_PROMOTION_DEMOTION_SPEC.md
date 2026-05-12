# L4D Memory Promotion & Demotion Spec

## 1. 目的

這份 spec 定義記憶的升級（promotion）與降級（demotion）規則，補充 L4A Memory Model 的 lifecycle 定義。

它回答：

- 什麼時候把東西「升級」成長期記憶
- 什麼時候把東西「降級」或移除
- Golden Order 是如何從歷史資料派生的
- 實體正規化（entity normalization）的流程

---

## 2. 核心原則

### 2.1 Golden Order 是 Materialized View，不是 Promotion 結果

Golden Order 不是從 Pattern Memory「升級」來的，而是從 canonical history 直接派生的 deterministic artifact。

```
Golden Order = 從 L1 Canonical History materialized 的 derived view
             ≠ Pattern Memory 的 promotion 結果
```

### 2.2 Pattern → Confirmed 只能由使用者確認觸發

LLM 可以「提議」升級，但不能自己完成升級。

### 2.3 Temporary Preference 是獨立的記憶類型

不是「不記」和「記成長期」二選一，而是有第三條路： временный 偏好。

### 2.4 Demotion 是自動的，但 Confirmed Negative 例外

大部分記憶會自動 demote，但 explicit confirmed negative 不會。

---

## 3. Promotion Rules（升級規則）

### 3.1 Path 1：使用者明講 → Confirmed Memory（最快）

**觸發條件**：
- 使用者明確說「記住我不喝奶茶」「我對花生過敏」
- 明確的偏好/厭惡表達

**處理流程**：
1. 由 intake Pass 1 的 `task_meal_link_pass` 或 general chat routing 識別
2. 直接寫入 Confirmed Memory
3. 不需要 reinforcement_count 門檻
4. 標記 `source = user_verbal`

**範例**：
- 「記住我不喝含糖飲料」
- 「我對海鮮過敏」

---

### 3.2 Path 2：行為重複 → Pattern Memory（中速）

**觸發條件**：
- 同一 store + item bundle 出現 3 次
- 或同一 item_kind 出現 5 次
- 或同一時段偏好出現 5 次

**處理流程**：
1. 從 canonical history 檢測重複行為
2. 建立 Pattern Memory 記錄
3. `reinforcement_count = 觀察次數`
4. `confidence = f(reinforcement_count)`

**Confidence 計算**：
```
reinforcement_count = 1 → confidence = 0.3
reinforcement_count = 2 → confidence = 0.5
reinforcement_count ≥ 3 → confidence = 0.7
reinforcement_count ≥ 5 → confidence = 0.9
```

**範例**：
- 連續 3 天午餐吃同一家的便當
- 下午茶時段連續 5 次選擇甜飲

---

### 3.3 Path 3：Canonical History → Golden Order（Materialization）

**重要**：這不是 promotion，而是從歷史資料派生的 materialized view。

**觸發條件**：
- canonicalized store + bundle
- 30 天內出現 ≥ 3 次
- 最近 60 天仍有新觀察（保持 freshness）

**處理流程**：
1. Entity Normalization（見 Section 5）
2. 從 canonical history 統計頻率
3. 建立 Golden Order 記錄
4. 標記 `source = materialized_from_canonical`

**可選加分**（非必要條件）：
- 若是被推薦後採納 → 標記 `recommendation_acceptance_bonus`
- 這只是標記，不影響 Golden Order 資格

**Golden Order 結構**：
```json
{
  "golden_order_id": "go_xxx",
  "store_id": "store_123",
  "store_name_normalized": "便利商店",
  "item_bundle": ["雞胸肉便當", "無糖綠茶"],
  "first_observed_at": "2025-01-01",
  "last_observed_at": "2025-01-15",
  "observation_count": 5,
  "observation_window_days": 30,
  "is_active": true,
  "recommendation_acceptance_bonus": false
}
```

---

### 3.4 Path 4：Pattern → Confirmed（需使用者確認）

**觸發條件**（兩條合法路徑）：

**路徑 4a：系統建議 + 使用者確認**
- 系統偵測到高穩定 pattern
- `reinforcement_count ≥ 5`
- `confidence ≥ 0.8`
- 30 天內行為一致
- UI 彈出確認：「偵測到你最近偏好低醣午餐，要記住嗎？」
- 使用者按確認 → 升級

**路徑 4b：使用者口頭確認**
- 使用者說：「對，記住我最近在減醣」
- 直接寫入 Confirmed Memory

**處理流程**：
1. LLM 可以「提議」升級，但不能自己完成
2. 必須經過使用者明確確認（UI 或口頭）
3. 寫入 Confirmed Memory，標記 `source = behavior_upgrade` 或 `source = user_verbal`

**禁止**：
- ❌ LLM 不能自己完成升級
- ❌ 不能只有 pattern 穩定就自動升級

---

### 3.4A Shared `FeedbackEvent` Confirmation Boundary

Memory confirmation、proactive dismiss/snooze/undo、recommendation/rescue feedback 共用小型 audit/input contract，但 `FeedbackEvent` 本身不直接 mutate memory truth。

```yaml
FeedbackEvent:
  target_type: memory_candidate | proactive_candidate | recommendation_offer | rescue_plan
  target_id: string
  action: confirm | reject | dismiss | snooze | undo | correct | opt_out
  reason: optional string
  snooze_until: optional datetime
  source_turn_id: string
  scope_keys:
    user_id: string
    workspace_id: string
    project_id: string
    surface: string
```

Promotion interpretation rules:

- `action=confirm` may satisfy Pattern → Confirmed only when the target is a valid `memory_candidate`, target/source/scope checks pass, and the candidate type is promotion-legal.
- `action=reject` or `correct` may close or repair a candidate, but does not update canonical MealThread / FoodDB / BodyBudget truth by itself.
- `dismiss` and `snooze` are user-control signals for proactive/recommendation/rescue posture; they never auto-promote memory.
- `opt_out` may project into a suppression rule candidate and app-use memory candidate, but only through separate proactive and memory validators.
- `confirm` of a memory candidate never enables proactive delivery, scheduler delivery, or user-facing route activation.

Required validators:

- target id exists and matches `target_type`
- source turn id exists and belongs to the same scope
- all scope keys are present
- action is legal for the target type
- no canonical mutation is implied by the feedback event alone

---

### 3.5 Path 5：修正 → Canonical Truth

**觸發條件**：
- 使用者修正之前的餐點估算
- 例如：原本寫 500 大卡，修正為 700 大卡

**處理流程**：
1. 不寫入 Pattern Memory
2. 只更新 Canonical MealItem
3. 記錄 `correction_lineage`
4. 這是「事實修正」，不是「偏好」

---

### 3.6 Path 6：一次性 / Temporary 偏好

**觸發條件與分類**：

| 類型 | 範例 | 處理 |
|------|------|------|
| **一次性實驗** | 「今天想試試看 XXX」 | 不寫入記憶 |
| **Temporary Preference** | 「這週在減醣」「這兩天不想吃辣」 | 寫入 Temporary Preference |
| **長期偏好** | 「我最近在減醣」 | 寫入 Pattern Memory |
| **Confirmed Negative** | 「不吃牛肉」 | 寫入 Confirmed Negative |

**Temporary Preference 結構**：
```json
{
  "temp_preference_id": "tp_xxx",
  "preference_type": "temporary_constraint",
  "subject": "不想吃辣",
  "context_scope": "all", // 或 "lunch", "dinner", "weekday"
  "valid_from": "2025-01-20",
  "valid_until": "2025-01-27", // 或用 expires_in_days
  "expires_in_days": 7,
  "reason": "這兩天腸胃不舒服",
  "is_active": true
}
```

---

## 4. Demotion Rules（降級規則）

### 4.1 Pattern Memory Demotion

| 條件 | 動作 |
|------|------|
| 30 天無新觀察 | confidence 降至 0.5，標記 `needs_attention` |
| 60 天無新觀察 | 移至 archive，不參與即時 retrieval |
| 90 天無新觀察 | 刪除記錄 |

### 4.2 Golden Order Demotion

| 條件 | 動作 |
|------|------|
| 60 天無重複 | 標記 `is_active = false` |
| 90 天無重複 | 移至 archive |
| 重新出現 | 重新激活，`is_active = true` |

### 4.3 Behavior-upgraded Confirmed Demotion

| 條件 | 動作 |
|------|------|
| 30 天無相關行為 | 標記 `needs_validation` |
| 60 天無相關行為 | 降級為 Pattern Memory |
| 使用者否認 | 立即降級為 Pattern |

### 4.4 Confirmed Negative Demotion

| 條件 | 動作 |
|------|------|
| default | **不自動 demote** |
| 使用者明講取消 | 立即移除 |

---

## 5. Entity Normalization（實體正規化）

### 5.1 問題背景

單純 deterministic 的 frequency counting 在實體辨認上有問題：

| 問題 | 範例 |
|------|------|
| 名稱變異 | 「便利商店」vs「7-11」vs「7-ELEVEn」vs「seven eleven」 |
| 模糊匹配 | 「麥當勞」應該對應哪個 store_id？ |
| 語言不一致 | 中文、英文、簡體、繁體 |

### 5.2 Normalization 流程

```
┌─────────────────────────────────────────────────────────────┐
│              Entity Normalization 流程                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: Deterministic 匹配                                  │
│  ─────────────────────────────────────────────────────────  │
│  - 查詢 store alias table                                    │
│  - 若有精確匹配 → 直接使用 canonical_id                      │
│                                                              │
│  Step 2: LLM Normalization (fallback)                        │
│  ─────────────────────────────────────────────────────────  │
│  - 若 Step 1 失敗                                            │
│  - LLM 將變異名稱正規化為 canonical form                      │
│  - 輸出：canonical_store_id + normalized_name               │
│  - 建立新的 alias 記錄（供未來 deterministic 使用）           │
│                                                              │
│  Step 3: Confidence 標記                                     │
│  ─────────────────────────────────────────────────────────  │
│  - 若正規化成功 → confidence = high                          │
│  - 若正規化失敗 → 維持原樣，標記 low_confidence               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Store Normalization 範例

```
輸入：「7-ELEVEn」「seven eleven」「7-11」「小七」

正規化後：
{
  "canonical_id": "store_001",
  "canonical_name": "7-ELEVEn",
  "normalized_from": ["7-ELEVEn", "seven eleven", "7-11", "小七"],
  "confidence": 0.95
}
```

### 5.4 Item Normalization 類似

- 食物名稱正規化
- 套餐 components 正規化
- 品牌名稱正規化

---

## 6. 與 L4A 的對齊

### 6.1 L4A 引用本文件

L4A Memory Model Spec 的以下章節應引用本文檔：

- Section 3.2 Pattern Memory → 見 Section 3.2, 3.3
- Section 3.3 Confirmed Memory → 見 Section 3.1, 3.4
- Section 3.5 Temporary Preference → 見 Section 3.6
- Section 3.6 Golden Orders → 見 Section 3.3
- Section 9.1 Create → 見 Section 3
- Section 9.3 Decay → 見 Section 4
- Section 9.4 Demotion → 見 Section 4
- Section 9.5 Confirm → 見 Section 3.4

### 6.2 數據流圖

```
┌─────────────────────────────────────────────────────────────┐
│                    Memory Lifecycle                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐                                           │
│  │ User Verbal  │ ──────→ Confirmed Memory (Path 1)         │
│  └──────────────┘                                           │
│                                                              │
│  ┌──────────────┐                                           │
│  │   Behavior   │ ──────→ Pattern Memory (Path 2)           │
│  │   Repeated   │              ↓                            │
│  └──────────────┘              ↓                            │
│                      Pattern ──→ Confirmed (Path 4)         │
│                              (需使用者確認)                  │
│                                                              │
│  ┌──────────────┐                                           │
│  │  Canonical   │ ──────→ Golden Order (Path 3)             │
│  │   History    │     (Materialization, not promotion)      │
│  └──────────────┘                                           │
│                                                              │
│  ┌──────────────┐                                           │
│  │  Correction  │ ──────→ Canonical Truth (Path 5)          │
│  └──────────────┘                                           │
│                                                              │
│  ┌──────────────┐                                           │
│  │   One-off    │ ──────→ 不寫入 (Path 6)                   │
│  │  Preference  │              ↓                            │
│  └──────────────┘              ↓                            │
│                      Temporary Preference (Path 6)          │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  Demotion Flow:                                              │
│  Pattern ──30天──→ needs_attention ──60天──→ Archive        │
│  Golden Order ──60天──→ inactive ──90天──→ Archive          │
│  Confirmed (behavior) ──30天──→ needs_validation            │
│  Confirmed (user_verbal) ──不自動 demote                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. v1 Default Decisions

### 7.1 Promotion 閾值

| 類型 | 閾值 |
|------|------|
| Pattern Memory 建立 | 同一 store+item 3 次，或同一 item_kind 5 次 |
| Golden Order 建立 | 30 天內 3 次 + 60 天內有新觀察 |
| Pattern → Confirmed | reinforcement_count ≥ 5 + confidence ≥ 0.8 + 30天一致 + 需使用者確認 |

### 7.2 Demotion 閾值

| 類型 | 閾值 |
|------|------|
| Pattern 降權 | 30 天無新觀察 |
| Pattern archive | 60 天無新觀察 |
| Golden Order inactive | 60 天無重複 |
| Golden Order archive | 90 天無重複 |
| Confirmed (behavior) needs_validation | 30 天無相關行為 |
| Confirmed (behavior) 降級 | 60 天無相關行為 |

### 7.3 Temporary Preference

| 參數 | 預設值 |
|------|--------|
| 最大有效天數 | 14 天 |
| 預設 context_scope | all |
| 自動過期 | 是 |

---

## 8. 測試情境

### 8.1 Promotion 測試

- [ ] 使用者說「記住我不喝奶茶」→ 直接寫入 Confirmed
- [ ] 同一 store+item 出現 3 次 → 建立 Pattern Memory
- [ ] Pattern reinforcement_count 正確遞增
- [ ] Golden Order 從 canonical history 正確 materialization
- [ ] Pattern → Confirmed 只能經由使用者確認完成
- [ ] LLM 不能自己完成升級
- [ ] `FeedbackEvent(action=confirm)` only promotes a scoped, source-backed memory candidate after validator approval
- [ ] `FeedbackEvent(action=dismiss|snooze|opt_out)` does not auto-promote product memory

### 8.2 Demotion 測試

- [ ] Pattern 30 天無新觀察 → confidence 降至 0.5
- [ ] Golden Order 60 天無重複 → is_active = false
- [ ] Confirmed (behavior) 30 天無行為 → needs_validation
- [ ] Confirmed (user_verbal) 不自動 demote

### 8.3 Entity Normalization 測試

- [ ] 「7-11」「7-ELEVEn」正規化為同一 canonical_id
- [ ] 無法正規化時標記 low_confidence
- [ ] 新正規化結果寫入 alias table

### 8.4 Temporary Preference 測試

- [ ] 「這週在減醣」正確建立 Temporary Preference
- [ ] 超過 valid_until 後自動過期
- [ ] 查詢時只返回 active 的 temporary preference

---

## 8A. Framework-Informed Promotion Guardrails

Hermes、OpenClaw、Mem0、Hindsight、Graphiti、Letta、memU 的 memory 機制可以作為 promotion design pressure，但不能取代本文件的 promotion/demotion truth。

採用的 guardrail translation：

- Hindsight 的 `retain / recall / reflect`：
  - `retain` 在本產品只代表建立 candidate 或 typed history observation。
  - `recall` 只能回傳 read-only context。
  - `reflect` 可以生成 review recommendation，但不能完成 promotion。
- OpenClaw 的 dreaming / backfill：
  - 可作為 lab review job 或 historical replay。
  - replay output 必須進 `review.md` / candidate queue，不可直接寫 `memory.md`。
- Hermes / Letta 的 core memory update：
  - 可參考 bounded profile/core block 與 read-only block guard。
  - agent 不可因一次 tool call 直接改 confirmed product memory，除非符合 Path 1 使用者明確聲明或 review gate。
- Graphiti 的 temporal facts：
  - 每個 promoted memory 應能帶 validity window、superseded_by、source refs。
  - conflicting memory 不應覆蓋舊資料，而應產生 contradiction review 或 supersession。
- memU 的 scope model：
  - promotion candidate、confirmed memory、review decision 必須保存 scope fields。
  - 缺少 scope keys 時，promotion 必須拒絕。
- Mem0 的 CRUD vocabulary：
  - `add/update/delete` 在本產品對應 propose/review/forget，不代表直接 durable write。

Lab branch execution:

- isolated advanced product lab 可以完整執行 candidate extraction、review decision、promotion/demotion、forget/delete、backfill、memory tool call、context injection。
- lab 中的 promotion 可以寫入 lab-only memory substrate，用於完整 E2E。
- 任何合回 main/self-use V1 的 PR，若未包含獨立 activation gate，必須保持 production durable memory activation off。

Required promotion evidence:

- source refs exist
- scope keys exist
- candidate type is legal
- no canonical truth override
- stale/conflict posture is represented
- user/human confirmation requirement is satisfied when required
- trace distinguishes `lab_promotion_executed=true` from `mainline_promotion_enabled=false`

---

## 9. 參考文獻

- L4A_MEMORY_MODEL_SPEC.md
- L4B_RETRIEVAL_POLICY_SPEC.md
- L4C_CONTEXT_PACKING_SPEC.md
- Superseded memory reference material has been removed from the active repo truth path.
