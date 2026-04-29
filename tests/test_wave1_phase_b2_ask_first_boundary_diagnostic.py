from __future__ import annotations

import json
from pathlib import Path

from scripts.build_wave1_phase_b2_evidence_synthesis_smoke import build_phase_b2_synthetic_smoke_report
from scripts.diagnose_b1_b2_ask_first_boundary import diagnose_b1_b2_ask_first_boundary
from scripts.live_diagnostic_decision_pack import build_b2_live_llm_diagnostic_contract_report


def _b1_green_handoff_snapshot() -> dict[str, object]:
    return {
        "b1_gate_scope": "Phase B-1 minimal tool-loop full natural-probe",
        "smoke_artifact": "artifacts/phase_b1_full_smoke.json",
        "readiness_artifact": "artifacts/phase_b1_readiness.json",
        "ready_for_phase_b1_implementation": True,
        "blockers": [],
        "not_claiming": "whole Wave 1 completion",
    }


def _phase_b2_report() -> dict[str, object]:
    return build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())


def _case_by_id(report: dict[str, object], case_id: str) -> dict[str, object]:
    return next(case for case in report["cases"] if case["case_id"] == case_id)


def _phase_b_report(*, bad_lookup: bool = False) -> dict[str, object]:
    requested_tools = ["lookup_generic_food"] if bad_lookup else []
    return {
        "phase": "B1",
        "tool_loop_traces": [
            {
                "case_id": "B1-004",
                "input_message": "我吃了滷味",
                "semantic_boundary": "self_selected_basket_without_ingredients",
                "manager_pass_1": {
                    "decision_payload": {
                        "manager_action": "call_tools" if bad_lookup else "final",
                        "final_action": None if bad_lookup else "request_clarification",
                        "response_mode": "clarification",
                        "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": "滷味"}}]
                        if bad_lookup
                        else [],
                    },
                    "requested_read_tools": requested_tools,
                },
                "runtime_tool_router": {
                    "requested_read_tools": requested_tools,
                    "allowed_tools": [] if bad_lookup else [],
                    "blocked_tools": ["lookup_generic_food", "retrieve_web_food_evidence"],
                    "block_reasons": [
                        {
                            "rule": "self_selected_basket_without_ingredients_blocks_estimate_tools",
                            "detail": "Composition is unknown; ask for ingredients before estimate.",
                        }
                    ],
                },
                "manager_pass_2": {"item_results": []},
                "mutation": {"mutation_attempted": False, "reason": "no_mutation_intent", "mutation_result": None},
            }
        ],
    }


def _register_text(extra: str = "") -> str:
    return (
        "approved:\n"
        "  pearl_milk_tea_missing_sugar_size:\n"
        "    status: approved\n"
        "pending:\n"
        "  homemade_dish_minimum_estimability:\n"
        "    status: pending\n"
        f"{extra}"
    )


def _live_report_with_unknown_estimate(phase_b2_report: dict[str, object]) -> dict[str, object]:
    return build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=phase_b2_report,
        provider_outputs_by_case_id={
            "B2-004": {
                "item_results": [
                    {
                        "interpreted_food_identity": "滷味",
                        "exactness_posture": "estimated",
                        "likely_kcal": 520,
                        "kcal_range": [350, 700],
                        "evidence_used": [],
                    }
                ]
            }
        },
    )


def _approved_register_text() -> str:
    return _register_text(
        "  self_selected_basket_without_listed_items:\n"
        "    status: approved\n"
        "    selected_policy: ask_first_unresolved_no_logged_estimate\n"
    )


def test_diagnostic_reports_missing_policy_as_contributing_after_payload_alignment() -> None:
    phase_b2 = _phase_b2_report()
    report = diagnose_b1_b2_ask_first_boundary(
        phase_b_report=_phase_b_report(),
        phase_b2_report=phase_b2,
        live_report=_live_report_with_unknown_estimate(phase_b2),
        semantic_register_text=_register_text(),
    )

    assert report["case_id"] == "B2-004"
    assert report["primary_root_cause"] == "none"
    assert "semantic_register_policy_missing" in report["contributing_factors"]
    assert report["semantic_policy"] == {
        "decision_id": "self_selected_basket_without_listed_items",
        "status": "missing",
        "selected_policy": None,
    }
    assert report["phase_a_b1"]["status"] == "pass"
    assert report["b2_source_selection"]["status"] == "pass"
    assert report["b2_packet_gate"]["status"] == "pass"
    assert report["live_payload"]["status"] == "pass"
    assert report["validator"]["actual_verdict"] == "product_decision_required"
    assert report["validator"]["expected_verdict"] == "product_decision_required"


def test_diagnostic_flags_phase_a_gap_when_b1_requests_lookup_for_bare_luwei() -> None:
    phase_b2 = _phase_b2_report()
    report = diagnose_b1_b2_ask_first_boundary(
        phase_b_report=_phase_b_report(bad_lookup=True),
        phase_b2_report=phase_b2,
        live_report=_live_report_with_unknown_estimate(phase_b2),
        semantic_register_text=_register_text(),
    )

    assert report["primary_root_cause"] == "phase_a_gap"
    assert report["phase_a_b1"]["status"] == "gap"
    assert "lookup_generic_food" in report["phase_a_b1"]["requested_read_tools"]


def test_diagnostic_flags_b2_source_selection_gap() -> None:
    phase_b2 = _phase_b2_report()
    b2_case = _case_by_id(phase_b2, "B2-004")
    b2_case["source_selection"]["source_path"] = "generic_anchor"
    b2_case["source_selection"]["evidence_required"] = "generic_anchor_packet"

    report = diagnose_b1_b2_ask_first_boundary(
        phase_b_report=_phase_b_report(),
        phase_b2_report=phase_b2,
        live_report=_live_report_with_unknown_estimate(phase_b2),
        semantic_register_text=_register_text(),
    )

    assert report["primary_root_cause"] == "b2_source_selection_gap"
    assert report["b2_source_selection"]["status"] == "gap"


def test_diagnostic_flags_b2_packet_gate_gap_when_deterministic_artifact_estimates_luwei() -> None:
    phase_b2 = _phase_b2_report()
    item = _case_by_id(phase_b2, "B2-004")["manager_pass_2"]["item_results"][0]
    item["likely_kcal"] = 520
    item["kcal_range"] = [350, 700]
    item["evidence_used"] = [{"packet_id": "pkt_skill_luwei"}]

    report = diagnose_b1_b2_ask_first_boundary(
        phase_b_report=_phase_b_report(),
        phase_b2_report=phase_b2,
        live_report=_live_report_with_unknown_estimate(phase_b2),
        semantic_register_text=_register_text(),
    )

    assert report["primary_root_cause"] == "b2_packet_gate_gap"
    assert report["b2_packet_gate"]["status"] == "gap"


def test_diagnostic_approved_policy_changes_validator_expectation_to_blocker() -> None:
    phase_b2 = _phase_b2_report()
    report = diagnose_b1_b2_ask_first_boundary(
        phase_b_report=_phase_b_report(),
        phase_b2_report=phase_b2,
        live_report=_live_report_with_unknown_estimate(phase_b2),
        semantic_register_text=_register_text(
            "  self_selected_basket_without_listed_items:\n"
            "    status: approved\n"
            "    selected_policy: ask_first_unresolved_no_logged_estimate\n"
        ),
    )

    assert report["semantic_policy"]["status"] == "approved"
    assert report["semantic_policy"]["selected_policy"] == "ask_first_unresolved_no_logged_estimate"
    assert report["validator"]["expected_verdict"] == "readiness_blocker"
    assert report["validator"]["status"] == "gap"
    assert report["primary_root_cause"] == "validator_classification_gap"


def test_diagnostic_post_alignment_sees_approved_policy_and_clarify_only_payload() -> None:
    phase_b2 = _phase_b2_report()
    live_report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=phase_b2,
        provider_outputs_by_case_id={
            "B2-004": {
                "clarification_question": "請列出滷味品項與大概份量。",
                "followup_question": "你吃了哪些滷味？",
            }
        },
        approved_ask_first_policy_ids=("self_selected_basket_without_listed_items",),
        selected_case_ids=("B2-004",),
    )

    report = diagnose_b1_b2_ask_first_boundary(
        phase_b_report=_phase_b_report(),
        phase_b2_report=phase_b2,
        live_report=live_report,
        semantic_register_text=_approved_register_text(),
    )

    assert report["primary_root_cause"] == "none"
    assert report["contributing_factors"] == []
    assert report["semantic_policy"] == {
        "decision_id": "self_selected_basket_without_listed_items",
        "status": "approved",
        "selected_policy": "ask_first_unresolved_no_logged_estimate",
    }
    assert report["live_payload"]["status"] == "pass"
    assert report["live_payload"]["task_type"] == "clarify_only"
    assert report["live_payload"]["item_results_allowed"] is False
    assert report["live_payload"]["estimate_allowed"] is False
    assert report["validator"]["actual_verdict"] == "diagnostic_observation"
    assert report["validator"]["status"] == "pass"
