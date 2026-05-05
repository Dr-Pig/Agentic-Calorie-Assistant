from __future__ import annotations

import json
from pathlib import Path

from app.composition import accurate_intake_context_conditioned_intent_wall as module
from app.composition.accurate_intake_context_conditioned_intent_wall import (
    build_context_conditioned_intent_wall_artifact,
)


REQUIRED_SCENARIOS = [
    "luwei_pending_components_followup",
    "half_sugar_no_prior_drink",
    "half_sugar_one_prior_drink",
    "half_sugar_multiple_drinks",
    "remove_tofu_no_luwei_context",
    "remove_tofu_one_luwei",
    "remove_tofu_multiple_targets",
    "previous_drink_calorie_query",
    "explicit_daily_target_1800",
    "meal_estimate_800_not_target",
    "long_session_less_rice",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(scenario["scenario_id"]): scenario
        for scenario in artifact["scenarios"]  # type: ignore[index]
    }


def test_context_conditioned_intent_wall_covers_required_short_term_context_cases() -> None:
    artifact = build_context_conditioned_intent_wall_artifact()

    assert artifact["artifact_type"] == "accurate_intake_context_conditioned_intent_wall"
    assert artifact["status"] == "pass"
    assert artifact["fixture_manager_used"] is True
    assert artifact["manager_fixture_semantic_source"] == "fixture_manager_structured_decision"
    assert artifact["live_llm_invoked"] is False
    assert artifact["production_db_used"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["deterministic_selected_intent"] is False
    assert artifact["deterministic_selected_target"] is False
    assert artifact["frontend_raw_text_semantic_router"] is False
    assert artifact["mutation_authority"] is False
    assert [scenario["scenario_id"] for scenario in artifact["scenarios"]] == REQUIRED_SCENARIOS


def test_context_conditioned_intent_wall_proves_same_utterance_changes_with_context() -> None:
    artifact = build_context_conditioned_intent_wall_artifact()
    by_id = _by_id(artifact)

    no_drink = by_id["half_sugar_no_prior_drink"]
    one_drink = by_id["half_sugar_one_prior_drink"]
    multiple_drinks = by_id["half_sugar_multiple_drinks"]

    assert no_drink["raw_user_input"] == one_drink["raw_user_input"] == multiple_drinks["raw_user_input"]
    assert no_drink["expected_semantic_posture"] == "clarification_required"
    assert no_drink["target_candidate_count"] == 0
    assert one_drink["expected_semantic_posture"] == "correction_candidate_available"
    assert one_drink["target_candidate_count"] == 1
    assert multiple_drinks["expected_semantic_posture"] == "ambiguous_target"
    assert multiple_drinks["ambiguity_preserved"] is True
    assert multiple_drinks["target_candidate_count"] == 2


def test_context_conditioned_intent_wall_verifies_pending_followup_and_query_boundaries() -> None:
    artifact = build_context_conditioned_intent_wall_artifact()
    by_id = _by_id(artifact)

    luwei = by_id["luwei_pending_components_followup"]
    query = by_id["previous_drink_calorie_query"]
    target_update = by_id["explicit_daily_target_1800"]
    meal_estimate = by_id["meal_estimate_800_not_target"]

    assert luwei["pending_followup_carryover"] is True
    assert luwei["pending_draft_present"] is True
    assert luwei["expected_semantic_posture"] == "attach_to_pending_draft"
    assert luwei["fixture_manager_decision"]["semantic_source"] == "fixture_manager_structured_decision"  # type: ignore[index]

    assert query["expected_semantic_posture"] == "query_no_mutation"
    assert query["query_no_mutation"] is True
    assert query["mutation_authority"] is False

    assert target_update["expected_semantic_posture"] == "daily_target_update_candidate"
    assert target_update["target_update_requires_manager_decision"] is True
    assert meal_estimate["expected_semantic_posture"] == "meal_estimate_context"
    assert meal_estimate["target_update_requires_manager_decision"] is False


def test_context_conditioned_intent_wall_verifies_long_session_bounds_context_without_losing_targets() -> None:
    artifact = build_context_conditioned_intent_wall_artifact()
    long_session = _by_id(artifact)["long_session_less_rice"]

    assert long_session["recent_chat_message_count"] == 20
    assert long_session["recent_chat_messages_omitted"] > 0
    assert long_session["target_candidate_count"] >= 1
    assert long_session["expected_semantic_posture"] == "correction_candidate_available"
    assert long_session["ambiguity_preserved"] is False


def test_context_conditioned_intent_wall_rejects_candidate_posture_without_candidates() -> None:
    artifact = build_context_conditioned_intent_wall_artifact()
    scenarios = list(artifact["scenarios"])  # type: ignore[index]
    one_luwei = next(
        scenario for scenario in scenarios if scenario["scenario_id"] == "remove_tofu_one_luwei"
    )
    one_luwei["target_candidate_count"] = 0
    one_luwei["target_candidates_present"] = False

    blockers = module._validate(scenarios)

    assert "remove_tofu_one_luwei.candidate_target_missing" in blockers


def test_context_conditioned_intent_wall_rejects_clarification_with_target_candidates() -> None:
    artifact = build_context_conditioned_intent_wall_artifact()
    scenarios = list(artifact["scenarios"])  # type: ignore[index]
    no_drink = next(
        scenario for scenario in scenarios if scenario["scenario_id"] == "half_sugar_no_prior_drink"
    )
    no_drink["target_candidate_count"] = 1
    no_drink["target_candidates_present"] = True

    blockers = module._validate(scenarios)

    assert "half_sugar_no_prior_drink.clarification_has_unexpected_target_candidates" in blockers


def test_context_conditioned_intent_wall_rejects_fixture_decision_posture_drift() -> None:
    artifact = build_context_conditioned_intent_wall_artifact()
    scenarios = list(artifact["scenarios"])  # type: ignore[index]
    query = next(
        scenario for scenario in scenarios if scenario["scenario_id"] == "previous_drink_calorie_query"
    )
    query["fixture_manager_decision"] = {
        **dict(query["fixture_manager_decision"]),  # type: ignore[arg-type]
        "expected_semantic_posture": "correction_candidate_available",
        "mutation_intent_candidate": "correction_candidate",
    }

    blockers = module._validate(scenarios)

    assert "previous_drink_calorie_query.fixture_decision_posture_mismatch" in blockers
    assert "previous_drink_calorie_query.query_mutation_intent_not_no_mutation" in blockers


def test_context_conditioned_intent_wall_rejects_target_update_and_meal_estimate_drift() -> None:
    artifact = build_context_conditioned_intent_wall_artifact()
    scenarios = list(artifact["scenarios"])  # type: ignore[index]
    target_update = next(
        scenario for scenario in scenarios if scenario["scenario_id"] == "explicit_daily_target_1800"
    )
    meal_estimate = next(
        scenario for scenario in scenarios if scenario["scenario_id"] == "meal_estimate_800_not_target"
    )
    target_update["fixture_manager_decision"] = {
        **dict(target_update["fixture_manager_decision"]),  # type: ignore[arg-type]
        "mutation_intent_candidate": "meal_estimate_candidate",
    }
    meal_estimate["target_update_requires_manager_decision"] = True
    meal_estimate["fixture_manager_decision"] = {
        **dict(meal_estimate["fixture_manager_decision"]),  # type: ignore[arg-type]
        "mutation_intent_candidate": "target_update_candidate",
    }

    blockers = module._validate(scenarios)

    assert "explicit_daily_target_1800.target_update_mutation_candidate_missing" in blockers
    assert "meal_estimate_800_not_target.meal_estimate_marked_as_target_update" in blockers
    assert "meal_estimate_800_not_target.meal_estimate_mutation_candidate_missing" in blockers


def test_context_conditioned_intent_wall_cli_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "context_conditioned_intent_wall.json"

    from scripts.run_accurate_intake_context_conditioned_intent_wall import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["summary"]["scenario_count"] == len(REQUIRED_SCENARIOS)


def test_context_conditioned_intent_wall_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_context_conditioned_intent_wall.py"),
        Path("scripts/run_accurate_intake_context_conditioned_intent_wall.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "tavily_adapter",
        "Tavily",
        "Kimi",
        "GrokFast",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "manager_context_packet_schema_changed = True",
        "deterministic_selected_intent = True",
        "deterministic_selected_target = True",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source


def test_ci_runs_context_conditioned_intent_wall() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "test_accurate_intake_context_conditioned_intent_wall.py" in workflow
    assert "run_accurate_intake_context_conditioned_intent_wall.py" in workflow
    assert "accurate_intake_context_conditioned_intent_wall_ci.json" in workflow
    assert "accurate-intake-context-conditioned-intent-wall-report" in workflow
