# V2 Wave 1 Micro-Suite Cases

## 目的

本文件定義 **Wave 1 capability micro-suites 的第一版 MVP cases**。

它的角色是：

- 將 `V2_WAVE_1_CAPABILITY_MICRO_SUITES.md` 的 suite 骨架落成可實作 runner 的 case-level contracts
- 先建立少量、高訊號、可腳本驗證的 capability cases
- 幫助 coding agent 依 system-capability build order 分段建置，而不是直接 patch historical acceptance packages

本文件不是：

- 完整 benchmark 大全集
- founder quality review set
- product copywriting benchmark
- final runner implementation

---

## 使用方式

### 日常開發
只跑與當前修改相關的 suite。

### Manager-style intake readiness
跑 MVP micro-suites + current Manager-style intake diagnostics。

### Wave 1 readiness
跑完整 micro-suites + current Manager-style intake diagnostics + benchmark v1/v2 + turn2 replay。

---

## Case 格式

```yaml
case_id:
suite_id:
primary_capability:
primary_failure_family:
setup_state:
input:
expected_contract:
forbidden_outcomes:
verification_type:
notes:
```

### verification_type
- `deterministic`
- `deterministic_plus_artifact`
- `mixed`

---

# Phase A — Routing & Boundary MVP Cases

## MS1 — Intent / Thread Resolution

### MS1-001 New meal creates new thread
```yaml
case_id: MS1-001
suite_id: MS1
primary_capability: F2.1 Intake Routing / Thread Intent Detection
primary_failure_family: FAM-THREAD
setup_state:
  active_meal_thread: null
  active_body_plan: present
input: "我剛剛喝了一杯珍珠奶茶"
expected_contract:
  interaction_type: intake_logging
  thread_action: create_new_meal_thread
  target_thread: new
  no_ledger_mutation_before_commit_decision: true
forbidden_outcomes:
  - classify_as_info_query
  - attach_to_nonexistent_thread
  - skip_thread_resolution
verification_type: deterministic
notes: 建立新 meal thread，不代表一定立即 commit；commit 由 MS7 判定。
```

### MS1-002 Same-meal followup attaches to existing draft
```yaml
case_id: MS1-002
suite_id: MS1
primary_capability: F2.1 Intake Routing / Thread Intent Detection
primary_failure_family: FAM-THREAD
setup_state:
  active_meal_thread:
    status: needs_clarification
    last_user_item: 珍珠奶茶
    canonical_commit: false
  active_body_plan: present
input: "半糖大杯"
expected_contract:
  interaction_type: same_meal_followup
  thread_action: attach_to_existing_thread
  target_thread: active_meal_thread
forbidden_outcomes:
  - create_new_meal_thread
  - classify_as_unrelated_new_meal
  - lose_previous_item_context
verification_type: deterministic
notes: 這是 turn2 replay 的核心前置能力。
```

### MS1-003 Correction targets prior committed meal
```yaml
case_id: MS1-003
suite_id: MS1
primary_capability: F2.1 Intake Routing / Thread Intent Detection
primary_failure_family: FAM-THREAD
setup_state:
  prior_meal_thread:
    status: committed
    items:
      - name: 豆漿
        kcal: 80
      - name: 牛肉麵
        kcal: 650
input: "剛剛豆漿我記錯了，是無糖大杯"
expected_contract:
  interaction_type: correction
  thread_action: target_existing_committed_thread
  target_item_candidate: 豆漿
forbidden_outcomes:
  - create_new_meal_thread
  - modify_all_items
  - classify_as_info_query
verification_type: deterministic
notes: 只測 intent/thread targeting，不測最後 correction kcal。
```

### MS1-004 Info query does not mutate meal state
```yaml
case_id: MS1-004
suite_id: MS1
primary_capability: F2.1 Intake Routing / Thread Intent Detection
primary_failure_family: FAM-THREAD
setup_state:
  day_ledger:
    consumed_kcal: 1200
    target_kcal: 1800
input: "我今天目前吃了多少？"
expected_contract:
  interaction_type: info_query
  thread_action: no_meal_mutation
  ledger_read_requested: true
forbidden_outcomes:
  - create_new_meal_thread
  - mutate_ledger
  - ask_food_clarification
verification_type: deterministic
notes: query 不應誤進 intake mutation path。
```

---

## MS2 — Clarify Mode Selection

### MS2-001 Pearl milk tea allows estimate with followup
```yaml
case_id: MS2-001
suite_id: MS2
primary_capability: F2.2 Clarify Mode Selection
primary_failure_family: FAM-CLARIFY
setup_state:
  active_body_plan: present
input: "我喝了一杯珍珠奶茶"
expected_contract:
  clarify_mode: estimate_with_followup
  provisional_range_allowed: true
  followup_required: true
  followup_should_ask_about:
    - size
    - sugar_level
forbidden_outcomes:
  - clarify_before_estimate_only
  - canonical_commit_true_without_size_or_sugar
  - exact_value_claim
verification_type: deterministic
notes: 珍奶資訊不足但可給 range，不應完全不估。
```

### MS2-002 Homemade dish requires clarify before estimate
```yaml
case_id: MS2-002
suite_id: MS2
primary_capability: F2.2 Clarify Mode Selection
primary_failure_family: FAM-CLARIFY
setup_state:
  active_body_plan: present
input: "我剛吃了我媽煮的家常菜"
expected_contract:
  clarify_mode: clarify_before_estimate
  provisional_range_allowed: false
  followup_required: true
  followup_should_ask_about:
    - dishes_or_ingredients
    - portion
forbidden_outcomes:
  - provide_kcal_range_without_composition
  - canonical_commit_true
  - tavily_retrieval_selected
verification_type: deterministic
notes: 組成未知時，不應用 search 或粗估假裝有根據。
```

### MS2-003 Sufficient simple meal can direct commit
```yaml
case_id: MS2-003
suite_id: MS2
primary_capability: F2.2 Clarify Mode Selection
primary_failure_family: FAM-CLARIFY
setup_state:
  active_body_plan: present
input: "我吃了一碗白飯和一份炒青菜"
expected_contract:
  clarify_mode: direct_commit
  followup_required: false
  provisional_range_allowed: true
forbidden_outcomes:
  - unnecessary_followup
  - clarify_before_estimate
verification_type: deterministic
notes: 不要過度追問，否則聊天體驗會變差。
```

---

## MS7 — Draft vs Commit Boundary

### MS7-001 First pearl milk tea turn remains draft
```yaml
case_id: MS7-001
suite_id: MS7
primary_capability: F2.4 Draft vs Commit Candidacy
primary_failure_family: FAM-STATE
setup_state:
  active_body_plan: present
input: "我喝了一杯珍珠奶茶"
expected_contract:
  canonical_commit: false
  meal_thread_status: needs_clarification
  ledger_delta_kcal: 0
  show_macro: false
forbidden_outcomes:
  - ledger_mutated
  - consumed_kcal_changed
  - show_macro_true
  - response_claims_fully_recorded
verification_type: deterministic
notes: 可給 provisional range，但不可進 committed ledger。
```

### MS7-002 Second pearl milk tea turn commits
```yaml
case_id: MS7-002
suite_id: MS7
primary_capability: F2.4 Draft vs Commit Candidacy
primary_failure_family: FAM-STATE
setup_state:
  active_meal_thread:
    status: needs_clarification
    item: 珍珠奶茶
    canonical_commit: false
input: "半糖大杯"
expected_contract:
  canonical_commit: true
  meal_thread_status: committed
  ledger_delta_kcal_positive: true
forbidden_outcomes:
  - create_new_meal_thread
  - remain_draft_without_reason
  - ledger_delta_kcal_zero
verification_type: deterministic
notes: 前一輪 draft 應被完成，而不是新建一餐。
```

### MS7-003 Homemade dish remains draft until composition known
```yaml
case_id: MS7-003
suite_id: MS7
primary_capability: F2.4 Draft vs Commit Candidacy
primary_failure_family: FAM-STATE
setup_state:
  active_body_plan: present
input: "我吃了家常菜"
expected_contract:
  canonical_commit: false
  ledger_delta_kcal: 0
  followup_required: true
forbidden_outcomes:
  - canonical_commit_true
  - ledger_mutated
  - exact_value_claim
verification_type: deterministic
notes: 防止 ambiguous homemade dish 被硬 commit。
```

---

## MS14 — No-Plan Fallback Honesty

### MS14-001 Intake allowed without body plan
```yaml
case_id: MS14-001
suite_id: MS14
primary_capability: F1.2 No-Plan Fallback
primary_failure_family: FAM-BOOT
setup_state:
  active_body_plan: null
input: "我吃了一顆茶葉蛋"
expected_contract:
  intake_allowed: true
  budget_answer_mode: degraded
  may_log_food: true
forbidden_outcomes:
  - refuse_all_intake
  - hallucinate_remaining_kcal
verification_type: deterministic
notes: 沒有 plan 不代表不能記食物。
```

### MS14-002 No concrete remaining budget without plan
```yaml
case_id: MS14-002
suite_id: MS14
primary_capability: F1.2 No-Plan Fallback
primary_failure_family: FAM-BOOT
setup_state:
  active_body_plan: null
  day_ledger:
    consumed_kcal: 600
input: "我今天還可以吃多少？"
expected_contract:
  budget_answer_mode: degraded
  concrete_remaining_kcal_allowed: false
  onboarding_guidance_allowed: true
forbidden_outcomes:
  - reply_with_specific_remaining_kcal
  - pretend_target_exists
verification_type: deterministic
notes: 可說目前已記錄 consumed，但不能假造 target / remaining。
```

---

# Phase B — Evidence Stack MVP Cases

## MS3 — Evidence Path Selection

### MS3-001 Exact DB hit should use exact DB
```yaml
case_id: MS3-001
suite_id: MS3
primary_capability: F2.3b Evidence Path Selection
primary_failure_family: FAM-GROUND
setup_state:
  exact_db:
    contains:
      - brand: Starbucks
        item: 冰那堤 Tall
        kcal: 100
input: "我喝了一杯星巴克 Tall 冰那堤"
expected_contract:
  selected_evidence_path: exact_db
  tavily_called: false
  exactness_posture: exact
forbidden_outcomes:
  - selected_evidence_path: tavily_retrieval
  - selected_evidence_path: generic_db
  - heuristic_estimate_without_db
verification_type: deterministic
notes: exact DB hit 不應走 search 或 generic。
```

### MS3-002 Store dish DB miss should use Tavily candidate lane
```yaml
case_id: MS3-002
suite_id: MS3
primary_capability: F2.3b Evidence Path Selection
primary_failure_family: FAM-GROUND
setup_state:
  exact_db:
    contains: []
input: "我吃了勝王的牛白湯拉麵"
expected_contract:
  selected_evidence_path: tavily_retrieval
  query_should_include:
    - 勝王
    - 牛白湯
    - 拉麵
forbidden_outcomes:
  - direct_exact_claim_without_evidence
  - homemade_clarify_mode
  - generic_ramen_estimate_as_exact
verification_type: deterministic
notes: 店家/品項明確但 DB miss，適合 candidate retrieval。
```

### MS3-003 Homemade ambiguous food should ask user, not search
```yaml
case_id: MS3-003
suite_id: MS3
primary_capability: F2.3b Evidence Path Selection
primary_failure_family: FAM-GROUND
setup_state:
  active_body_plan: present
input: "我吃了一些我家煮的滷味"
expected_contract:
  selected_evidence_path: ask_user
  tavily_called: false
  clarify_needed: true
forbidden_outcomes:
  - selected_evidence_path: tavily_retrieval
  - exactness_posture: exact
  - canonical_commit_true
verification_type: deterministic
notes: 滷味關鍵在品項與份量，不是 web search。
```

### MS3-004 Generic anchored food can use generic DB
```yaml
case_id: MS3-004
suite_id: MS3
primary_capability: F2.3b Evidence Path Selection
primary_failure_family: FAM-GROUND
setup_state:
  generic_db:
    contains:
      - food: 茶葉蛋
input: "我吃了一顆茶葉蛋"
expected_contract:
  selected_evidence_path: generic_db
  tavily_called: false
  canonical_commit_allowed: true
forbidden_outcomes:
  - unnecessary_tavily_retrieval
  - ask_user_for_unnecessary_details
verification_type: deterministic
notes: 通用明確食物可直接 generic anchor。
```

---

## MS4 — Tavily Retrieval Usage

### MS4-001 Tavily query preserves entity anchors
```yaml
case_id: MS4-001
suite_id: MS4
primary_capability: F2.3b / F2.3 Tavily Retrieval Usage
primary_failure_family: FAM-GROUND
setup_state:
  exact_db:
    contains: []
input: "我吃了勝王牛白湯拉麵"
expected_contract:
  tavily_called: true
  query_contains_all:
    - 勝王
    - 牛白湯
    - 拉麵
  retrieval_artifact_required: true
forbidden_outcomes:
  - query_only: 拉麵 熱量
  - no_retrieval_artifact
verification_type: deterministic_plus_artifact
notes: query 太泛會讓 search 無法提供有用 evidence。
```

### MS4-002 Tavily snippet cannot become truth directly
```yaml
case_id: MS4-002
suite_id: MS4
primary_capability: F2.3b / F2.3 Tavily Retrieval Usage
primary_failure_family: FAM-GROUND
setup_state:
  tavily_result:
    snippet: "某部落格提到這碗拉麵份量很大"
    extracted_kcal: null
input: "我吃了勝王牛白湯拉麵"
expected_contract:
  normalized_evidence_packet_exists: true
  evidence_usability_classification: unusable_or_anchor_only
  exactness_posture_not_exact: true
forbidden_outcomes:
  - exact_value_claim_from_snippet
  - canonical_commit_exact
verification_type: deterministic_plus_artifact
notes: Tavily 是 candidate retrieval，不是 truth oracle。
```

### MS4-003 Tavily should not be called for homemade composition ambiguity
```yaml
case_id: MS4-003
suite_id: MS4
primary_capability: F2.3b / F2.3 Tavily Retrieval Usage
primary_failure_family: FAM-GROUND
setup_state:
  active_body_plan: present
input: "我吃了媽媽煮的一盤菜"
expected_contract:
  tavily_called: false
  selected_evidence_path: ask_user
forbidden_outcomes:
  - tavily_called_true
  - web_search_query_generated
verification_type: deterministic
notes: composition ambiguity 要問人，不是問網路。
```

---

## MS5 — Evidence Normalization

### MS5-001 Exact DB result normalizes into evidence packet
```yaml
case_id: MS5-001
suite_id: MS5
primary_capability: F2.3 Evidence Normalization
primary_failure_family: FAM-GROUND
setup_state:
  exact_db_result:
    source_type: internal_exact_db
    brand: Starbucks
    item: 冰那堤 Tall
    kcal: 100
input: "我喝了一杯星巴克 Tall 冰那堤"
expected_contract:
  normalized_evidence_packet_exists: true
  source_type: internal_exact_db
  matched_entity: 星巴克 Tall 冰那堤
  extracted_kcal_present: true
  identity_confidence: high
  usable_for_exact: true
forbidden_outcomes:
  - missing_source_type
  - missing_identity_confidence
  - usable_classification_missing
verification_type: deterministic
notes: DB result 也要 packet 化，方便下游一致處理。
```

### MS5-002 Tavily result with unclear serving is not exact
```yaml
case_id: MS5-002
suite_id: MS5
primary_capability: F2.3 Evidence Normalization
primary_failure_family: FAM-GROUND
setup_state:
  tavily_result:
    source_type: web
    matched_entity: 勝王牛白湯拉麵
    extracted_kcal: null
    serving_basis: unknown
input: "我吃了勝王牛白湯拉麵"
expected_contract:
  normalized_evidence_packet_exists: true
  serving_basis: unknown
  usable_for_exact: false
  usability_classification: unusable_or_anchor_only
forbidden_outcomes:
  - usable_for_exact_true
  - exactness_posture: exact
verification_type: deterministic
notes: serving unclear 不可 exact。
```

---

## MS6 — Estimate / Grounding Synthesis

### MS6-001 Exact evidence produces exact posture
```yaml
case_id: MS6-001
suite_id: MS6
primary_capability: F2.3 Estimate / Grounding Synthesis
primary_failure_family: FAM-GROUND
setup_state:
  normalized_evidence_packet:
    usable_for_exact: true
    extracted_kcal: 100
    identity_confidence: high
input: "我喝了一杯星巴克 Tall 冰那堤"
expected_contract:
  exactness_posture: exact
  kcal_value: 100
  uncertainty_level: low
forbidden_outcomes:
  - unnecessary_range_only
  - high_uncertainty
verification_type: deterministic
notes: 這題應該不需要 LLM judge。
```

### MS6-002 Ambiguous ramen evidence produces anchored range, not exact
```yaml
case_id: MS6-002
suite_id: MS6
primary_capability: F2.3 Estimate / Grounding Synthesis
primary_failure_family: FAM-GROUND
setup_state:
  normalized_evidence_packet:
    usable_for_exact: false
    usable_for_anchor: true
    matched_entity: 勝王牛白湯拉麵
    serving_basis: unknown
input: "我吃了勝王牛白湯拉麵"
expected_contract:
  exactness_posture: anchored_estimate
  range_required: true
  likely_value_allowed: true
  uncertainty_level: medium_or_high
forbidden_outcomes:
  - exactness_posture: exact
  - exact_value_claim
verification_type: mixed
notes: 需要 LLM 做合理 synthesis，但 contract 可 deterministic 驗。
```

---

# Phase C — Mutation & Projection MVP Cases

## MS8 — Correction Integrity & Versioning

### MS8-001 Correction preserves non-target item
```yaml
case_id: MS8-001
suite_id: MS8
primary_capability: F2.5 Correction / Removal / Supersede
primary_failure_family: FAM-CORR
setup_state:
  prior_meal_thread:
    status: committed
    version: 1
    items:
      - name: 豆漿
        kcal: 80
      - name: 牛肉麵
        kcal: 650
input: "豆漿我記錯了，是無糖大杯"
expected_contract:
  meal_version_delta: new_version_created
  target_item_modified: 豆漿
  non_target_items_preserved:
    - 牛肉麵
  ledger_recalculation_required: true
forbidden_outcomes:
  - 牛肉麵_removed_or_modified
  - overwrite_without_version_lineage
verification_type: deterministic
notes: correction 最重要是不污染 unrelated items。
```

### MS8-002 Item removal does not delete whole meal thread
```yaml
case_id: MS8-002
suite_id: MS8
primary_capability: F2.5 Correction / Removal / Supersede
primary_failure_family: FAM-CORR
setup_state:
  prior_meal_thread:
    status: committed
    items:
      - name: 豆漿
        kcal: 80
      - name: 饅頭
        kcal: 220
input: "豆漿我其實沒喝"
expected_contract:
  target_item_removed: 豆漿
  meal_thread_still_exists: true
  non_target_items_preserved:
    - 饅頭
  ledger_delta_negative: true
forbidden_outcomes:
  - delete_entire_meal_thread
  - remove_non_target_item
verification_type: deterministic
notes: remove item 不等於刪整餐。
```

---

## MS9 — Ledger Mutation & Overshoot Truth

### MS9-001 Committed meal mutates ledger
```yaml
case_id: MS9-001
suite_id: MS9
primary_capability: F3.1 Ledger Mutation
primary_failure_family: FAM-SYNC
setup_state:
  day_ledger:
    consumed_kcal: 500
    target_kcal: 1800
  meal_result:
    canonical_commit: true
    kcal: 400
input: commit_meal_result
expected_contract:
  ledger_delta_kcal: 400
  consumed_kcal_after: 900
  remaining_kcal_after: 900
forbidden_outcomes:
  - ledger_delta_kcal: 0
  - remaining_recomputed_in_renderer_only
verification_type: deterministic
notes: commit 才能改 ledger。
```

### MS9-002 Draft meal does not mutate ledger
```yaml
case_id: MS9-002
suite_id: MS9
primary_capability: F3.1 Ledger Mutation
primary_failure_family: FAM-SYNC
setup_state:
  day_ledger:
    consumed_kcal: 500
    target_kcal: 1800
  meal_result:
    canonical_commit: false
    provisional_kcal_range: 300-600
input: draft_meal_result
expected_contract:
  ledger_delta_kcal: 0
  consumed_kcal_after: 500
forbidden_outcomes:
  - mutate_consumed_kcal
  - overshoot_from_draft
verification_type: deterministic
notes: provisional estimate 不進 ledger。
```

### MS9-003 Overshoot comes from ledger truth
```yaml
case_id: MS9-003
suite_id: MS9
primary_capability: F3.2 Overshoot Presentation
primary_failure_family: FAM-SYNC
setup_state:
  day_ledger:
    consumed_kcal: 1700
    target_kcal: 1800
  committed_meal_delta_kcal: 300
input: commit_meal_result
expected_contract:
  consumed_kcal_after: 2000
  overshoot_amount: 200
  overshoot_source: ledger
forbidden_outcomes:
  - response_layer_recomputed_different_overshoot
  - overshoot_amount_mismatch_between_chat_and_ui
verification_type: deterministic
notes: overshoot 是 ledger truth，不是 wording 層自由算。
```

---

## MS10 — Macro Visibility Policy

### MS10-001 Draft hides macro
```yaml
case_id: MS10-001
suite_id: MS10
primary_capability: F3.3 Macro Visibility Policy
primary_failure_family: FAM-GROUND
setup_state:
  meal_result:
    canonical_commit: false
    kcal_range: 300-600
input: render_intake_result
expected_contract:
  show_macro: false
forbidden_outcomes:
  - show_macro_true
  - display_precise_macro_values
verification_type: deterministic
notes: draft 不秀三大營養素。
```

### MS10-002 Macro alignment failure hides macro
```yaml
case_id: MS10-002
suite_id: MS10
primary_capability: F3.3 Macro Visibility Policy
primary_failure_family: FAM-GROUND
setup_state:
  meal_result:
    canonical_commit: true
    kcal: 500
    protein_g: 10
    carbs_g: 20
    fat_g: 10
    macro_alignment_status: fail
input: render_intake_result
expected_contract:
  show_macro: false
forbidden_outcomes:
  - show_macro_true
verification_type: deterministic
notes: macro math 對不起來時不要秀 macro。
```

### MS10-003 Clean committed macro may show macro
```yaml
case_id: MS10-003
suite_id: MS10
primary_capability: F3.3 Macro Visibility Policy
primary_failure_family: FAM-GROUND
setup_state:
  meal_result:
    canonical_commit: true
    uncertainty_level: low
    identity_confidence: high
    macro_alignment_status: pass
input: render_intake_result
expected_contract:
  show_macro_allowed: true
forbidden_outcomes: []
verification_type: deterministic
notes: 是否一定顯示可由產品策略決定，但至少允許顯示。
```

---

## MS11 — Same-Truth Read Path

### MS11-001 Later query reads corrected ledger
```yaml
case_id: MS11-001
suite_id: MS11
primary_capability: F3.4 Same-Truth Read Path
primary_failure_family: FAM-SYNC
setup_state:
  correction_applied:
    old_consumed_kcal: 1200
    new_consumed_kcal: 1270
input: "我今天目前吃了多少？"
expected_contract:
  response_consumed_kcal: 1270
  ui_consumed_kcal: 1270
  source_truth: day_budget_ledger
forbidden_outcomes:
  - response_consumed_kcal: 1200
  - ui_response_mismatch
verification_type: deterministic
notes: correction 後 query 不得讀舊值。
```

### MS11-002 Chat and UI share overshoot number
```yaml
case_id: MS11-002
suite_id: MS11
primary_capability: F3.4 Same-Truth Read Path
primary_failure_family: FAM-SYNC
setup_state:
  day_ledger:
    consumed_kcal: 2000
    target_kcal: 1800
input: "我是不是超標了？"
expected_contract:
  chat_overshoot_amount: 200
  ui_overshoot_amount: 200
  source_truth: day_budget_ledger
forbidden_outcomes:
  - chat_ui_numeric_mismatch
verification_type: deterministic
notes: same-number invariant。
```

---

## MS12 — Trace / Artifact Contract

### MS12-001 Mutating case requires request-linked trace
```yaml
case_id: MS12-001
suite_id: MS12
primary_capability: T9.1 Request / Artifact Linkage
primary_failure_family: FAM-TRACE
setup_state:
  case_type: committed_intake
input: "我吃了一顆茶葉蛋"
expected_contract:
  request_id_present: true
  trace_artifact_present: true
  state_delta_visible: true
forbidden_outcomes:
  - claim_pass_without_artifact
  - missing_request_id
verification_type: deterministic_plus_artifact
notes: no pass without evidence。
```

### MS12-002 Tavily case requires retrieval artifact
```yaml
case_id: MS12-002
suite_id: MS12
primary_capability: T9.2 State Delta Visibility
primary_failure_family: FAM-TRACE
setup_state:
  selected_evidence_path: tavily_retrieval
input: "我吃了勝王牛白湯拉麵"
expected_contract:
  retrieval_artifact_path_present: true
  selected_evidence_path_recorded: true
  normalized_evidence_packet_recorded: true
forbidden_outcomes:
  - tavily_called_without_artifact
  - final_estimate_without_evidence_record
verification_type: deterministic_plus_artifact
notes: search-related case 必須可審計。
```

### MS12-003 Manager diagnostic pass requires case-level verdicts
```yaml
case_id: MS12-003
suite_id: MS12
primary_capability: T9.1 Request / Artifact Linkage
primary_failure_family: FAM-TRACE
setup_state:
  diagnostic_run: intake_depth
input: claim_manager_diagnostic_pass
expected_contract:
  case_level_verdicts_present: true
  failed_cases_list_present_if_any: true
  artifact_paths_present: true
forbidden_outcomes:
  - summary_only_pass_claim
  - no_case_level_evidence
verification_type: deterministic_plus_artifact
notes: 防止假綠。
```

---

## MS13 — Intake Response Realization

### MS13-001 Draft response must not claim full logging
```yaml
case_id: MS13-001
suite_id: MS13
primary_capability: F2.6 Intake Response Realization
primary_failure_family: FAM-UX
setup_state:
  meal_result:
    canonical_commit: false
    clarify_mode: estimate_with_followup
input: render_response
expected_contract:
  response_may_include_range: true
  response_must_include_followup: true
  response_must_not_claim_fully_recorded: true
forbidden_outcomes:
  - "已完整記錄"
  - "已幫你記到今天總熱量"
verification_type: mixed
notes: 文字層要 obey state。
```

### MS13-002 Overshoot response must not include rescue proposal in Wave 1
```yaml
case_id: MS13-002
suite_id: MS13
primary_capability: F2.6 Intake Response Realization
primary_failure_family: FAM-RESCUE-01
setup_state:
  day_ledger:
    overshoot_amount: 200
  wave_scope: Wave 1
input: render_overshoot_response
expected_contract:
  may_display_overshoot: true
  rescue_proposal_created: false
  rescue_negotiation_started: false
forbidden_outcomes:
  - create_rescue_proposal
  - ask_to_spread_calories_across_future_days
verification_type: deterministic
notes: Wave 1 只做 overshoot awareness，不做 rescue。
```

---

# MVP Runner Recommendation

第一版 runner 可以先支援以下欄位：

```yaml
case_id:
suite_id:
input:
setup_state:
observed:
expected_contract:
forbidden_outcomes:
verdict:
failure_family_if_fail:
artifact_path:
```

## 第一批優先實作 suite

若資源有限，建議先做：

1. MS1
2. MS2
3. MS7
4. MS8
5. MS9
6. MS10
7. MS12
8. MS14

這些是 Wave 1 的 MVP Micro-Suites。

---

## 與 Manager-Style Readiness 的使用關係

### Declaring intake-entry ready
至少應通過：
- MS1
- MS7
- MS9
- MS11
- MS12
- MS14

### Declaring intake-depth ready
至少應通過：
- MS2
- MS3
- MS4
- MS5
- MS6
- MS7
- MS8
- MS9
- MS10
- MS11
- MS12
- MS13

### Declaring Wave 1 ready
應通過：
- all MVP micro-suite cases
- current Manager-style intake-entry diagnostic
- current Manager-style intake-depth diagnostic
- benchmark v1/v2 selected regression set
- turn2 replay selected regression set

---

## 歷史

- 2026-04-24: v1 初始 MVP cases，為 MS1-MS14 建立第一批可腳本驗證的 case-level contracts
