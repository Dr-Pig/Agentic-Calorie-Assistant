from __future__ import annotations

import json

from app.advanced_shadow_lab.product_lab_exercise import run_product_lab_exercise_budget
from app.advanced_shadow_lab.product_lab_exercise_fixture_inputs import (
    build_product_lab_exercise_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_journey_coverage import (
    build_product_lab_journey_coverage_summary,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn


LAB_MODE = "isolated_advanced_product_lab"


def test_exercise_budget_lab_creates_lab_local_event_ledger_and_today_projection() -> None:
    artifact = run_product_lab_exercise_budget(
        fixture_inputs=build_product_lab_exercise_fixture_inputs("running_30m_met"),
        enabled=True,
    )

    assert artifact["artifact_type"] == "advanced_product_lab_exercise_budget_artifact"
    assert artifact["status"] == "pass"
    assert artifact["workflow_family"] == "exercise"
    assert artifact["semantic_extraction"]["decision_mode"] == "llm_fixture_output"
    assert artifact["semantic_extraction"]["exercise_type"] == "running"
    assert artifact["semantic_extraction"]["duration_minutes"] == 30
    assert artifact["semantic_extraction"]["raw_user_text_semantic_inference_performed"] is False
    assert artifact["estimate"]["estimated_kcal"] == 244
    assert artifact["estimate"]["formula_name"] == "met_kcal_v1"
    assert artifact["lab_exercise_event"]["exercise_type"] == "running"
    assert artifact["lab_exercise_event"]["estimated_kcal_burned"] == 244
    assert artifact["lab_ledger_entry"]["ledger_entry_type"] == "exercise_bonus"
    assert artifact["lab_ledger_entry"]["delta_kcal"] == 244
    assert artifact["lab_today_budget_projection"] == {
        "base_budget_kcal": 1400,
        "previous_effective_budget_kcal": 1400,
        "exercise_bonus_total_kcal": 244,
        "projected_effective_budget_kcal": 1644,
        "meal_consumption_total_kcal": 800,
        "projected_remaining_kcal": 844,
    }
    assert "跑步 30 分鐘" in artifact["chat_reply_packet"]["copy"]
    assert "244 kcal" in artifact["chat_reply_packet"]["copy"]
    assert "1644 kcal" in artifact["chat_reply_packet"]["copy"]
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["production_db_migration_allowed"] is False
    assert artifact["body_plan_mutated"] is False
    assert artifact["durable_product_memory_written"] is False


def test_exercise_budget_lab_preserves_user_asserted_kcal_without_recalculation() -> None:
    artifact = run_product_lab_exercise_budget(
        fixture_inputs=build_product_lab_exercise_fixture_inputs("user_asserted_300"),
        enabled=True,
    )

    assert artifact["status"] == "pass"
    assert artifact["semantic_extraction"]["calculation_basis"] == "user_asserted"
    assert artifact["estimate"]["estimated_kcal"] == 300
    assert artifact["estimate"]["formula_name"] == "user_asserted"
    assert artifact["lab_ledger_entry"]["delta_kcal"] == 300
    assert artifact["lab_today_budget_projection"]["projected_effective_budget_kcal"] == 1700
    assert artifact["semantic_extraction"]["raw_user_text_semantic_inference_performed"] is False


def test_exercise_budget_lab_unknown_exercise_asks_clarifying_question_without_budget_change() -> None:
    artifact = run_product_lab_exercise_budget(
        fixture_inputs=build_product_lab_exercise_fixture_inputs("unknown_exercise"),
        enabled=True,
    )

    assert artifact["status"] == "needs_clarification"
    assert artifact["semantic_extraction"]["exercise_action"] == "cannot_extract"
    assert artifact["lab_exercise_event"] == {}
    assert artifact["lab_ledger_entry"] == {}
    assert artifact["lab_today_budget_projection"]["projected_effective_budget_kcal"] == 1400
    assert artifact["chat_reply_packet"]["message_kind"] == "clarifying_question"
    assert "運動類型" in artifact["chat_reply_packet"]["copy"]
    assert artifact["canonical_product_mutation_allowed"] is False


def test_exercise_budget_lab_turn_surfaces_chat_and_today_state() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode=LAB_MODE,
        turn={
            "session_id": "lab-exercise-session",
            "turn_id": "lab-exercise-turn",
            "surface": "chat",
            "user_utterance": "我今天跑步 30 分鐘",
            "semantic_intent_fixture": "exercise_budget_bonus",
            "exercise_budget_enabled": True,
        },
        fixture_inputs=build_product_lab_exercise_fixture_inputs("running_30m_met"),
    )
    messages = artifact["lab_chat_surface"]["messages"]
    exercise_message = [item for item in messages if item["workflow_family"] == "exercise"][0]

    assert artifact["status"] == "pass"
    assert "exercise_budget" in artifact["product_capabilities_exercised"]
    assert artifact["product_lab_exercise_budget_artifact"]["status"] == "pass"
    assert exercise_message["trigger_type"] == "exercise_budget_bonus"
    assert exercise_message["exercise_budget"]["lab_ledger_entry"]["delta_kcal"] == 244
    assert exercise_message["exercise_budget"]["today_budget_projection"][
        "projected_effective_budget_kcal"
    ] == 1644
    assert exercise_message["exercise_budget"]["canonical_commit_requested"] is False
    assert exercise_message["canonical_mutation_requested"] is False
    assert artifact["lab_chat_response_packet"]["lab_runtime_capabilities"][
        "exercise_budget_served_to_lab"
    ] is True
    assert "no_send" not in json.dumps(artifact["lab_chat_surface"], ensure_ascii=False)
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["production_db_migration_allowed"] is False


def test_exercise_budget_journey_coverage_moves_u_to_executable_evidence() -> None:
    summary = build_product_lab_journey_coverage_summary({})

    assert "U" in summary["covered_by_existing_executable_evidence_journey_ids"]
    assert summary["product_capability_gap_journey_ids"] == []
    assert summary["implemented_but_missing_executable_scenario_journey_ids"] == []
    assert summary["next_product_capability_slice"] == ""
