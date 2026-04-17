# Benchmark Case Schema

## 1. 目的

這份文件定義 benchmark case 的標準資料結構。

目標是讓 benchmark case：

- 可重播
- 可版本化
- 可做 multi-turn
- 可帶 canonical state 與 memory seed
- 可支援 flow-level 與 cross-flow 測試

---

## 2. Case 基本結構

每個 benchmark case 至少應由以下檔案或欄位組成：

- `case.yaml`
- `initial_state.json`
- `memory_seed.json`
- `turns.json`
- `expected_outputs.json`
- `expected_state_delta.json`
- `notes.md`（可選）

---

## 3. `case.yaml`

`case.yaml` 用來定義這個 case 的 metadata。

建議欄位：

```yaml
case_id: intake_multi_turn_001
title: "多輪補充同一餐"
bucket: intake_multi_turn
tier: 1
case_class: golden
safety_classification: normal
source_type: hand_authored
version: 1
tags:
  - intake
  - multi_turn
  - same_thread
  - default_commit
owner: codex
status: active
```

### 必備欄位

- `case_id`
- `bucket`
- `tier`
- `case_class`
- `safety_classification`
- `source_type`
- `version`

### `case_class`

合法值：

- `golden`
- `edge`
- `adversarial`
- `regression`

### `safety_classification`

建議值：

- `normal`
- `safety_critical`
- `guardrail_stress`

### `source_type`

建議值：

- `hand_authored`
- `synthetic`
- `real_derived`
- `failure_replay`

---

## 4. `initial_state.json`

定義 case 開始前的 canonical state。

至少可包含：

```json
{
  "meal_threads": [],
  "day_budget_ledger": null,
  "body_plan": null,
  "open_proposals": [],
  "proactive_triggers": []
}
```

### 用途

- 測有無既有餐點 thread
- 測有無既有 ledger overlay
- 測有無 active body plan
- 測 proposal / rescue / calibration 已存在情境

---

## 5. `memory_seed.json`

定義 case 開始前的 derived memory / summary 狀態。

例如：

```json
{
  "preference_profile_summary": null,
  "golden_order_summary": null,
  "intake_completeness_summary": null,
  "adherence_summary": null,
  "rescue_history_summary": null,
  "suppression_summary": null,
  "calibration_history_summary": null
}
```

### 用途

- 測 preference-aware recommendation
- 測 logging-quality-first calibration
- 測 negative preference
- 測 suppression / proactive

---

## 6. `turns.json`

定義多輪或單輪互動腳本。

格式建議：

```json
{
  "turns": [
    {
      "turn_id": 1,
      "channel": "chat",
      "input": {
        "role": "user",
        "text": "我剛剛吃了雞腿便當"
      },
      "expected": {
        "flow": "intake",
        "should_commit": true,
        "should_ask_follow_up": false
      }
    },
    {
      "turn_id": 2,
      "channel": "chat",
      "input": {
        "role": "user",
        "text": "還有一杯紅茶"
      },
      "expected": {
        "flow": "intake",
        "target_same_meal_thread": true,
        "should_create_new_version": true
      }
    }
  ]
}
```

### 必備欄位

- `turn_id`
- `input`
- `expected`

### `expected` 常用欄位

- `flow`
- `should_commit`
- `should_ask_follow_up`
- `should_create_new_version`
- `target_same_meal_thread`
- `should_create_proposal`
- `expected_guardrails`

---

## 7. `expected_outputs.json`

定義這個 case 預期的 runtime 輸出形狀。

可包含：

```json
{
  "final_flow": "intake",
  "expected_pass_outputs": {
    "task_meal_link_result": {
      "intent": "intake"
    },
    "decision_result": {
      "clarify_is_blocking": false
    },
    "nutrition_result": {
      "commit_readiness": "commit_ready"
    }
  },
  "expected_top_level": {
    "should_commit": true,
    "should_create_proposal": false,
    "should_trigger_safety_gate": false
  }
}
```

### 用途

- 驗證 pass-level contract
- 驗證 flow-level outcome
- 驗證 no-op / no-proposal / monitor-only 類情境

---

## 8. `expected_state_delta.json`

定義 case 結束後，canonical state 應怎麼變。

例如：

```json
{
  "meal_threads_created": 1,
  "meal_versions_created": 2,
  "meal_items_created": 3,
  "ledger_entries_created": 1,
  "body_plan_changed": false,
  "proposal_created": false
}
```

### 用途

- 驗證 commit 邊界
- 驗證 proposal 邊界
- 驗證 cross-flow state sync

---

## 9. `notes.md`

可選，但建議保留。

適合記：

- case 背景
- 為什麼它重要
- 它對應哪個 bug / regression
- 哪個 spec 條文在保護這個 case

---

## 10. 最低治理要求

每個 benchmark case 至少要能回答：

- 測哪個 bucket
- 起始 state 是什麼
- 記憶 seed 是什麼
- 使用者輸入了什麼
- 預期不該發生什麼
- 預期 state 怎麼變

---

## 11. 與 L5B 的對齊

這份 schema 服務於：

- `golden`
- `edge`
- `adversarial`
- `regression`
- `safety_critical`

五種 benchmark class。

---

## 12. Derived Executable Action Pack

當 Official Golden utterance pack 已存在，但 workflow runner 需要額外的 runtime input contract 時，可建立 derived executable action pack。

這不是新的 benchmark authority tier，而是 subordinate artifact。

建議 top-level 欄位：

```json
{
  "pack_id": "rescue_executable_action_pack_v1",
  "pack_mode": "executable_action",
  "authority_level": "derived_from_official_canonical",
  "derived_from_pack_id": "rescue_official_canonical_pack_v1",
  "runner_input_contract": {},
  "cases": []
}
```

每個 executable case 至少應包含：

- `executable_case_id`
- `source_official_case_id`
- `suite_id`
- `derivation_status`
- `expected_runtime_outcome`

workflow-specific 可再加：

- `state_seed`
- `proposal_seed`
- `execution_mode`
- `runtime_action`
- `block_reason`

正式規則：

- `expected_runtime_outcome` 必須完整繼承 source official case 的主處置 truth
- 若尚無唯一 runtime action mapping，不得硬補語意；應改用 blocked status 與 `block_reason`
