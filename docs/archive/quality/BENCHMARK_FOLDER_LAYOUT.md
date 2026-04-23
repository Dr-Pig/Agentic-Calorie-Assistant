# Benchmark Folder Layout

## 1. 目的

這份文件定義 benchmark 在 repo 內的推薦資料夾結構。

目標：

- 讓 bucket 與 case class 清楚
- 讓 multi-turn / stateful case 易於維護
- 讓 regression case 易於追加

---

## 2. 推薦結構

```text
benchmarks/
  intake/
    single_turn/
    multi_turn/
    correction/
    time_handling/
    commit_boundary/
  recommendation/
    budget_fit/
    preference_fit/
    location_fallback/
    negative_preference/
    explicit_intake_handoff/
  calibration/
    insufficient_data/
    logging_quality_first/
    noise_only/
    mismatch/
    proposal_gate/
  rescue/
    same_day_soft_cap/
    short_horizon_spread/
    next_meal_protection/
    logging_first/
    non_viable_escalation/
  cross_flow/
    intake_to_recommendation/
    recommendation_to_intake/
    calibration_to_recommendation/
    rescue_to_recommendation/
    correction_to_ledger/
    cross_midnight/
```

---

## 3. 每個 case 目錄

每個 case 建議獨立成一個目錄：

```text
benchmarks/intake/multi_turn/intake_multi_turn_001/
  case.yaml
  initial_state.json
  memory_seed.json
  turns.json
  expected_outputs.json
  expected_state_delta.json
  notes.md
```

---

## 4. Regression Cases

建議每個主要 bucket 下都有明確的 regression 區，或用 tag 標記：

```text
benchmarks/intake/multi_turn/regressions/
benchmarks/recommendation/negative_preference/regressions/
```

若不想另開資料夾，也至少要在 `case.yaml` 標記：

```yaml
case_class: regression
source_type: failure_replay
```

---

## 5. Safety-Critical Cases

建議 safety-critical case 可用兩種方式管理：

### 方式 A

直接放在各 bucket 內，用 metadata 標：

```yaml
safety_classification: safety_critical
```

### 方式 B

另外維護一份聚合索引：

```text
benchmarks/_indexes/safety_critical_cases.yaml
```

---

## 6. Shared Indexes

建議至少維護：

- `benchmarks/_indexes/all_cases.yaml`
- `benchmarks/_indexes/regression_cases.yaml`
- `benchmarks/_indexes/safety_critical_cases.yaml`

這樣後續跑測試時：

- 可以依 bucket 跑
- 可以依 regression 跑
- 可以只跑 safety-critical set

---

## 7. 版本治理

建議：

- benchmark 版本獨立於 app 版本
- 每次新增重要 case 時更新索引
- regression case 不刪，只升版

---

## 8. 命名建議

case id 建議格式：

```text
<bucket>_<class>_<seq>
```

例如：

- `intake_multi_turn_golden_001`
- `recommendation_negative_preference_regression_002`
- `rescue_non_viable_escalation_edge_001`

---

## 9. 開放問題

1. 是否要把 `golden / edge / adversarial / regression` 拆成子資料夾
2. 是否要把真實 replay case 與 synthetic case 分倉
