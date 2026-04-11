# L3T Implementation Checklist

## 1. 目的

本清單把 [`L3T Typed Runtime Contract Spec`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L3T_TYPED_RUNTIME_CONTRACT_SPEC.md) 對應到 repo 內實際 Pydantic models 與 code modules。

它回答：

- 哪些 typed contract 已經有實作
- 哪些只是部分對齊
- 哪些仍缺模型或 bridge
- 下一步應在哪些檔案補

---

## 2. Intake Contracts

### 2.1 `TaskMealLinkResult`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `implemented`
- Notes:
  - 欄位已接近 `L3T`
  - 可後續再收緊 enum / optional posture

### 2.2 `DecisionPassResult`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `partial`
- Gaps:
  - `next_action` 與 `tool_plan` 仍偏 legacy naming
  - 尚未完全對齊 `L3T` 的 `clarify_user / no_food_commit / local_then_search` vocabulary

### 2.3 `NutritionResolutionResult`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `partial`
- Gaps:
  - `resolution_mode / resolution_basis` vocabulary 與 `L3T` 尚未完全一致
  - 缺部分 `current_evidence_sufficiency / why_no_more_tools / reason_for_not_requesting_tool` 的 typed hardening

### 2.4 `FinalResponseResult`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `implemented`

### 2.5 `EstimatePayload`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `implemented as assembled runtime artifact`
- Notes:
  - 現階段允許保留
  - 但 canonical write 應改走 `CommitRequestCandidate`

### 2.6 `MealItemPayload`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `implemented`
- Mapping:
  - `ComponentEstimate -> MealItemPayload` 已可 1:1 映射

### 2.7 `CommitRequestCandidate`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `implemented`
- Runtime bridge:
  - [`app/application/canonical_commit_bridge.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/canonical_commit_bridge.py)
  - [`app/application/text_meal_commit_service.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/text_meal_commit_service.py)
- Notes:
  - Phase 2 已開始用這條 bridge

---

## 3. Recommendation Contracts

### 3.1 `RecommendationCandidate`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `implemented`
- Usage status: `not yet wired`

### 3.2 `HintPacket`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `implemented`
- Usage status: `not yet wired`

### 3.3 `RecommendationResponseResult`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `implemented`
- Usage status: `not yet wired`

---

## 4. Trace Contracts

### 4.1 `StageTraceEvent`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `implemented`
- Runtime usage:
  - [`app/application/stage_trace_runtime.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/stage_trace_runtime.py)
  - [`app/observability/stage_trace_store.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/observability/stage_trace_store.py)

### 4.2 `PassExecutionEnvelope`

- Current model: [`app/schemas.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/schemas.py)
- Status: `legacy-compatible partial`
- Gaps:
  - current status enum still uses `success/degraded/failed`
  - `L3T` target is `ok/failed/abstained`
- Migration posture:
  - postpone breaking rename until pass runner and all pass helpers are updated together

---

## 5. Canonical Bridge Alignment

### Done

- `EstimatePayload -> CommitRequestCandidate`
- `CommitRequestCandidate -> canonical persistence`
- `Stage trace append` now uses typed runtime event
- legacy meal-log persistence now builds a typed `CommitRequestCandidate`
  before canonical write:
  - [`app\application\canonical_commit_bridge.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/application/canonical_commit_bridge.py)
  - [`app\infrastructure\meal_log_persistence.py`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/app/infrastructure/meal_log_persistence.py)

### Remaining

- recommendation typed models wire-up
- calibration typed models
- rescue typed models
- pass runner envelopes vocabulary unification
- tighten `DecisionPassResult` / `NutritionResolutionResult` enum vocabulary
  to the final `L3T` literals without legacy compatibility aliases

---

## 6. Next Work Items

1. Align `DecisionPassResult` enum vocabulary to `L3T`
2. Align `NutritionResolutionResult` vocabulary to `L3T`
3. Introduce typed recommendation path models into recommendation implementation
4. Add typed calibration / rescue result models to `app/schemas.py`
5. Migrate `PassExecutionEnvelope` to final `L3T` status vocabulary with coordinated runner changes
