# Stateful Multi-turn Case Template

## 1. 用途

這份模板用來建立：

- 多輪對話 benchmark
- 帶既有 state 的 benchmark
- 帶 memory seed 的 benchmark
- cross-flow benchmark

---

## 2. 建立流程

建立一個 stateful multi-turn case 時，請依序完成：

1. 定 `case.yaml`
2. 定 `initial_state.json`
3. 定 `memory_seed.json`
4. 定 `turns.json`
5. 定 `expected_outputs.json`
6. 定 `expected_state_delta.json`

不要反過來直接先寫對話。

---

## 3. 模板

### `case.yaml`

```yaml
case_id: intake_multi_turn_golden_001
title: "同一餐多輪補充與修正"
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
  - correction
owner: codex
status: active
```

### `initial_state.json`

```json
{
  "meal_threads": [],
  "day_budget_ledger": {
    "local_date": "2026-04-11",
    "effective_budget_kcal": 1600,
    "remaining_kcal": 1200
  },
  "body_plan": {
    "estimated_tdee": 2100,
    "target_rate": -0.4
  },
  "open_proposals": [],
  "proactive_triggers": []
}
```

### `memory_seed.json`

```json
{
  "preference_profile_summary": {
    "drink_preference_strength": "high",
    "staple_type_distribution": {
      "rice": 0.6,
      "noodle": 0.2
    }
  },
  "golden_order_summary": null,
  "intake_completeness_summary": {
    "coverage_14d": 0.9
  },
  "adherence_summary": {
    "budget_adherence": "medium"
  },
  "rescue_history_summary": null,
  "suppression_summary": null,
  "calibration_history_summary": null
}
```

### `turns.json`

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
        "should_ask_follow_up": false,
        "target_same_meal_thread": false
      }
    },
    {
      "turn_id": 2,
      "channel": "chat",
      "input": {
        "role": "user",
        "text": "還有一杯無糖紅茶"
      },
      "expected": {
        "flow": "intake",
        "should_commit": true,
        "should_create_new_version": true,
        "target_same_meal_thread": true
      }
    },
    {
      "turn_id": 3,
      "channel": "chat",
      "input": {
        "role": "user",
        "text": "白飯其實只吃半碗"
      },
      "expected": {
        "flow": "intake",
        "should_commit": true,
        "should_create_new_version": true,
        "target_same_meal_thread": true
      }
    }
  ]
}
```

### `expected_outputs.json`

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

### `expected_state_delta.json`

```json
{
  "meal_threads_created": 1,
  "meal_versions_created": 3,
  "meal_items_created": 3,
  "ledger_entries_created": 3,
  "body_plan_changed": false,
  "proposal_created": false
}
```

---

## 4. 設計原則

### 4.1 先定 state，再定語句

不要一開始只寫聊天內容。  
先定：

- 起始 state
- memory seed
- 預期 state delta

### 4.2 每一輪都要有預期

多輪 case 不能只寫最終結果。  
每一輪至少要知道：

- flow 是什麼
- 應不應 commit
- 應不應 clarify
- 是否應接到既有 thread

### 4.3 明確寫出不該發生的事

例如：

- 不該新建第二個 thread
- 不該建立 proposal
- 不該改 body plan

---

## 5. 適用情境

這個模板特別適合：

- intake multi-turn
- historical correction
- recommendation → intake handoff
- rescue → recommendation sync
- calibration → proposal gate
- cross-midnight stateful case
