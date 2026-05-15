from __future__ import annotations

from app.composition.current_shell_golden_set_grader import (
    grade_golden_case_result,
    load_golden_set_manifest,
)


def _base_result(case_id: str) -> dict:
    manifest = load_golden_set_manifest()
    manifest_cases = list(manifest["cases"]) + list(manifest["websearch_extension"]["cases"])
    case = next(entry for entry in manifest_cases if entry["case_id"] == case_id)
    return {
        "case_id": case_id,
        "fixture_decisions": {
            "intent": False,
            "action": False,
            "attach_target": False,
            "mutation_outcome": False,
            "response_meaning": False,
        },
        "trace_layers": {layer_id: {"present": True} for layer_id in case["required_trace_layers"]},
        "runtime": dict(case["expected_runtime"]),
        "ui": dict(case["ui_assertions"]),
        "response": {
            "assistant_message": "已處理。",
            "zh_tw_primary": True,
            "internal_debug_words_present": False,
            "state_contradiction": False,
            "invented_nutrition_fact": False,
            "naturalness_judge_status": "diagnostic_not_blocking",
        },
        "latency": {
            "timeout_is_product_target": False,
            "llm_calls": case["latency_call_budget"]["max_llm_calls"],
            "tool_calls": case["latency_call_budget"]["max_tool_calls"],
        },
        "dogfood_trace": {
            "trace_id": f"trace-{case_id}",
            "feedback_links_to_trace": True,
            "correlates_ui_runtime_read_model_response": case["dogfood_trace"].get(
                "correlates_ui_runtime_read_model_response", False
            ),
        },
        "generalization": {
            "exact_utterance_only_pass": False,
            "keyword_or_fixture_shortcut_used": False,
        },
    }


def test_grader_passes_a_valid_gs5_no_anchor_followup_result() -> None:
    result = _base_result("GS5")

    grade = grade_golden_case_result(result)

    assert grade["status"] == "pass"
    assert grade["blockers"] == []
    assert grade["case_id"] == "GS5"


def test_grader_passes_a_valid_websearch_extension_candidate_result() -> None:
    result = _base_result("GSW1")

    grade = grade_golden_case_result(result)

    assert grade["status"] == "pass"
    assert grade["blockers"] == []
    assert grade["case_id"] == "GSW1"


def test_grader_blocks_websearch_candidate_truth_promotion() -> None:
    result = _base_result("GSW1")
    result["runtime"]["websearch_snippet_as_truth_allowed"] = True
    result["runtime"]["runtime_mutation_allowed"] = True
    result["runtime"]["websearch_candidate_to_commit_allowed"] = True
    result["ui"]["today_consumed_updates"] = True

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert (
        "runtime.websearch_snippet_as_truth_allowed_expected:False_actual:True"
        in grade["blockers"]
    )
    assert "runtime.runtime_mutation_allowed_expected:False_actual:True" in grade["blockers"]
    assert "runtime.websearch_candidate_to_commit_allowed_expected:False_actual:True" in grade["blockers"]
    assert "ui.today_consumed_updates_expected:False_actual:True" in grade["blockers"]


def test_grader_blocks_websearch_keyword_router_fake_pass() -> None:
    result = _base_result("GSW1")
    result["runtime"]["pre_manager_websearch_routing_allowed"] = True
    result["generalization"]["pre_manager_websearch_routing_used"] = True
    result["generalization"]["case_id_or_fixture_label_routing_used"] = True

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert "runtime.pre_manager_websearch_routing_allowed_expected:False_actual:True" in grade["blockers"]
    assert "generalization.pre_manager_websearch_routing_used" in grade["blockers"]
    assert "generalization.case_id_or_fixture_label_routing_used" in grade["blockers"]


def test_grader_blocks_wrong_brand_exact_or_macro_promotion() -> None:
    result = _base_result("GSW2")
    result["runtime"]["wrong_brand_promotion_allowed"] = True
    result["runtime"]["exact_promotion_allowed"] = True
    result["runtime"]["macro_truth_allowed"] = True

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert "runtime.wrong_brand_promotion_allowed_expected:False_actual:True" in grade["blockers"]
    assert "runtime.exact_promotion_allowed_expected:False_actual:True" in grade["blockers"]
    assert "runtime.macro_truth_allowed_expected:False_actual:True" in grade["blockers"]


def test_grader_blocks_websearch_when_fooddb_anchor_exists() -> None:
    result = _base_result("GSW3")
    result["runtime"]["websearch_tool_call_expected"] = True
    result["runtime"]["fooddb_anchor_bypass_allowed"] = True

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert "runtime.websearch_tool_call_expected_expected:False_actual:True" in grade["blockers"]
    assert "runtime.fooddb_anchor_bypass_allowed_expected:False_actual:True" in grade["blockers"]


def test_grader_blocks_candidate_only_macro_visibility() -> None:
    result = _base_result("GSW4")
    result["runtime"]["websearch_candidate_to_macro_truth_allowed"] = True
    result["ui"]["macro_hidden_when_candidate_only"] = False

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert (
        "runtime.websearch_candidate_to_macro_truth_allowed_expected:False_actual:True"
        in grade["blockers"]
    )
    assert "ui.macro_hidden_when_candidate_only_expected:True_actual:False" in grade["blockers"]


def test_grader_treats_canonical_write_commit_as_gs1_commit_effect() -> None:
    result = _base_result("GS1")
    result["runtime"]["workflow_effect"] = "canonical_write"
    result["runtime"]["canonical_commit_status"] = "committed"
    result["runtime"]["final_action"] = "commit"
    result["response"]["assistant_message"] = "已記錄這餐。"

    grade = grade_golden_case_result(result)

    assert grade["status"] == "pass"
    assert grade["blockers"] == []


def test_grader_accepts_structured_pending_teppan_combo_attachment() -> None:
    result = _base_result("GS10")
    result["runtime"]["workflow_effect"] = "canonical_write"
    result["runtime"]["canonical_commit_status"] = "committed"
    result["runtime"]["final_action"] = "commit"
    result["runtime"]["target_attachment"] = {
        "operation": "attach_to_pending_followup",
        "target_resolution_source": "pending_followup_state",
    }

    grade = grade_golden_case_result(result)

    assert grade["status"] == "pass"
    assert grade["blockers"] == []


def test_grader_accepts_structured_previous_teppan_meal_attachment() -> None:
    result = _base_result("GS11")
    result["runtime"]["workflow_effect"] = "correction_applied"
    result["runtime"]["canonical_commit_status"] = "committed"
    result["runtime"]["final_action"] = "correction_applied"
    result["runtime"]["target_attachment"] = {
        "meal_thread_id": 1,
        "meal_version_id": 1,
        "target_resolution_source": "tool_result_validated",
        "correction_confidence": "medium",
    }

    grade = grade_golden_case_result(result)

    assert grade["status"] == "pass"
    assert grade["blockers"] == []


def test_grader_accepts_structured_whole_meal_removal_attachment() -> None:
    result = _base_result("GS12")
    result["runtime"]["workflow_effect"] = "correction_applied"
    result["runtime"]["canonical_commit_status"] = "committed"
    result["runtime"]["final_action"] = "correction_applied"
    result["runtime"]["old_version_superseded"] = True
    result["runtime"]["removed_versions_excluded_from_ledger"] = True
    result["runtime"]["target_attachment"] = {
        "meal_thread_id": 3,
        "operation": "remove_meal",
        "target_resolution_source": "resolve_correction_target",
    }

    grade = grade_golden_case_result(result)

    assert grade["status"] == "pass"
    assert grade["blockers"] == []


def test_grader_blocks_fixture_owned_semantics() -> None:
    result = _base_result("GS5")
    result["fixture_decisions"]["action"] = True

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert "fixture_decisions.action_not_allowed" in grade["blockers"]


def test_grader_blocks_teppan_fallback_400_commit_fake_pass() -> None:
    result = _base_result("GS5")
    result["runtime"]["workflow_effect"] = "commit"
    result["runtime"]["mutation_allowed"] = True
    result["runtime"]["fallback_400_allowed"] = True
    result["runtime"]["pending_followup_saved"] = False
    result["ui"]["today_consumed_updates"] = True

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert "runtime.workflow_effect_expected:ask_followup_actual:commit" in grade["blockers"]
    assert "runtime.mutation_allowed_expected:False_actual:True" in grade["blockers"]
    assert "runtime.fallback_400_allowed_expected:False_actual:True" in grade["blockers"]
    assert "ui.today_consumed_updates_expected:False_actual:True" in grade["blockers"]


def test_grader_blocks_missing_blocking_trace_layer() -> None:
    result = _base_result("GS9")
    result["trace_layers"].pop("manager_pass_1_decision")

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert "trace_layers.manager_pass_1_decision_missing" in grade["blockers"]


def test_grader_blocks_response_state_and_internal_debug_leak() -> None:
    result = _base_result("GS9")
    result["response"]["internal_debug_words_present"] = True
    result["response"]["state_contradiction"] = True

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert "response.internal_debug_words_present" in grade["blockers"]
    assert "response.state_contradiction" in grade["blockers"]


def test_grader_blocks_missing_trace_id_and_call_budget_overrun() -> None:
    result = _base_result("GS14")
    result["dogfood_trace"]["trace_id"] = ""
    result["latency"]["llm_calls"] = 3

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert "dogfood_trace.trace_id_missing" in grade["blockers"]
    assert "latency.llm_calls_exceeds_budget:3>1" in grade["blockers"]


def test_grader_blocks_exact_utterance_or_keyword_shortcut_pass() -> None:
    result = _base_result("GS5")
    result["generalization"]["exact_utterance_only_pass"] = True
    result["generalization"]["keyword_or_fixture_shortcut_used"] = True

    grade = grade_golden_case_result(result)

    assert grade["status"] == "blocked"
    assert "generalization.exact_utterance_only_pass" in grade["blockers"]
    assert "generalization.keyword_or_fixture_shortcut_used" in grade["blockers"]
