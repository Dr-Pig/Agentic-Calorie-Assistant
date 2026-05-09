from __future__ import annotations

import json
from pathlib import Path

from app.composition.dogfood_operator_review import build_dogfood_operator_review_surface


def _turn(
    turn_id: str,
    *,
    mutation_intent: str,
    intent_type: str = "log_meal",
    workflow_effect: str = "route_to_intake",
    final_action: str = "route_to_intake",
    mutation_or_query: str = "query",
    active_before: int = 0,
    active_after: int = 0,
    budget_before: int = 1600,
    budget_after: int = 1600,
    runtime_error: str | None = None,
) -> dict:
    turn = {
        "turn_id": turn_id,
        "raw_user_input": f"display only text {turn_id}",
        "assistant_response_summary": f"display only assistant text {turn_id}",
        "manager_decision": {
            "intent_type": intent_type,
            "workflow_effect": workflow_effect,
            "final_action": final_action,
            "mutation_intent_candidate": mutation_intent,
            "target_attachment": {"mode": "structured_fixture"},
        },
        "mutation_or_query": mutation_or_query,
        "state_before": {
            "budget_kcal": budget_before,
            "consumed_kcal": 0,
            "remaining_kcal": budget_before,
            "active_meal_count": active_before,
        },
        "state_after": {
            "budget_kcal": budget_after,
            "consumed_kcal": 0,
            "remaining_kcal": budget_after,
            "active_meal_count": active_after,
        },
        "state_delta": {},
    }
    if runtime_error is not None:
        turn["raw_response"] = {"error": runtime_error, "payload": None}
    return turn


def _one_day_report_with_unrelated_display_text() -> dict:
    return {
        "one_day_realistic_web_dogfood": {
            "status": "diagnostic_pass_with_evidence_gap",
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "turns": [
                _turn(
                    "target_001",
                    intent_type="set_manual_daily_target",
                    workflow_effect="manual_daily_target_update",
                    final_action="target_updated",
                    mutation_intent="budget_target_write",
                    mutation_or_query="mutation",
                    budget_before=0,
                    budget_after=1600,
                ),
                _turn("breakfast_001", mutation_intent="canonical_write"),
                _turn("lunch_001", mutation_intent="canonical_write"),
                _turn("tea_001", mutation_intent="canonical_write"),
                _turn(
                    "dinner_draft_001",
                    workflow_effect="draft_clarify_no_mutation",
                    final_action="ask_items",
                    mutation_intent="no_mutation",
                ),
                _turn(
                    "dinner_basket_001",
                    workflow_effect="listed_basket_commit",
                    final_action="commit",
                    mutation_intent="canonical_write",
                ),
                _turn(
                    "dinner_remove_001",
                    workflow_effect="correction_remove_item",
                    final_action="correction_applied",
                    mutation_intent="correction_write",
                ),
                _turn(
                    "query_001",
                    intent_type="answer_remaining_budget",
                    workflow_effect="answer_only",
                    final_action="answer_only",
                    mutation_intent="no_mutation",
                ),
            ],
            "evidence": {
                "daily_target_updated": True,
                "food_logs_created": False,
                "evidence_gap_observed": True,
                "evidence_gap_handled_without_fake_kcal": True,
                "pending_followup_used": False,
                "remove_item_negative_guard": {
                    "attempted": True,
                    "target_attachment_present": True,
                    "existing_item_id_present": False,
                    "runtime_blocked_missing_target": True,
                    "correction_or_removal_applied": False,
                },
                "same_truth_verified": "not_checked",
                "dogfood_review_queue_compatible": "not_checked",
                "local_data_hygiene_respected": "not_checked",
            },
            "blockers": ["food evidence gap prevented realistic food logging"],
        }
    }


def _browser_realistic_v2_report(
    *,
    manager_context_status: str = "not_available",
    chat_history_reloaded: bool = True,
    forbidden_storage_used: bool = False,
) -> dict:
    return {
        "artifact_type": "accurate_intake_browser_realistic_web_dogfood_v2",
        "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
        "fixture_manager_used": True,
        "fixture_evidence_used": True,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "browser_executed": True,
        "browser": {
            "target_update_rendered": True,
            "today_summary_rendered": True,
            "debug_surface_rendered": True,
            "runtime_status_surface_rendered": True,
            "browser_reload_checked": True,
            "chat_history_reloaded": chat_history_reloaded,
            "cjk_messages_rendered": True,
            "assistant_bubbles_rendered": True,
            "manager_context_status": manager_context_status,
            "evidence_gap_observed": True,
            "forbidden_storage_used": forbidden_storage_used,
            "turn_results": [
                {
                    "turn_id": "breakfast_001",
                    "raw_user_input": "早餐吃茶葉蛋和拿鐵",
                    "expected_manager_decision": {
                        "intent_type": "log_meal",
                        "workflow_effect": "route_to_intake",
                        "final_action": "commit",
                        "mutation_intent_candidate": "canonical_write",
                        "target_attachment": {"mode": "new_meal"},
                    },
                    "last_payload_parseable": True,
                    "runtime_error_present": False,
                }
            ],
            "storage": {
                "localStorageKeys": ["bad"] if forbidden_storage_used else [],
                "sessionStorageKeys": [],
            },
        },
        "blockers": [],
    }


def test_operator_review_keeps_pr110_diagnostic_gap_from_becoming_pass() -> None:
    artifact = build_dogfood_operator_review_surface(_one_day_report_with_unrelated_display_text())

    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["artifact_type"] == "accurate_intake_dogfood_operator_review_surface"
    assert artifact["source_status"] == "diagnostic_pass_with_evidence_gap"
    assert artifact["review_status"] == "generated"
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["canonical_eval_promoted"] is False
    assert artifact["status"] == "diagnostic_review_with_evidence_gap"
    assert artifact["summary"]["food_evidence_gap_turns"] == 4
    assert artifact["summary"]["successful_food_logs"] == 0
    assert artifact["summary"]["not_checked_surfaces"] == [
        "same_truth",
        "dogfood_review_queue",
        "local_data_hygiene",
    ]


def test_operator_review_classifies_turns_from_structured_fields_not_raw_text() -> None:
    artifact = build_dogfood_operator_review_surface(_one_day_report_with_unrelated_display_text())
    classifications = {
        turn["turn_id"]: turn["classification"]
        for turn in artifact["turn_reviews"]
    }

    assert classifications["target_001"] == "target_update_success"
    assert classifications["breakfast_001"] == "food_evidence_gap"
    assert classifications["lunch_001"] == "food_evidence_gap"
    assert classifications["tea_001"] == "food_evidence_gap"
    assert classifications["dinner_draft_001"] == "query_no_mutation"
    assert classifications["dinner_basket_001"] == "food_evidence_gap"
    assert classifications["dinner_remove_001"] == "blocked_mutation"
    assert classifications["query_001"] == "query_no_mutation"

    breakfast = next(
        turn for turn in artifact["turn_reviews"] if turn["turn_id"] == "breakfast_001"
    )
    assert breakfast["display_raw_user_input"] == "display only text breakfast_001"
    assert breakfast["classification_inputs"]["raw_user_input_used_for_classification"] is False
    assert breakfast["classification_inputs"]["assistant_text_used_for_classification"] is False
    assert breakfast["classification_inputs"]["allowed_fields_only"] is True
    assert breakfast["actual_mutation_result"]["active_meal_count_increased"] is False
    assert breakfast["reviewer_notes"] == ["canonical_write_intent_without_mutation"]


def test_operator_review_preserves_negative_guard_query_and_not_checked_statuses() -> None:
    artifact = build_dogfood_operator_review_surface(_one_day_report_with_unrelated_display_text())

    remove_turn = next(turn for turn in artifact["turn_reviews"] if turn["turn_id"] == "dinner_remove_001")
    assert remove_turn["classification"] == "blocked_mutation"
    assert remove_turn["evidence_gap_reason"] == "remove_item_target_missing_existing_item_id"
    assert remove_turn["actual_mutation_result"]["mutation_applied"] is False
    assert remove_turn["same_truth_status"] == "not_checked"

    query_turn = next(turn for turn in artifact["turn_reviews"] if turn["turn_id"] == "query_001")
    assert query_turn["classification"] == "query_no_mutation"
    assert query_turn["query_no_mutation_status"] == "state_unchanged"
    assert query_turn["same_truth_status"] == "not_checked"


def test_operator_review_classifies_runtime_error_as_manager_context_gap() -> None:
    report = _one_day_report_with_unrelated_display_text()
    report["one_day_realistic_web_dogfood"]["turns"][1] = _turn(
        "breakfast_001",
        mutation_intent="canonical_write",
        runtime_error="Exceeded fixture turns.",
    )

    artifact = build_dogfood_operator_review_surface(report)

    breakfast = next(turn for turn in artifact["turn_reviews"] if turn["turn_id"] == "breakfast_001")
    assert breakfast["classification"] == "manager_context_gap"
    assert breakfast["evidence_gap_reason"] == "runtime_error_or_missing_payload"
    assert breakfast["runtime_error_status"] == {
        "present": True,
        "error": "Exceeded fixture turns.",
        "payload_present": False,
    }
    assert breakfast["classification_inputs"]["raw_user_input_used_for_classification"] is False
    assert breakfast["classification_inputs"]["assistant_text_used_for_classification"] is False
    assert artifact["summary"]["manager_context_gap_turns"] == 1


def test_operator_review_accepts_browser_realistic_v2_without_pass_or_real_fooddb_claim() -> None:
    artifact = build_dogfood_operator_review_surface(_browser_realistic_v2_report())

    assert artifact["status"] == "browser_diagnostic_review_with_fixture_evidence_gap"
    assert artifact["source_artifact"] == "accurate_intake_browser_realistic_web_dogfood_v2"
    assert artifact["source_status"] == "browser_diagnostic_pass_with_fixture_evidence_gap"
    assert artifact["review_status"] == "generated"
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["canonical_eval_promoted"] is False
    assert artifact["real_fooddb_pass_claimed"] is False
    assert artifact["dogfood_pass"] is False
    assert artifact["production_readiness_claimed"] is False
    assert artifact["summary"]["manager_context_status"] == "not_available"
    assert artifact["summary"]["food_evidence_gap_turns"] == 1


def test_operator_review_browser_v2_manager_context_gap_stays_neutral() -> None:
    artifact = build_dogfood_operator_review_surface(
        _browser_realistic_v2_report(manager_context_status="missing_context_snapshot")
    )

    assert artifact["summary"]["manager_context_status"] == "missing_context_snapshot"
    assert artifact["manager_context_review"] == {
        "status": "missing_context_snapshot",
        "diagnostic_only": True,
        "context_engineering_fault_claimed": False,
    }
    serialized = json.dumps(artifact, ensure_ascii=False)
    assert "context_engineering_failed" not in serialized
    assert "ce_failed" not in serialized


def test_operator_review_browser_v2_rejects_context_status_overclaim() -> None:
    artifact = build_dogfood_operator_review_surface(
        _browser_realistic_v2_report(manager_context_status="context_engineering_failed")
    )

    assert artifact["summary"]["manager_context_status"] == "not_checked"
    assert "manager_context_status_overclaim" in artifact["summary"]["browser_surface_findings"]
    serialized = json.dumps(artifact, ensure_ascii=False)
    assert "context_engineering_failed" not in serialized


def test_operator_review_browser_v2_classifies_reload_and_storage_findings() -> None:
    artifact = build_dogfood_operator_review_surface(
        _browser_realistic_v2_report(
            chat_history_reloaded=False,
            forbidden_storage_used=True,
        )
    )

    assert "browser_reload_gap" in artifact["summary"]["browser_surface_findings"]
    assert "storage_violation" in artifact["summary"]["browser_surface_findings"]
    assert artifact["classification_policy"]["frontend_semantic_owner"] is False


def test_operator_review_builder_script_writes_local_only_artifact(tmp_path: Path) -> None:
    report_path = tmp_path / "one_day.json"
    output_path = tmp_path / "operator_review.json"
    report_path.write_text(
        json.dumps(_one_day_report_with_unrelated_display_text(), ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_dogfood_operator_review import main

    exit_code = main(["--dogfood-json", str(report_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["local_only"] is True
    assert artifact["do_not_commit"] is True
    assert artifact["source_status"] == "diagnostic_pass_with_evidence_gap"


def test_operator_review_builder_script_accepts_browser_v2_artifact(tmp_path: Path) -> None:
    report_path = tmp_path / "browser_v2.json"
    output_path = tmp_path / "operator_review_v2.json"
    report_path.write_text(
        json.dumps(_browser_realistic_v2_report(), ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_dogfood_operator_review import main

    exit_code = main(["--dogfood-json", str(report_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["source_artifact"] == "accurate_intake_browser_realistic_web_dogfood_v2"
    assert artifact["status"] == "browser_diagnostic_review_with_fixture_evidence_gap"
    assert artifact["summary"]["manager_context_status"] == "not_available"
