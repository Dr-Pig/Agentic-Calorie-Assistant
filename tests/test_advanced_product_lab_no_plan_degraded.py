from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_no_plan_degraded import (
    run_product_lab_no_plan_degraded,
)
from app.advanced_shadow_lab.product_lab_no_plan_fixture_inputs import (
    build_product_lab_no_plan_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.shared.infra.json_artifacts import read_json_artifact


def test_product_lab_no_plan_degraded_uses_existing_budget_contracts() -> None:
    artifact = run_product_lab_no_plan_degraded(
        fixture_inputs=build_product_lab_no_plan_fixture_inputs(),
        enabled=True,
    )

    assert artifact["artifact_type"] == "advanced_product_lab_no_plan_degraded_artifact"
    assert artifact["status"] == "pass"
    assert artifact["remaining_budget_contract"]["status"] == "onboarding_required"
    assert artifact["budget_boundary_projection"]["fallback_honesty_decision"] == {
        "budget_answer_mode": "degraded",
        "concrete_remaining_kcal_allowed": False,
        "onboarding_guidance_allowed": True,
        "intake_allowed_without_plan": True,
    }
    assert artifact["intake_logging_allowed_without_plan"] is True
    assert artifact["intake_packet"]["meal_title"] == "beef noodle soup"
    assert artifact["intake_packet"]["estimated_kcal"] == 650
    assert artifact["intake_packet"]["remaining_budget_visible"] is False
    assert artifact["intake_packet"]["daily_target_visible"] is False
    assert artifact["budget_query_packet"]["remaining_kcal"] is None
    assert artifact["budget_query_packet"]["daily_target_kcal"] is None
    assert artifact["budget_query_packet"]["onboarding_cta"]["action"] == "start_onboarding"
    assert artifact["today_ui_mirror"] == {
        "surface": "today",
        "no_active_body_plan": True,
        "daily_target_visible": False,
        "remaining_budget_visible": False,
        "daily_target_kcal": None,
        "remaining_kcal": None,
        "onboarding_entry_visible": True,
    }
    assert artifact["advanced_trigger_policy"] == {
        "recommendation_allowed": False,
        "rescue_allowed": False,
        "calibration_allowed": False,
        "proactive_allowed": False,
    }
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["body_plan_created"] is False
    assert artifact["day_budget_ledger_created"] is False


def test_product_lab_turn_surfaces_no_plan_chat_and_ui_mirror() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_no_plan_turn("no-plan-turn-1"),
        fixture_inputs=build_product_lab_no_plan_fixture_inputs(),
    )

    assert artifact["status"] == "pass"
    messages = artifact["lab_chat_surface"]["messages"]
    assert [message["workflow_family"] for message in messages] == [
        "intake_logging",
        "budget_query",
    ]
    intake = messages[0]["no_plan_degraded"]
    budget = messages[1]["no_plan_degraded"]
    assert intake["intake_packet"]["estimated_kcal"] == 650
    assert intake["intake_packet"]["remaining_budget_visible"] is False
    assert budget["budget_query_packet"]["onboarding_cta"]["action"] == "start_onboarding"
    assert budget["budget_query_packet"]["remaining_kcal"] is None
    assert artifact["product_lab_no_plan_degraded_artifact"]["today_ui_mirror"][
        "daily_target_kcal"
    ] is None
    assert artifact["product_lab_proactive_artifact"]["candidate_count"] == 0
    assert artifact["product_lab_rescue_artifact"]["status"] == "not_applicable"
    assert artifact["product_lab_calibration_artifact"]["status"] == "not_applicable"


def test_product_lab_session_records_no_plan_degraded_journey(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-no-plan",
        fixture_inputs=build_product_lab_no_plan_fixture_inputs(),
        turns=[_no_plan_turn("t1-no-plan")],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_no_plan_degraded_turn_count"] == 1
    assert artifact["lab_no_plan_intake_logging_allowed"] is True
    assert artifact["lab_no_plan_budget_query_degraded"] is True
    assert artifact["lab_no_plan_today_ui_hides_target_and_remaining"] is True
    assert artifact["lab_no_plan_onboarding_cta_visible"] is True
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["mainline_runtime_connected"] is False

    [turn_path] = [Path(path) for path in artifact["turn_artifact_paths"]]
    turn_record = read_json_artifact(turn_path)
    no_plan = turn_record["turn_artifact"]["product_lab_no_plan_degraded_artifact"]
    assert no_plan["budget_boundary_projection"]["owner_alignment"] == "aligned"
    assert no_plan["today_ui_mirror"]["remaining_kcal"] is None


def _no_plan_turn(turn_id: str) -> dict[str, object]:
    return {
        "session_id": "lab-session-no-plan",
        "turn_id": turn_id,
        "surface": "chat",
        "user_utterance": "fixture text is not a semantic oracle",
        "semantic_intent_fixture": "no_plan_degraded_journey",
        "no_plan_degraded_enabled": True,
    }
