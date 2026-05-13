from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_context_engineering_pr_train.yaml"
)
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"


def _plan() -> dict:
    return yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8-sig"))


def test_context_engineering_train_records_twenty_nine_right_sized_prs() -> None:
    plan = _plan()

    assert plan["artifact_type"] == "advanced_product_lab_context_engineering_pr_train"
    assert plan["status"] == "complete"
    assert plan["planned_pr_count"] == 29
    assert plan["dynamic_remaining_pr_count"] == 0
    assert plan["last_completed_pr_number"] == 29
    assert plan["active_pr_number"] is None

    prs = plan["pr_train"]
    assert len(prs) == 29
    assert [item["pr_number"] for item in prs] == list(range(1, 30))
    assert prs[0]["slice_id"] == "context_engineering_bootstrap_and_train_alignment"
    assert prs[-1]["slice_id"] == "recommendation_entry_contract_and_next_train_closeout"
    assert len({item["slice_id"] for item in prs}) == 29


def test_context_engineering_train_keeps_only_two_stable_repo_branches() -> None:
    plan = _plan()
    strategy = plan["branch_strategy"]

    assert strategy["target_branch"] == "codex/advanced-product-lab"
    assert strategy["stable_repo_branches"] == ["main", "codex/advanced-product-lab"]
    assert strategy["additional_long_lived_branches_allowed"] is False
    assert strategy["short_lived_pr_branches_required"] is False
    assert strategy["logical_pr_slices_run_on_same_branch"] is True
    assert strategy["mainline_activation_enabled"] is False
    assert strategy["self_use_v1_affected"] is False


def test_context_engineering_train_keeps_lab_and_mainline_activation_separate() -> None:
    plan = _plan()
    required_flags = plan["required_artifact_flags"]

    assert required_flags["lab_enabled"] is True
    assert required_flags["lab_isolated"] is True
    assert required_flags["mainline_activation_enabled"] is False
    assert required_flags["mainline_runtime_connected"] is False
    assert required_flags["production_scheduler_delivery_allowed"] is False
    assert required_flags["canonical_product_mutation_allowed"] is False
    assert required_flags["manager_context_packet_changed"] is False


def test_context_engineering_train_covers_shared_manager_and_reusable_meal_requirements() -> None:
    plan = _plan()
    clauses = {
        item["coverage_id"]: item for item in plan["spec_coverage_matrix"]["required_clauses"]
    }

    assert clauses["one_manager_style_runtime_contract"]["first_pr"] == 2
    assert clauses["multi_intent_context_engineering_golden_set"]["first_pr"] == 5
    assert clauses["memory_and_rescue_on_shared_turn_plan"]["first_pr"] == 19
    assert clauses["reusable_meal_entity_not_memory_only"]["first_pr"] == 21
    assert clauses["recommendation_entry_after_shared_planner"]["first_pr"] == 29


def test_context_engineering_train_declares_dynamic_estimate_protocol() -> None:
    plan = _plan()
    protocol = plan["dynamic_estimate_protocol"]

    assert protocol["update_after_each_merge"] is True
    assert protocol["report_in_chat_after_each_completed_pr"] is True
    assert protocol["estimate_may_increase"] is True
    assert protocol["estimate_may_decrease"] is True
    assert (
        "docs/quality/advanced_product_lab_context_engineering_pr_train.yaml"
        in protocol["persistent_truth_files"]
    )


def test_context_engineering_train_records_local_slice_progress() -> None:
    plan = _plan()

    completed = plan["last_merge_evidence"]["completed_prs"]
    assert [item["pr_number"] for item in completed] == list(range(1, 30))
    assert completed[0]["result"] == (
        "context_engineering_bootstrap_and_train_alignment_completed_locally"
    )
    assert completed[1]["result"] == (
        "shared_manager_style_convergence_contract_completed_locally"
    )
    assert completed[2]["result"] == (
        "shared_capability_registry_contract_completed_locally"
    )
    assert completed[3]["result"] == "manager_turn_plan_schema_completed_locally"
    assert completed[4]["result"] == (
        "multi_intent_golden_set_schema_and_loader_completed_locally"
    )
    assert completed[5]["result"] == (
        "current_shell_and_advanced_lab_overlap_case_pack_completed_locally"
    )
    assert completed[6]["result"] == (
        "ambiguity_holdout_and_adversarial_case_pack_completed_locally"
    )
    assert completed[7]["result"] == (
        "trace_grader_and_omission_rubric_completed_locally"
    )
    assert completed[8]["result"] == (
        "bounded_react_loop_state_contract_completed_locally"
    )
    assert completed[9]["result"] == (
        "tool_choice_ordering_and_argument_walls_completed_locally"
    )
    assert completed[10]["result"] == "context_pack_assembler_base_completed_locally"
    assert completed[11]["result"] == "memory_context_pack_adapter_completed_locally"
    assert completed[12]["result"] == "rescue_context_pack_adapter_completed_locally"
    assert completed[13]["result"] == "current_shell_runtime_bridge_contract_completed_locally"
    assert completed[14]["result"] == "advanced_lab_runtime_bridge_contract_completed_locally"
    assert completed[15]["result"] == "manager_tool_result_envelope_normalization_completed_locally"
    assert completed[16]["result"] == "final_response_plan_and_capability_signal_packet_completed_locally"
    assert completed[17]["result"] == "direct_bypass_to_manager_path_convergence_completed_locally"
    assert completed[18]["result"] == "memory_run_on_shared_turn_plan_completed_locally"
    assert completed[19]["result"] == "rescue_run_on_shared_turn_plan_completed_locally"
    assert completed[20]["result"] == "reusable_meal_entity_contract_completed_locally"
    assert completed[21]["result"] == "reusable_meal_promotion_and_drift_policy_completed_locally"
    assert completed[22]["result"] == "reusable_meal_golden_set_and_holdouts_completed_locally"
    assert completed[23]["result"] == "reusable_meal_memory_hint_bridge_completed_locally"
    assert completed[24]["result"] == "reusable_meal_intake_shadow_retrieval_completed_locally"
    assert completed[25]["result"] == (
        "integrated_memory_rescue_reusable_meal_fixture_e2e_completed_locally"
    )
    assert completed[26]["result"] == "grokfast_manager_turn_live_diagnostic_completed_locally"
    assert completed[26]["live_artifact"].endswith(
        "advanced_product_lab_manager_turn_grokfast_diagnostic_pr27_live.json"
    )
    assert completed[27]["result"] == (
        "context_engineering_shadow_comparison_and_decision_pack_completed_locally"
    )
    assert completed[27]["decision_pack_artifact"].endswith(
        "advanced_product_lab_context_engineering_decision_pack_pr28.json"
    )
    assert completed[28]["result"] == (
        "recommendation_entry_contract_and_next_train_closeout_completed_locally"
    )
    assert completed[28]["entry_contract_artifact"].endswith(
        "advanced_product_lab_recommendation_entry_contract_pr29.json"
    )
    assert completed[28]["next_train"].endswith(
        "advanced_product_lab_recommendation_pr_train.yaml"
    )


def test_context_engineering_train_is_indexed_without_becoming_bootstrap_truth() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")

    assert "advanced_product_lab_context_engineering_pr_train.yaml" in doc_index
    assert "advanced_product_lab_recommendation_pr_train.yaml" in doc_index
    assert "context engineering train" in doc_index
    assert "advanced_product_lab_context_engineering_pr_train.yaml" not in doc_index[
        doc_index.index("## Active Bootstrap") : doc_index.index("## Active Truth Rules")
    ]
