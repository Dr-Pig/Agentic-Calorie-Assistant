# L5D Suite Migration Mapping Table V1

本表把現有 benchmark / tests / runners 映射到 `L5D` suite taxonomy。

## 1. Benchmarks / Packs / Registries

| existing_asset | asset_type | mapped_suite_id | authority_tier | migration_status | notes |
| --- | --- | --- | --- | --- | --- |
| `docs/quality/benchmarks/founder_fit_golden_v1.json` | `benchmark_fixture` | `intake_founder_fit_primary_golden_v1` | `Official Golden` | `mapped_existing` | 既有 founder-fit 黃金集，屬 intake 主線 |
| `docs/quality/benchmarks/intake/multi_turn/turn2_hybrid_replay_pack_v1.json` | `benchmark_fixture` | `intake_turn2_hybrid_replay_golden_v1` | `Official Golden` | `mapped_existing` | turn-2 replay 官方主線 |
| `docs/quality/benchmarks/intake/multi_turn/*` | `stateful_multi_turn_case_dir` | `intake_turn2_hybrid_replay_golden_v1` | `Official Golden` | `mapped_existing` | 既有 turn-2 case dirs 與 state delta files |
| `docs/quality/benchmarks/semantic_routing/semantic_routing_founder_fit_pack_v1.json` | `benchmark_fixture` | `semantic_routing_provisional_smoke_v1` | `Provisional Exploratory` | `mapped_existing` | 已明確降級為 provisional / non-canonical |
| `docs/quality/benchmarks/semantic_routing/semantic_routing_official_canonical_pack_v1.json` | `benchmark_fixture` | `semantic_routing_official_canonical_v1` | `Official Golden` | `mapped_existing` | 官方 lane，但目前 case 仍極少 / 待 promotion |
| `docs/quality/benchmarks/semantic_routing/semantic_routing_candidate_review_queue_v1.json` | `candidate_queue` | `semantic_routing_candidate_queue_v1` | `Provisional Exploratory` | `mapped_existing` | candidate-only，不屬 oracle truth |
| `docs/quality/benchmarks/intake/intake_candidate_review_queue_v1.json` | `candidate_queue` | `intake_task_meal_link_golden_v1` | `Official Golden` | `mapped_existing` | intake 官方候選入口，逐題 promotion 到對應 suite |
| `docs/quality/benchmarks/general_chat/general_chat_candidate_review_queue_v1.json` | `candidate_queue` | `general_chat_budget_query_golden_v1` | `Official Golden` | `mapped_existing` | general_chat 官方候選入口，逐題 promotion 到 budget/goal/open-workflow suites |
| `docs/quality/benchmarks/rescue/rescue_candidate_review_queue_v1.json` | `candidate_queue` | `rescue_accept_action_golden_v1` | `Official Golden` | `mapped_existing` | rescue 官方候選入口，逐題 promotion 到對應 suite |
| `docs/quality/benchmarks/intake/intake_official_canonical_pack_v1.json` | `benchmark_fixture` | `intake_official_canonical_pack_v1` | `Official Golden` | `mapped_existing` | intake 第一批已核准 official canonical pack |
| `docs/quality/benchmarks/general_chat/general_chat_official_canonical_pack_v1.json` | `benchmark_fixture` | `general_chat_official_canonical_pack_v1` | `Official Golden` | `mapped_existing` | general_chat 第一批已核准 official canonical pack，覆蓋 budget/goal/open-workflow boundary |
| `docs/quality/benchmarks/rescue/rescue_official_canonical_pack_v1.json` | `benchmark_fixture` | `rescue_official_canonical_pack_v1` | `Official Golden` | `mapped_existing` | rescue 第一批已核准 official canonical pack |
| `docs/quality/benchmarks/intake/intake_executable_action_pack_v1.json` | `derived_executable_pack` | `intake_official_canonical_pack_v1` | `Official Golden` | `mapped_existing` | subordinate executable contract，不是新的 suite authority source |
| `docs/quality/benchmarks/rescue/rescue_executable_action_pack_v1.json` | `derived_executable_pack` | `rescue_official_canonical_pack_v1` | `Official Golden` | `mapped_existing` | subordinate executable contract；rescue adjust direction 已明確映射到 runtime action |
| `scripts/run_rescue_executable_pack.py` | `runner` | `rescue_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | derived executable runner，直接消費 rescue executable action pack |
| `scripts/run_intake_executable_pack.py` | `runner` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | derived executable runner，直接消費 intake executable action pack |
| `scripts/run_general_chat_official_pack.py` | `runner` | `general_chat_budget_query_golden_v1` | `Official Golden` | `mapped_existing` | general_chat official canonical runner，直接執行 budget/goal/open-workflow pack |
| `docs/quality/benchmarks/retrieval/retrieval_candidate_selection_golden_v1.json` | `benchmark_fixture` | `retrieval_candidate_selection_golden_v1` | `Official Golden` | `mapped_existing` | agent-governed capability/service suite，直接由 canonical spec 與現有 retrieval tests 派生 |
| `docs/quality/benchmarks/context/context_packing_sufficiency_golden_v1.json` | `benchmark_fixture` | `context_packing_sufficiency_golden_v1` | `Official Golden` | `mapped_existing` | agent-governed capability/service suite，覆蓋 context packing sufficiency |
| `docs/quality/benchmarks/fallback/bounded_repair_gate_golden_v1.json` | `benchmark_fixture` | `bounded_repair_gate_golden_v1` | `Official Golden` | `mapped_existing` | agent-governed degraded/fallback suite，覆蓋 bounded repair 與 gate immutability |
| `docs/quality/INTAKE_OFFICIAL_GOLDEN_BATCH_REVIEW_V1.md` | `batch_review_sheet` | `intake_task_meal_link_golden_v1` | `Official Golden` | `mapped_existing` | intake 批次審核表面，實際覆蓋多個 intake suites |
| `docs/quality/GENERAL_CHAT_OFFICIAL_GOLDEN_BATCH_REVIEW_V1.md` | `batch_review_sheet` | `general_chat_budget_query_golden_v1` | `Official Golden` | `mapped_existing` | general_chat 批次審核表面，實際覆蓋 budget/goal/open-workflow suites |
| `docs/quality/RESCUE_OFFICIAL_GOLDEN_BATCH_REVIEW_V1.md` | `batch_review_sheet` | `rescue_accept_action_golden_v1` | `Official Golden` | `mapped_existing` | rescue 批次審核表面，實際覆蓋多個 rescue suites |
| `docs/quality/benchmarks/templates/candidate_review_queue_template.json` | `template` | `none` | `Smoke / Infra` | `mapped_existing` | utterance-governed candidate queue scaffold |
| `docs/quality/benchmarks/templates/official_canonical_pack_template.json` | `template` | `none` | `Smoke / Infra` | `mapped_existing` | official canonical pack scaffold |
| `docs/quality/benchmarks/templates/executable_action_pack_template.json` | `template` | `none` | `Smoke / Infra` | `mapped_existing` | derived executable pack scaffold |
| `scripts/create_benchmark_artifact.py` | `authoring_helper` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | batch artifact scaffolding helper，不提供 canonical truth |
| `docs/quality/AUDIT_RUNNER_REGISTRY.json` | `runner_registry` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | 已補 suite-governance metadata，後續只需隨新增 suite 擴展 |
| `docs/quality/AUDIT_FIXTURE_REGISTRY.json` | `fixture_registry` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | 已補 suite-governance metadata，後續只需隨新增 suite 擴展 |
| `scripts/run_founder_golden_audit.py` | `runner` | `intake_founder_fit_primary_golden_v1` | `Official Golden` | `mapped_existing` | 既有 founder golden runner |
| `scripts/run_turn2_hybrid_replay.py` | `runner` | `intake_turn2_hybrid_replay_golden_v1` | `Official Golden` | `mapped_existing` | 既有 turn-2 runner |
| `scripts/run_semantic_routing_eval.py` | `runner` | `semantic_routing_provisional_smoke_v1` | `Provisional Exploratory` | `mapped_existing` | 目前支援 provisional 與 official 兩 lane |

## 2. Tests

| existing_asset | asset_type | mapped_suite_id | authority_tier | migration_status | notes |
| --- | --- | --- | --- | --- | --- |
| `tests/test_text_meal.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | intake runtime broad regression |
| `tests/test_base_nutrition_integration.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | intake nutrition integration |
| `tests/test_base_nutrition_wide_research.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | nutrition estimation smoke |
| `tests/test_base_nutrition_wide_research_v2_1.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | nutrition estimation smoke |
| `tests/test_base_nutrition_wide_research_v2_2.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | nutrition estimation smoke |
| `tests/test_common_dish_priors.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | intake estimation priors |
| `tests/test_exact_item_wide_research_v3.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | exact-item estimation smoke |
| `tests/test_macro.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | nutrition / macro derivation |
| `tests/test_nutrition_contract_benchmark.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | contract-focused benchmark smoke |
| `tests/test_nutrition_repair_policy.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | repair policy smoke |
| `tests/test_post_pass_override_guards.py` | `test_file` | `intake_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | pass guard smoke |
| `tests/test_followup_closure_validation.py` | `test_file` | `intake_turn2_hybrid_replay_golden_v1` | `Official Golden` | `mapped_existing` | follow-up closure validation ties to turn-2 |
| `tests/test_turn2_hybrid_replay_foundation.py` | `test_file` | `intake_turn2_hybrid_replay_golden_v1` | `Official Golden` | `mapped_existing` | turn-2 replay runner foundation |
| `tests/test_text_meal_trace_eval.py` | `test_file` | `trace_contract_smoke_v1` | `Smoke / Infra` | `mapped_existing` | intake trace/eval plumbing |
| `tests/test_benchmark_handoff.py` | `test_file` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | benchmark handoff plumbing |
| `tests/test_benchmark_v1_fixture.py` | `test_file` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | fixture loading / schema smoke |
| `tests/test_eval_runner.py` | `test_file` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | runner smoke |
| `tests/test_pass_runner_and_invariants.py` | `test_file` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | pass-runner invariants |
| `tests/test_planner_loop_runner.py` | `test_file` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | planner loop runner smoke |
| `tests/test_real_world_regression_fixture.py` | `test_file` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | regression fixture smoke |
| `tests/test_run_real_world_regression.py` | `test_file` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | regression runner smoke |
| `tests/test_rescue_chat_surface.py` | `test_file` | `rescue_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | rescue chat surface |
| `tests/test_rescue_overlay.py` | `test_file` | `rescue_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | rescue overlay writeback |
| `tests/test_rescue_proposal.py` | `test_file` | `rescue_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | rescue proposal mechanics |
| `tests/test_rescue_response.py` | `test_file` | `rescue_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | rescue response contract smoke |
| `tests/test_rescue_routes.py` | `test_file` | `rescue_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | rescue web routes |
| `tests/test_rescue_runtime.py` | `test_file` | `rescue_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | rescue runtime smoke |
| `tests/test_open_proposals_read_model.py` | `test_file` | `rescue_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | proposal read side backing rescue |
| `tests/test_calibration_benchmark_fixture.py` | `test_file` | `calibration_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | calibration fixture smoke |
| `tests/test_calibration_model.py` | `test_file` | `calibration_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | calibration model smoke |
| `tests/test_calibration_proposal_gate.py` | `test_file` | `calibration_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | calibration proposal gate |
| `tests/test_body_observation_persistence.py` | `test_file` | `calibration_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | body observation persistence under calibration-adjacent lane |
| `tests/test_context_memory_contract.py` | `test_file` | `trace_contract_smoke_v1` | `Smoke / Infra` | `mapped_existing` | memory/context contract |
| `tests/test_knowledge_packets.py` | `test_file` | `trace_contract_smoke_v1` | `Smoke / Infra` | `mapped_existing` | knowledge/context packet smoke |
| `tests/test_trace_observability_contract.py` | `test_file` | `trace_contract_smoke_v1` | `Smoke / Infra` | `mapped_existing` | trace observability |
| `tests/test_trace_triage.py` | `test_file` | `trace_contract_smoke_v1` | `Smoke / Infra` | `mapped_existing` | trace triage contract |
| `tests/test_current_budget_read_model.py` | `test_file` | `trace_contract_smoke_v1` | `Smoke / Infra` | `mapped_existing` | current budget read-side contract |
| `tests/test_general_chat_workflow.py` | `test_file` | `general_chat_budget_query_golden_v1` | `Official Golden` | `mapped_existing` | general_chat budget/goal/open-workflow contract smoke |
| `tests/test_routes_today_ui.py` | `test_file` | `trace_contract_smoke_v1` | `Smoke / Infra` | `mapped_existing` | read-model/UI smoke |
| `tests/test_routes_weight_ui.py` | `test_file` | `trace_contract_smoke_v1` | `Smoke / Infra` | `mapped_existing` | read-model/UI smoke |
| `tests/test_retrieval_external_search.py` | `test_file` | `retrieval_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | retrieval integration smoke |
| `tests/test_retrieval_external_search_benchmark.py` | `test_file` | `retrieval_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | retrieval benchmark smoke |
| `tests/test_search_ranking.py` | `test_file` | `retrieval_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | retrieval ranking |
| `tests/test_import_external_workspace_candidates.py` | `test_file` | `retrieval_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | external candidate import |
| `tests/test_source_registry_wide_research.py` | `test_file` | `retrieval_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | source registry / retrieval support |
| `tests/test_build_tfda_base_from_candidates.py` | `test_file` | `retrieval_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | retrieval-backed source assembly |
| `tests/test_builderspace_adapter.py` | `test_file` | `retrieval_runtime_smoke_v1` | `Smoke / Infra` | `mapped_existing` | adapter smoke |
| `tests/chain_conv_cases.json` | `test_data` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | chain conversation fixture |
| `tests/diagnostic_cases.json` | `test_data` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | diagnostic fixture |
| `tests/readiness_audit_cases.json` | `test_data` | `benchmark_harness_smoke_v1` | `Smoke / Infra` | `mapped_existing` | readiness audit fixture |
| `tests/test_semantic_routing_eval_foundation.py` | `test_file` | `semantic_routing_provisional_smoke_v1` | `Provisional Exploratory` | `mapped_existing` | validates current provisional/official semantic-routing lanes |
| `tests/test_official_text_surface_mojibake_guard.py` | `test_file` | `quality_guard_smoke_v1` | `Smoke / Infra` | `mapped_existing` | official text-surface guard |
| `tests/test_user_facing_mojibake_guard.py` | `test_file` | `quality_guard_smoke_v1` | `Smoke / Infra` | `mapped_existing` | user-facing guard |
| `tests/test_risk_gate.py` | `test_file` | `quality_guard_smoke_v1` | `Smoke / Infra` | `mapped_existing` | risk/safety gate smoke |
| `tests/test_target_calculation.py` | `test_file` | `quality_guard_smoke_v1` | `Smoke / Infra` | `mapped_existing` | target calculation / deterministic guard |
| `tests/test_canonical_persistence.py` | `test_file` | `quality_guard_smoke_v1` | `Smoke / Infra` | `mapped_existing` | canonical persistence contract |

## 3. Migration Rules

- `mapped_existing`
  - 現有資產可直接對應到某個 suite
- `registry_extension_needed`
  - 現有 registry 還需要增加 suite metadata 欄位
- `planned_split`
  - 現有資產之後應拆到更細 suite，但目前先維持單一映射

這張表的角色是**先消除 orphan assets**，不是一次完成所有細緻切分。
