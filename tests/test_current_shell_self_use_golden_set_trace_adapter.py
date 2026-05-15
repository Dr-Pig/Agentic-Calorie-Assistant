from __future__ import annotations

from app.composition.current_shell_golden_set_trace_adapter import (
    build_golden_case_result_from_trace,
    grade_golden_case_trace,
)


def _gs5_trace_artifact() -> dict:
    return {
        "case_id": "GS5",
        "trace_id": "trace-gs5",
        "prompt_registry": {"manager_prompt_version": "v18"},
        "current_turn_context_packet": {"current_turn": "breakfast combo", "pending_question": None},
        "react_trace": {
            "manager_pass_1": {"decision_payload": {"workflow_effect": "ask_followup"}},
            "requested_tools": ["fooddb.lookup"],
            "executed_tools": ["fooddb.lookup"],
            "manager_pass_final": {"decision_payload": {"workflow_effect": "ask_followup"}},
            "guard_result": {"mutation_allowed": False},
            "total_latency_ms": 12000,
            "tool_call_count": 1,
        },
        "filtered_tool_plan": {"allowed_tools": ["fooddb.lookup"]},
        "compact_packets": [{"packet_id": "teppan-no-anchor", "posture": "ask_followup"}],
        "mutation_result": {"mutation_allowed": False},
        "renderer_input_basis": {"today_consumed_updates": False},
        "final_response_basis": {"basis": "composition_unknown"},
        "runtime": {
            "workflow_effect": "ask_followup",
            "mutation_allowed": False,
            "fallback_400_allowed": False,
            "pre_manager_estimability_shortcut_allowed": False,
            "pending_followup_saved": True,
            "assumed_slot_question_required": True,
        },
        "ui": {
            "today_consumed_updates": False,
            "pending_question_visible": True,
            "frontend_nutrition_math_allowed": False,
        },
        "response": {
            "visible_text": "我先確認套餐內容後再幫你估，這一筆還沒有記入今日熱量。",
            "zh_tw_primary": True,
            "internal_debug_words_present": False,
            "state_contradiction": False,
            "invented_nutrition_fact": False,
        },
        "latency": {"timeout_is_product_target": False, "llm_calls": 2, "tool_calls": 1},
        "dogfood_trace": {"feedback_links_to_trace": True},
        "generalization": {
            "exact_utterance_only_pass": False,
            "keyword_or_fixture_shortcut_used": False,
        },
    }


def test_trace_adapter_maps_structured_runtime_trace_to_golden_grader_input() -> None:
    result = build_golden_case_result_from_trace("GS5", _gs5_trace_artifact())

    assert result["case_id"] == "GS5"
    assert result["fixture_decisions"]["action"] is False
    assert result["trace_layers"]["manager_pass_1_decision"]["present"] is True
    assert result["trace_layers"]["manager_pass_2_synthesis"]["present"] is True
    assert result["trace_layers"]["final_response_basis"]["present"] is True
    assert result["runtime"]["workflow_effect"] == "ask_followup"
    assert result["dogfood_trace"]["trace_id"] == "trace-gs5"

    grade = grade_golden_case_trace("GS5", _gs5_trace_artifact())
    assert grade["status"] == "pass"


def test_trace_adapter_does_not_infer_runtime_outcome_from_raw_utterance() -> None:
    trace = _gs5_trace_artifact()
    trace["raw_user_input"] = "早餐吃早餐店鐵板麵套餐"
    trace.pop("runtime")

    grade = grade_golden_case_trace("GS5", trace)

    assert grade["status"] == "blocked"
    assert "runtime.workflow_effect_expected:ask_followup_actual:None" in grade["blockers"]


def test_trace_adapter_exposes_fallback_400_commit_fake_pass_to_grader() -> None:
    trace = _gs5_trace_artifact()
    trace["runtime"] = {
        "workflow_effect": "commit",
        "mutation_allowed": True,
        "fallback_400_allowed": True,
        "pending_followup_saved": False,
        "assumed_slot_question_required": False,
    }
    trace["ui"]["today_consumed_updates"] = True

    grade = grade_golden_case_trace("GS5", trace)

    assert grade["status"] == "blocked"
    assert "runtime.workflow_effect_expected:ask_followup_actual:commit" in grade["blockers"]
    assert "runtime.fallback_400_allowed_expected:False_actual:True" in grade["blockers"]


def test_trace_adapter_blocks_fixture_provider_from_counting_as_golden_set_pass() -> None:
    trace = _gs5_trace_artifact()
    trace["manager_provider"] = {
        "provider": "deterministic_self_use_manager_fixture",
        "live_llm_invoked": False,
    }

    grade = grade_golden_case_trace("GS5", trace)

    assert grade["status"] == "blocked"
    assert "fixture_decisions.intent_not_allowed" in grade["blockers"]
    assert "fixture_decisions.action_not_allowed" in grade["blockers"]
