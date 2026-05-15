from __future__ import annotations

from types import SimpleNamespace

from app.composition.commit_boundary_preflight import run_commit_boundary_preflight
from app.composition.current_shell_golden_set_request_trace_outcomes import (
    approved_nutrition_evidence_present,
)
from app.composition.intake_entry_handoff import entry_handoff_tool_calls
from app.runtime.agent.founder_live_manager_contract import founder_live_manager_contract_constraints
from app.runtime.agent.manager_branch_shapes import manager_semantic_decision_schema
from app.runtime.contracts.phase_a import ManagerSemanticDecision


def _manager_decision(semantic_decision: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        workflow_effect="route_to_intake",
        semantic_decision=semantic_decision,
        target_attachment={},
    )


def test_manager_semantic_decision_schema_carries_manager_owned_user_kcal() -> None:
    schema = manager_semantic_decision_schema()

    assert "user_provided_kcal" in schema["properties"]

    decision = ManagerSemanticDecision(
        semantic_authority="manager_llm",
        current_turn_intent="log_meal",
        target_attachment={"mode": "new_workflow"},
        workflow_effect="commit",
        final_action_candidate="commit",
        estimation_posture="user_provided_kcal",
        followup_posture="optional_refinement",
        mutation_intent_candidate="canonical_write",
        uncertainty_posture="user_asserted",
        source="user_provided_kcal",
        user_provided_kcal=650,
    )

    assert decision.user_provided_kcal == 650


def test_entry_handoff_skips_estimate_tool_only_for_structured_manager_owned_user_kcal() -> None:
    common = {
        "semantic_authority": "manager_llm",
        "current_turn_intent": "log_meal",
        "target_attachment": {"mode": "new_workflow"},
        "workflow_effect": "commit",
        "final_action_candidate": "commit",
        "estimation_posture": "user_provided_kcal",
        "followup_posture": "optional_refinement",
        "mutation_intent_candidate": "canonical_write",
        "uncertainty_posture": "user_asserted",
        "source": "user_provided_kcal",
    }

    without_structured_number = entry_handoff_tool_calls(_manager_decision(common))
    with_structured_number = entry_handoff_tool_calls(
        _manager_decision({**common, "user_provided_kcal": 650})
    )

    assert [call["name"] for call in without_structured_number] == ["estimate_nutrition"]
    assert with_structured_number == []


def test_user_provided_kcal_artifact_is_commit_eligible_without_macro_truth() -> None:
    from app.nutrition.application import estimate_artifacts

    assert hasattr(estimate_artifacts, "build_user_provided_kcal_artifact")
    artifact = estimate_artifacts.build_user_provided_kcal_artifact(
        None,
        user_external_id="user-1",
        raw_user_input="breakfast was 650 kcal",
        local_date="2026-05-14",
        user_provided_kcal=650,
    )
    payload = artifact.payload
    trace = dict(payload.trace_contract)

    assert payload.estimated_kcal == 650
    assert payload.protein_g == 0
    assert payload.carb_g == 0
    assert payload.fat_g == 0
    assert trace["source_basis"] == "user_provided_kcal"
    assert trace["macro_visibility_status"] == "hidden_missing_source"
    assert trace["optional_refinement_allowed"] is True
    assert trace["approved_user_provided_kcal_trace"]["runtime_truth_allowed"] is True
    assert trace["approved_user_provided_kcal_trace"]["deterministic_text_extraction_used"] is False

    result = run_commit_boundary_preflight(
        payload=payload,
        manager_final_action="commit",
        active_body_plan_present=True,
        manager_semantic_decision={
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "workflow_effect": "commit",
            "final_action_candidate": "commit",
            "mutation_intent_candidate": "canonical_write",
            "source": "user_provided_kcal",
            "user_provided_kcal": 650,
        },
    )

    assert result.blocked is False
    assert result.projected_commit_intent == "commit"


def test_golden_adapter_treats_user_provided_kcal_as_approved_kcal_evidence() -> None:
    request_trace = {
        "tool_outputs": {
            "tool_results": [
                {
                    "tool_name": "user_provided_kcal_evidence",
                    "evidence": {
                        "nutrition_payload": {
                            "estimated_kcal": 650,
                            "trace_contract": {
                                "source_basis": "user_provided_kcal",
                                "approved_user_provided_kcal_trace": {
                                    "runtime_truth_allowed": True,
                                    "macro_truth_allowed": False,
                                    "deterministic_text_extraction_used": False,
                                },
                            },
                        }
                    },
                }
            ]
        }
    }

    assert approved_nutrition_evidence_present(request_trace, {}) is True


def test_founder_live_contract_treats_user_provided_kcal_tool_packet_as_nutrition_evidence() -> None:
    constraints = founder_live_manager_contract_constraints(
        "test-profile",
        tool_results=[
            {
                "tool_name": "user_provided_kcal_evidence",
                "evidence": {
                    "nutrition_payload": {
                        "estimated_kcal": 650,
                        "trace_contract": {
                            "source_basis": "user_provided_kcal",
                            "approved_user_provided_kcal_trace": {
                                "runtime_truth_allowed": True,
                                "macro_truth_allowed": False,
                                "deterministic_text_extraction_used": False,
                            },
                        },
                    }
                },
            }
        ],
    )

    evidence_state = constraints["manager_contract_evidence_state"]
    assert evidence_state["nutrition_evidence_present"] is True


def test_user_provided_kcal_visible_reply_is_natural_and_not_duplicate() -> None:
    from app.nutrition.application.estimate_artifacts import build_user_provided_kcal_artifact
    from app.runtime.application.reply_renderer import render_intake_reply

    artifact = build_user_provided_kcal_artifact(
        None,
        user_external_id="user-1",
        raw_user_input="早餐吃了 650 kcal",
        local_date="2026-05-14",
        user_provided_kcal=650,
    )
    text = render_intake_reply(
        intent_type="log_meal",
        nutrition_payload=artifact.payload,
        persistence_result=SimpleNamespace(canonical_commit={"meal_version_id": 123}),
        manager_final_action="commit",
        remaining_budget=SimpleNamespace(status="ready", remaining_kcal=662),
    )

    assert text.count("650 kcal") == 1
    assert "三大營養素資料不足" in text
    assert "補食物內容" in text
    assert "早餐吃了 650 kcal 650 kcal" not in text
