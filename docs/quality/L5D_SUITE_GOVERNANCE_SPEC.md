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
- `suite_archetype`
- `approval_mode`
- `truth_source`

### 2.2 與 L5B 的關係

`L5B` 保留：

- benchmark bucket map
- case classes
- minimum case counts
- source mix
- case schema

`L5D` 不取代 bucket taxonomy。對 intake 等成熟 workflow，`L5B` bucket 是 scenario-level parent grouping；`L5D` suite 是 finer-grained execution unit。

`L5D` 也允許從已核准的 Official Golden utterance pack 派生出 **executable action pack**，但這種 artifact：

- 不是新的 suite authority tier
- 不是新的產品真相來源
- 只能作為 runner input contract 的衍生層

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

- 不接受未拍板產品語意
- 不接受 ambiguity case
- 可作為 regression gate

`Official Golden` 不再被自動等同於「逐題使用者核准」。

是否需要 human gate，應由下列欄位共同決定：

- `suite_archetype`
- `approval_mode`
- `truth_source`

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

### 3.4 Approval Mode 與 Truth Source

`approval_mode` 只允許：

- `user_required`
- `agent_allowed`

`truth_source` 只允許：

- `product_semantic_decision`
- `canonical_spec_derivation`
- `runtime_contract_derivation`

正式矩陣：

- `utterance_governed + product_semantic_decision -> user_required`
- `executable_workflow + canonical_spec_derivation -> agent_allowed`
- `capability_service + canonical_spec_derivation -> agent_allowed`
- `Smoke / Infra + runtime_contract_derivation -> agent_allowed`

若某個 `Official Golden` suite 需要新的產品語意裁決，仍必須走 `user_required`。  
若某個 `Official Golden` suite 只是既有 canonical spec 的執行化或驗證化，則應使用 `agent_allowed`，不得因 `Official Golden` 三字就自動卡在人工 promotion。

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
- `suite_archetype`
- `approval_mode`
- `truth_source`
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

若 suite archetype 是 `capability_service` 或 `executable_workflow`，且官方真相直接來自既有 canonical spec / runtime contract，則可改用 workflow-specific 或 service-specific primary oracle fields，例如：

- `expected_service_outcome`
- `expected_runtime_outcome`

但不得藉此引入未拍板產品語意。

### 4.1A `general_chat` official truth posture

`general_chat` v1 official truth 先只核：

- `target_workflow_family`
- `disposition`
- `workflow_effect`
- `required_read_surfaces`

不核：

- tone
- explanation density
- inquiry vs explain
- wording style

對 budget-aware 與 goal-aware chat，`required_read_surfaces` 應直接對齊：

- `CurrentBudgetView`
- `ActiveBodyPlanView`

### 4.1B `intake` two-layer official truth posture

`intake` official truth 不應只停在全局 routing labels。

`intake` v1 應分兩層：

- Layer A：global routing truth
  - `target_object`
  - `target_workflow_family`
  - `disposition`
  - `workflow_effect`
- Layer B：workflow-specific decision truth
  - `meal_link_action`
  - `decision_next_action`
  - `commit_posture`

規則：

- Layer A 仍是 cross-product routing oracle
- Layer B 只在 intake suite 中補充，不回推成全局 routing taxonomy
- response wording 仍不得進 primary oracle

### 4.1C `rescue` two-layer official truth posture

`rescue` official truth 應維持 proposal-attached、deterministic-first 的兩層結構。

- Layer A：global routing truth
  - `target_object`
  - `target_workflow_family`
  - `disposition`
  - `workflow_effect`
- Layer B：workflow-specific decision truth
  - `proposal_action`
  - `adjust_direction`
  - `special_posture`

規則：

- `rescue` v1 surface contract 仍以單一 spread plan 為主，不回退到 intake-style 4-pass taxonomy
- `adjust_direction` 只在 `proposal_action = adjust` 時要求
- `special_posture` 只在 `logging_first` / `escalate` 等特殊姿態成立時要求
- rescue math、viability、cooldown、floor legality 不得被 response wording 取代

### 4.1D `recommendation` two-layer official truth posture

`recommendation` v1 official truth 應明確維持 non-mutating。

- Layer A：global routing truth
  - `target_object`
  - `target_workflow_family`
  - `disposition`
  - `workflow_effect`
- Layer B：workflow-specific decision truth
  - `candidate_set_action`
  - `ranking_posture`
  - `handoff_posture`

規則：

- recommendation 顯示、排序、或回應本身不建立 canonical intent state
- recommendation 若需要進入 commit，應顯式 handoff 到 intake，而不是在 recommendation 內偷做 mutation
- plan-changing 或 budget-changing suggestion 不得被降格成 recommendation；應走 proposal family

### 4.1E `calibration` two-layer official truth posture

`calibration` official truth 應區分 model posture 與 proposal posture，但兩者都屬 `calibration` workflow family。

- Layer A：global routing truth
  - `target_object`
  - `target_workflow_family`
  - `disposition`
  - `workflow_effect`
- Layer B：workflow-specific decision truth
  - `posture_class`
  - `proposal_gate_outcome`
  - `proposal_action_family`

規則：

- `calibration_model` 的 posture judgment 是 deterministic-first，不得讓 LLM 重做 truth judgment
- `calibration proposal response surface` 屬於 `calibration`，不屬於 `recommendation`
- `proposal_action_family` 只在 proposal lane active 時要求

### 4.1F `body_observation` two-layer official truth posture

`body_observation` v1 official truth 應保持 thin workflow，不把純 answer path 硬抬成 heavy graph。

- Layer A：global routing truth
  - `target_object`
  - `target_workflow_family`
  - `disposition`
  - `workflow_effect`
- Layer B：workflow-specific decision truth
  - `observation_action`

規則：

- create / ingest 路徑走 `body_observation`
- 純 read / answer path 可回到 `general_chat + answer_only`
- 若未來需要 handoff 到 calibration，應以顯式 Layer B decision truth 新增，不得偷混成 response phrasing

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

## 5A. Test Suite Archetype Policy

不是所有 suite 都需要同一種 artifact 形狀。

`candidate queue -> official canonical pack -> executable action pack` 這種三層鏈，只適用於少數**utterance truth 與 runtime input 明顯分離**的 suite。若把它當成全產品預設，會造成治理過重，並讓測試集結構脫離實際產品需求。

正式規則：

- suite 必須先選定 archetype，才能決定需要哪些 artifact
- archetype 應由驗證目標決定，不得因既有工具方便而倒推產品結構
- 不同 archetype 可共用 `authority_tier / workflow_family / validation_layer / suite_id` metadata
- 但不得被迫採用相同的 pack 深度

### 5A.1 Archetype A: Utterance-Governed Suite

適用情況：

- 主要驗證對話 utterance 的產品真相
- 主 oracle 需要經過人工核准
- utterance truth 與 runner 可執行輸入不是同一層
- runtime action 需要從已核准的 official utterance truth 派生

典型例子：

- `rescue_official_canonical_pack_v1`
- `intake_official_canonical_pack_v1`
- 後續高價值的 cross-workflow boundary suites

預設：

- `approval_mode = user_required`
- `truth_source = product_semantic_decision`

允許的 artifact 鏈：

1. `candidate_review_queue`
2. `official_canonical_pack`
3. `derived_executable_action_pack`（只有 runtime input 與 utterance truth 不同時才需要）

硬規則：

- `derived_executable_action_pack` 必須 subordinate to `official_canonical_pack`
- executable artifact 不得成為新的產品真相來源
- implementer 不得在 derivation 階段補寫未核准的產品語意

### 5A.2 Archetype B: Executable Workflow Suite

適用情況：

- 主要驗 workflow action、state transition、writeback、side effects
- runner 可直接取得可執行輸入
- 不需要先從對話 utterance 抽產品真相

典型例子：

- 已知 action 的 intake / rescue runtime workflow 驗證
- proposal persistence / writeback / mutation correctness
- read-model / commit-boundary / service orchestration 驗證

預設：

- `approval_mode = agent_allowed`
- `truth_source = canonical_spec_derivation`

建議 artifact：

- executable pack
- fixture set
- pytest / integration runner input

這類 suite **通常不需要**：

- `candidate_review_queue`
- `official_canonical_pack`

除非該 suite 同時承擔產品語意核准責任。

### 5A.3 Archetype C: Capability / Service Suite

適用情況：

- 主要驗 capability 或 service 本身
- 驗證對象不是對話 utterance，而是 retrieval / memory / context packing / fallback / guardrail / gate 行為

典型例子：

- retrieval hit selection
- memory write eligibility
- context packing sufficiency / priority
- fallback / bounded repair / deterministic guard

預設：

- `approval_mode = agent_allowed`
- `truth_source = canonical_spec_derivation`

建議 artifact：

- service benchmark pack
- pytest fixture
- smoke / infra registry entry

這類 suite 不應為了形式一致而額外長出 utterance-governed 三層 pack。

### 5A.4 Archetype Selection Rule

選 archetype 時，先問三件事：

1. 這個 suite 的 primary truth 是否是 **對話 utterance 的產品語意**？
2. 這個 suite 的 runner input 是否與 official truth **不是同一層**？
3. 這個 suite 的主要驗證對象是 **workflow execution** 還是 **capability/service behavior**？

決策規則：

- 若 `1 = yes` 且 `2 = yes`，選 `Utterance-Governed Suite`
- 若主要是 workflow action / state transition，選 `Executable Workflow Suite`
- 若主要是 retrieval / memory / context / fallback / guard，選 `Capability / Service Suite`

### 5A.5 Anti-Overdesign Rule

不得把 `candidate queue + official pack + executable pack` 當成全產品預設。

特別是下列情況，應避免三層化：

- 單純 capability/service 測試
- 純 runtime action correctness
- 已有 deterministic fixture 可直接執行的 integration suite
- 只需要 smoke / registry / harness plumbing 的 infra suite

---

## 6. Suite Inventory v1

### 6.1 Intake

| suite_id | authority_tier | maturity_status | validation_layer | parent_bucket |
| --- | --- | --- | --- | --- |
| `intake_task_meal_link_golden_v1` | `Official Golden` | `authored_active` | `pass_or_node_decision` | `intake_single_turn` |
| `intake_decision_clarify_vs_proceed_golden_v1` | `Official Golden` | `authored_active` | `pass_or_node_decision` | `commit_boundary` |
| `intake_nutrition_resolution_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `pass_or_node_decision` | `intake_single_turn` |
| `intake_final_response_contract_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `response_contract` | `intake_single_turn` |
| `intake_ledger_writeback_contract_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `workflow_canonical_action` | `commit_boundary` |
| `intake_followup_question_generation_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `response_contract` | `intake_multi_turn` |
| `intake_followup_turn2_continuation_golden_v1` | `Official Golden` | `authored_active` | `cross_turn_progression` | `intake_multi_turn` |
| `intake_followup_answer_integration_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `cross_turn_progression` | `intake_multi_turn` |
| `intake_same_thread_vs_new_meal_boundary_golden_v1` | `Official Golden` | `planned_not_yet_authored` | `cross_workflow_boundary` | `commit_boundary` |
| `intake_correction_action_golden_v1` | `Official Golden` | `authored_active` | `workflow_canonical_action` | `historical_correction` |
| `intake_open_new_workflow_boundary_golden_v1` | `Official Golden` | `authored_active` | `cross_workflow_boundary` | `commit_boundary` |
| `intake_founder_fit_primary_golden_v1` | `Official Golden` | `legacy_mapped` | `workflow_canonical_action` | `intake_single_turn` |
| `intake_turn2_hybrid_replay_golden_v1` | `Official Golden` | `legacy_mapped` | `cross_turn_progression` | `intake_multi_turn` |
| `intake_official_canonical_pack_v1` | `Official Golden` | `authored_active` | `workflow_canonical_action` | `intake_single_turn` |
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
| `rescue_official_canonical_pack_v1` | `Official Golden` | `authored_active` | `workflow_canonical_action` | `rescue_short_horizon_spread` |
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
| `general_chat_budget_query_golden_v1` | `Official Golden` | `authored_active` | `workflow_canonical_action` | `none` |
| `general_chat_goal_query_golden_v1` | `Official Golden` | `authored_active` | `workflow_canonical_action` | `none` |
| `general_chat_open_workflow_boundary_golden_v1` | `Official Golden` | `authored_active` | `cross_workflow_boundary` | `none` |
| `general_chat_official_canonical_pack_v1` | `Official Golden` | `authored_active` | `workflow_canonical_action` | `none` |

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

### 8.1 User-Required Promotion

當 `approval_mode = user_required` 時，promotion flow 固定為：

1. candidate queue
2. batch review sheet
3. user approval batch
4. promotion to official
5. official runner inclusion

### 8.2 Agent-Allowed Promotion

當 `approval_mode = agent_allowed` 時，promotion flow 固定為：

1. derive the suite from canonical spec / runtime contract truth
2. author or update the official artifact directly
3. run registry / fixture / promotion / contract checks
4. include the suite in official runner lanes
5. keep change traceability through execution docs and git history

規則：

- 只有 `approval_mode = user_required` 的 Official Golden 需要使用者核准
- `approval_mode = agent_allowed` 的 Official Golden 可由 agent 自行 author / review / promote
- `Provisional Exploratory` 與 `Smoke / Infra` 可由 implementer 維護
- 但不得被宣稱為 official truth

v1 具體 review artifacts 先收：

- `docs/quality/benchmarks/intake/intake_candidate_review_queue_v1.json`
- `docs/quality/benchmarks/rescue/rescue_candidate_review_queue_v1.json`
- `docs/quality/INTAKE_OFFICIAL_GOLDEN_BATCH_REVIEW_V1.md`
- `docs/quality/RESCUE_OFFICIAL_GOLDEN_BATCH_REVIEW_V1.md`

---

## 9. Derived Executable Action Packs

當某個 workflow 的 Official Golden utterance pack 已存在，但自動執行仍需要 workflow-specific runtime input 時，可建立 derived executable action pack。

定位：

- subordinate to the official utterance pack
- derived runtime-input contract only
- not a separate source of benchmark truth

正式規則：

- executable action pack 的 primary outcome 必須完全繼承 source official case：
  - `target object`
  - `workflow ownership`
  - `disposition`
  - `workflow effect`
- 若第一層 disposition 保持粗粒度，但 workflow runtime 仍需要可執行方向欄位，該欄位只能作為 workflow-specific execution detail 存在於 official / executable 層
  - v1 例：`rescue adjust` 保持 `disposition = adjust`，但可在 rescue 官方/可執行層補 `adjust_direction`
- executable action pack 可以新增：
  - `state_seed` 或 `proposal_seed`
  - `execution_mode`
  - `runtime_action`
  - `block_reason`
- 若 source official case 尚無唯一 runtime action mapping，必須顯式標記：
  - `derivation_status = blocked_pending_runtime_action_choice`
- blocked executable case 不得假裝成可直接 auto-run

v1 derived executable artifacts 先收：

- `docs/quality/benchmarks/intake/intake_executable_action_pack_v1.json`
- `docs/quality/benchmarks/rescue/rescue_executable_action_pack_v1.json`

它們是 workflow-specific runner input contract，不是新的 Official Golden suite。

---

## 9A. Batch Authoring Surfaces

為避免後續 suite 擴張時每次手工拼 artifact，v1 標準 batch authoring surface 先收：

- `docs/quality/benchmarks/templates/candidate_review_queue_template.json`
- `docs/quality/benchmarks/templates/official_canonical_pack_template.json`
- `docs/quality/benchmarks/templates/executable_action_pack_template.json`
- `scripts/create_benchmark_artifact.py`

規則：

- template 只提供 artifact 形狀，不提供新產品語意
- 由 template scaffold 出來的 artifact，仍須遵守對應的 `approval_mode` / `truth_source` 規則
- `agent_allowed` suite 可直接從 canonical spec 衍生 author；`user_required` suite 仍須先走 candidate queue / batch review

---

## 10. Runner Strategy

不新建 unified runner。先擴充現有 runner 生態，使其支援依下列 metadata 過濾：

- `authority_tier`
- `workflow_family`
- `validation_layer`
- `suite_id`

現有 runner / registry 若尚未攜帶上述 metadata，應先透過 mapping table 與 suite manifest 補齊，而不是另起一套平行執行系統。

v1 follow-through 先要求：

- `AUDIT_RUNNER_REGISTRY.json` 補 `suite_id / authority_tier / workflow_family / capability_family / validation_layer`
- `AUDIT_FIXTURE_REGISTRY.json` 補 `suite_id / authority_tier / workflow_family / capability_family / validation_layer`
- `scripts/check_audit_runner_contract.py` 與 `scripts/check_audit_fixture_safety.py` 必須把上述 metadata 當成 hard-gated registry contract，而不是 advisory fields
- `scripts/check_suite_promotion_contract.py` 必須驗 intake / rescue official packs 與其 candidate queues 的 promotion linkage、approved status、與 primary outcome 對齊
- `scripts/check_executable_action_pack_contract.py` 必須驗 derived executable action packs 與 source official packs 的 linkage、primary outcome inheritance、以及 blocked derivation 顯式化
