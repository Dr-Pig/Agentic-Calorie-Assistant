# L5D Suite Governance Spec

## 1. 目的

本文件定義**全產品測試集版圖**的 suite-level 治理規範。

它回答：

- 全產品有哪些 suite family
- 每個 suite 的 authority tier 是什麼
- suite 與 workflow / capability / validation layer 如何對應
- 現有 benchmark / tests / runners 如何映射到新 taxonomy
- Official Golden 如何經由 candidate queue 與 batch review promotion

它不取代：

- `L5A_EVAL_SPEC.md` 的 eval mechanics、score shapes、release gates
- `L5B_BENCHMARK_SPEC.md` 的 bucket taxonomy、case classes、source mix、case schema
- `L5C_SAFETY_GUARDRAIL_SPEC.md` 的 safety / guardrail 邊界

本文件的定位是：

- **suite-level governance layer**
- 不是新的 unified runner implementation
- 不是 production runtime contract
- 不是新的平行 benchmark philosophy

---

## 2. 與 L5A / L5B / L5C / L6F 的關係

### 2.1 與 L5A 的關係

`L5A` 保留：

- eval levels
- eval dimensions
- trace requirements
- pass-level / flow-level / cross-flow / end-to-end 評估 mechanics
- release gate posture

`L5D` 只新增 suite inventory 與 authority 治理：

- `suite_id`
- `authority_tier`
- `maturity_status`
- `workflow_family`
- `capability_family`
- `validation_layer`
- `approval_owner`

### 2.2 與 L5B 的關係

`L5B` 保留：

- benchmark bucket map
- case classes
- minimum case counts
- source mix
- case schema

`L5D` 不取代 bucket taxonomy。對 intake 等成熟 workflow，`L5B` bucket 是 scenario-level parent grouping；`L5D` suite 是 finer-grained execution unit。

### 2.3 與 L5C 的關係

凡屬 `safety_critical`、guardrail、hard-fail / soft-fail 邊界的 suite，仍須受 `L5C` 約束。`L5D` 不重複定義 safety threshold。

### 2.4 與 L6F 的關係

凡牽涉 routing truth 的 suite，primary oracle 仍須遵守 `L6F`：

- `target object`
- `workflow ownership`
- `disposition`
- `workflow effect`

response-side distinctions 不得進 Official Golden primary oracle。

---

## 3. Authority Tiers

每個 suite 必須屬於以下其中一層：

- `Official Golden`
- `Provisional Exploratory`
- `Smoke / Infra`

### 3.1 Official Golden

特性：

- 需要明確產品核准
- 不接受未拍板產品語意
- 不接受 ambiguity case
- 可作為 regression gate

### 3.2 Provisional Exploratory

特性：

- 可收 drift cluster、競爭解讀、模糊題、founder-fit exploratory evidence
- 可用來找 failure topology
- 不得冒充官方 correctness

### 3.3 Smoke / Infra

特性：

- 只驗 runner / harness / schema / registry / logging / plumbing
- 可驗單元層 regression
- 不代表產品語意被核准

---

## 4. Suite Manifest 最小欄位

每個 suite manifest 至少應包含：

- `suite_id`
- `title`
- `authority_tier`
- `maturity_status`
- `workflow_family`
- `capability_family`
- `validation_layer`
- `approval_owner`
- `primary_oracle_fields`
- `allows_ambiguity`
- `parent_bucket`（若適用）

建議的 `maturity_status`：

- `authored_active`
- `planned_not_yet_authored`
- `legacy_mapped`
- `deprecated_exploratory`

對 `Official Golden`，`primary_oracle_fields` 預設只允許：

- `target object`
- `workflow ownership`
- `disposition`
- `workflow effect`

---

## 5. Validation Layer 上限框架

全產品的 validation layer 上限框架為：

- `workflow_canonical_action`
- `pass_or_node_decision`
- `cross_turn_progression`
- `cross_workflow_boundary`
- `capability_service`
- `response_contract`
- `degraded_or_fallback`
- `smoke_infra`

這是全產品**最大可能範圍**，不是每個 workflow 都必須完整覆蓋。

正式規則：

- 成熟 workflow 可覆蓋多層
- `planned_not_yet_authored` workflow 只需使用其合理子集
- 未成熟 workflow 不得因 taxonomy 壓力被迫假裝已有 canonical graph

---

## 6. Suite Inventory v1

### 6.1 Intake

| suite_id | authority_tier | maturity_status | validation_layer | parent_bucket |
| --- | --- | --- | --- | --- |
| `intake_task_meal_link_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `pass_or_node_decision` | `intake_single_turn` |
| `intake_decision_clarify_vs_proceed_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `pass_or_node_decision` | `commit_boundary` |
| `intake_nutrition_resolution_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `pass_or_node_decision` | `intake_single_turn` |
| `intake_final_response_contract_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `response_contract` | `intake_single_turn` |
| `intake_followup_question_generation_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `response_contract` | `intake_multi_turn` |
| `intake_followup_turn2_continuation_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `cross_turn_progression` | `intake_multi_turn` |
| `intake_followup_answer_integration_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `cross_turn_progression` | `intake_multi_turn` |
| `intake_same_thread_vs_new_meal_boundary_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `cross_workflow_boundary` | `commit_boundary` |
| `intake_correction_action_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `workflow_canonical_action` | `historical_correction` |
| `intake_open_new_workflow_boundary_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `cross_workflow_boundary` | `commit_boundary` |
| `intake_founder_fit_primary_golden_v1` | `Official Golden` | `legacy_mapped` | `workflow_canonical_action` | `intake_single_turn` |
| `intake_turn2_hybrid_replay_golden_v1` | `Official Golden` | `legacy_mapped` | `cross_turn_progression` | `intake_multi_turn` |
| `intake_runtime_smoke_v1` | `Smoke / Infra` | `legacy_mapped` | `smoke_infra` | `none` |

### 6.2 Rescue

| suite_id | authority_tier | maturity_status | validation_layer | parent_bucket |
| --- | --- | --- | --- | --- |
| `rescue_trigger_assessment_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `pass_or_node_decision` | `rescue_logging_first` |
| `rescue_option_shaping_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `pass_or_node_decision` | `rescue_short_horizon_spread` |
| `rescue_accept_action_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `workflow_canonical_action` | `rescue_short_horizon_spread` |
| `rescue_reject_action_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `workflow_canonical_action` | `rescue_logging_first` |
| `rescue_defer_action_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `workflow_canonical_action` | `rescue_same_day_soft_cap` |
| `rescue_adjust_action_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `workflow_canonical_action` | `rescue_short_horizon_spread` |
| `rescue_answer_only_boundary_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `cross_workflow_boundary` | `rescue_logging_first` |
| `rescue_response_contract_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `response_contract` | `rescue_short_horizon_spread` |
| `rescue_runtime_smoke_v1` | `Smoke / Infra` | `legacy_mapped` | `smoke_infra` | `none` |

### 6.3 Recommendation

| suite_id | authority_tier | maturity_status | validation_layer | parent_bucket |
| --- | --- | --- | --- | --- |
| `recommendation_context_assembly_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `capability_service` | `recommendation_budget_fit` |
| `recommendation_candidate_retrieval_filtering_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `capability_service` | `recommendation_budget_fit` |
| `recommendation_ranking_selection_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `pass_or_node_decision` | `recommendation_preference_fit` |
| `recommendation_response_contract_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `response_contract` | `recommendation_preference_fit` |
| `recommendation_open_new_workflow_boundary_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `cross_workflow_boundary` | `recommendation_explicit_intake_handoff` |

### 6.4 Calibration

| suite_id | authority_tier | maturity_status | validation_layer | parent_bucket |
| --- | --- | --- | --- | --- |
| `calibration_observation_interpretation_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `pass_or_node_decision` | `calibration_noise_only` |
| `calibration_budget_adjustment_decision_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `pass_or_node_decision` | `calibration_mismatch` |
| `calibration_proposal_action_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `workflow_canonical_action` | `calibration_proposal_gate` |
| `calibration_response_contract_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `response_contract` | `calibration_proposal_gate` |
| `calibration_runtime_smoke_v1` | `Smoke / Infra` | `legacy_mapped` | `smoke_infra` | `none` |

### 6.5 Body Observation / General Chat

| suite_id | authority_tier | maturity_status | validation_layer | parent_bucket |
| --- | --- | --- | --- | --- |
| `body_observation_create_action_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `workflow_canonical_action` | `none` |
| `body_observation_response_contract_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `response_contract` | `none` |
| `body_observation_to_calibration_boundary_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `cross_workflow_boundary` | `cross_flow_state_sync` |
| `general_chat_answer_only_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `workflow_canonical_action` | `none` |
| `general_chat_open_workflow_boundary_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `cross_workflow_boundary` | `none` |

### 6.6 Retrieval / Memory / Context Packing / Fallback

| suite_id | authority_tier | maturity_status | validation_layer | parent_bucket |
| --- | --- | --- | --- | --- |
| `retrieval_candidate_selection_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `capability_service` | `none` |
| `retrieval_hit_quality_by_domain_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `capability_service` | `none` |
| `memory_write_eligibility_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `capability_service` | `memory_preference_override` |
| `memory_read_hit_selection_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `capability_service` | `memory_preference_override` |
| `context_packing_sufficiency_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `capability_service` | `cross_flow_state_sync` |
| `context_packing_priority_order_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `capability_service` | `cross_flow_state_sync` |
| `llm_fallback_retry_contract_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `degraded_or_fallback` | `tool_failure_conservative_fallback` |
| `degraded_mode_response_contract_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `degraded_or_fallback` | `tool_failure_need_more_info` |
| `bounded_repair_gate_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `degraded_or_fallback` | `tool_failure_no_commit` |
| `retrieval_runtime_smoke_v1` | `Smoke / Infra` | `legacy_mapped` | `smoke_infra` | `none` |
| `trace_contract_smoke_v1` | `Smoke / Infra` | `legacy_mapped` | `smoke_infra` | `none` |
| `quality_guard_smoke_v1` | `Smoke / Infra` | `legacy_mapped` | `smoke_infra` | `none` |
| `benchmark_harness_smoke_v1` | `Smoke / Infra` | `legacy_mapped` | `smoke_infra` | `none` |
| `semantic_routing_provisional_smoke_v1` | `Provisional Exploratory` | `legacy_mapped` | `cross_workflow_boundary` | `cross_flow_state_sync` |
| `semantic_routing_official_canonical_v1` | `Official Golden` | `legacy_mapped` | `cross_workflow_boundary` | `cross_flow_state_sync` |
| `semantic_routing_candidate_queue_v1` | `Provisional Exploratory` | `legacy_mapped` | `cross_workflow_boundary` | `cross_flow_state_sync` |

---

## 7. Migration Mapping 與既有資產

現有 benchmark / tests / runners 不得成為 orphan assets。第一份 mapping truth 應維護於：

- `docs/quality/L5D_SUITE_MIGRATION_MAPPING_TABLE_V1.md`

mapping table 至少必須覆蓋：

- `tests/`
- `docs/quality/benchmarks/`
- `docs/quality/AUDIT_RUNNER_REGISTRY.json`
- `docs/quality/AUDIT_FIXTURE_REGISTRY.json`
- semantic-routing provisional / official / candidate artifacts
- workflow-specific candidate queues
- batch review sheets

---

## 8. Official Golden Promotion Flow

Official Golden 的 promotion flow 固定為：

1. candidate queue
2. batch review sheet
3. user approval batch
4. promotion to official
5. official runner inclusion

規則：

- 只有 `Official Golden` 需要使用者核准
- `Provisional Exploratory` 與 `Smoke / Infra` 可由 implementer 維護
- 但不得被宣稱為 official truth

v1 具體 review artifacts 先收：

- `docs/quality/benchmarks/intake/intake_candidate_review_queue_v1.json`
- `docs/quality/benchmarks/rescue/rescue_candidate_review_queue_v1.json`
- `docs/quality/INTAKE_OFFICIAL_GOLDEN_BATCH_REVIEW_V1.md`
- `docs/quality/RESCUE_OFFICIAL_GOLDEN_BATCH_REVIEW_V1.md`

---

## 9. Runner Strategy

不新建 unified runner。先擴充現有 runner 生態，使其支援依下列 metadata 過濾：

- `authority_tier`
- `workflow_family`
- `validation_layer`
- `suite_id`

現有 runner / registry 若尚未攜帶上述 metadata，應先透過 mapping table 與 suite manifest 補齊，而不是另起一套平行執行系統。

v1 follow-through 先要求：

- `AUDIT_RUNNER_REGISTRY.json` 補 `suite_id / authority_tier / workflow_family / capability_family / validation_layer`
- `AUDIT_FIXTURE_REGISTRY.json` 補 `suite_id / authority_tier / workflow_family / capability_family / validation_layer`
