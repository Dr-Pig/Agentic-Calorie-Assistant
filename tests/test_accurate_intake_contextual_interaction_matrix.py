from __future__ import annotations

import json
from pathlib import Path

from app.composition import accurate_intake_contextual_interaction_matrix as module
from app.composition.accurate_intake_contextual_interaction_matrix import (
    build_contextual_interaction_matrix_artifact,
)


REQUIRED_INTERACTIONS = [
    "pending_luwei_components_answer",
    "modify_drink_sugar_no_prior_drink",
    "modify_drink_sugar_one_prior_drink",
    "modify_drink_sugar_multiple_drinks",
    "remove_tofu_no_luwei_context",
    "remove_tofu_one_luwei",
    "remove_tofu_multiple_targets",
    "previous_drink_calorie_query",
    "daily_target_update_1800",
    "meal_estimate_800_not_target",
    "long_session_less_rice",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(row["interaction_id"]): row
        for row in artifact["interactions"]  # type: ignore[index]
    }


def test_contextual_interaction_matrix_covers_required_short_term_interactions() -> None:
    artifact = build_contextual_interaction_matrix_artifact()

    assert artifact["artifact_type"] == "accurate_intake_contextual_interaction_matrix"
    assert artifact["status"] == "pass"
    assert artifact["claim_scope"] == "local_pl_ce_short_term_context_interaction_matrix"
    assert artifact["semantic_owner"] == "fixture_manager_structured_decision"
    assert artifact["manager_fixture_semantic_source_used"] is True
    assert artifact["deterministic_supplies_candidates_and_pins_only"] is True
    assert artifact["deterministic_selected_intent"] is False
    assert artifact["deterministic_selected_target"] is False
    assert artifact["frontend_raw_text_semantic_router"] is False
    assert artifact["frontend_semantic_owner"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["fooddb_truth_changed"] is False
    assert artifact["web_tavily_used"] is False
    assert [row["interaction_id"] for row in artifact["interactions"]] == REQUIRED_INTERACTIONS


def test_contextual_interaction_matrix_links_context_wall_and_ui_flow_evidence() -> None:
    artifact = build_contextual_interaction_matrix_artifact()
    by_id = _by_id(artifact)

    pending = by_id["pending_luwei_components_answer"]
    assert pending["context_wall_scenario_id"] == "luwei_pending_components_followup"
    assert pending["expected_semantic_posture"] == "attach_to_pending_draft"
    assert pending["pending_followup_required"] is True
    assert pending["pending_draft_required"] is True
    assert pending["ui_render_obligation"] == "render_pending_followup_context"

    one_drink = by_id["modify_drink_sugar_one_prior_drink"]
    assert one_drink["context_wall_scenario_id"] == "half_sugar_one_prior_drink"
    assert one_drink["correction_flow_scenario_id"] == "modify_drink_sugar_candidate"
    assert one_drink["target_candidates_required"] is True
    assert one_drink["ui_render_obligation"] == "render_read_only_target_candidates"

    ambiguous = by_id["modify_drink_sugar_multiple_drinks"]
    assert ambiguous["expected_semantic_posture"] == "ambiguous_target"
    assert ambiguous["ambiguity_must_be_preserved"] is True
    assert ambiguous["ui_render_obligation"] == "render_ambiguity_without_target_selection"


def test_contextual_interaction_matrix_keeps_query_target_update_and_meal_estimate_distinct() -> None:
    by_id = _by_id(build_contextual_interaction_matrix_artifact())

    query = by_id["previous_drink_calorie_query"]
    target = by_id["daily_target_update_1800"]
    meal = by_id["meal_estimate_800_not_target"]

    assert query["workflow_effect"] == "query_only"
    assert query["query_no_mutation"] is True
    assert query["mutation_authority"] is False
    assert query["responder_allowed_fact_scenario_id"] == "candidate_supported_no_mutation"

    assert target["workflow_effect"] == "target_update_candidate"
    assert target["target_update_requires_manager_decision"] is True
    assert target["mutation_authority"] is False
    assert target["responder_allowed_fact_scenario_id"] == "committed_backend_budget"

    assert meal["workflow_effect"] == "meal_estimate_context"
    assert meal["target_update_requires_manager_decision"] is False
    assert meal["mutation_authority"] is False
    assert meal["responder_allowed_fact_scenario_id"] == "committed_backend_budget"


def test_contextual_interaction_matrix_rejects_missing_linked_context_wall_case() -> None:
    artifact = build_contextual_interaction_matrix_artifact()
    rows = list(artifact["interactions"])  # type: ignore[index]
    rows[0] = {**dict(rows[0]), "context_wall_scenario_id": "missing"}

    blockers = module._validate(
        rows,
        context_wall=module._context_wall_by_id(),
        correction_flow=module._correction_flow_by_id(),
        responder_scenarios=module._responder_scenarios_by_id(),
    )

    assert "pending_luwei_components_answer.context_wall_scenario_missing" in blockers


def test_contextual_interaction_matrix_rejects_missing_responder_link() -> None:
    artifact = build_contextual_interaction_matrix_artifact()
    rows = list(artifact["interactions"])  # type: ignore[index]
    rows[8] = {**dict(rows[8]), "responder_allowed_fact_scenario_id": None}

    blockers = module._validate(
        rows,
        context_wall=module._context_wall_by_id(),
        correction_flow=module._correction_flow_by_id(),
        responder_scenarios=module._responder_scenarios_by_id(),
    )

    assert "daily_target_update_1800.responder_scenario_missing" in blockers


def test_contextual_interaction_matrix_rejects_frontend_or_deterministic_semantic_ownership() -> None:
    artifact = build_contextual_interaction_matrix_artifact()
    rows = list(artifact["interactions"])  # type: ignore[index]
    rows[1] = {
        **dict(rows[1]),
        "frontend_semantic_owner": True,
        "deterministic_selected_intent": True,
    }

    blockers = module._validate(
        rows,
        context_wall=module._context_wall_by_id(),
        correction_flow=module._correction_flow_by_id(),
        responder_scenarios=module._responder_scenarios_by_id(),
    )

    assert "modify_drink_sugar_no_prior_drink.frontend_semantic_owner" in blockers
    assert "modify_drink_sugar_no_prior_drink.deterministic_selected_intent" in blockers


def test_contextual_interaction_matrix_cli_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "contextual_interaction_matrix.json"

    from scripts.build_accurate_intake_contextual_interaction_matrix import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["summary"]["interaction_count"] == len(REQUIRED_INTERACTIONS)
    assert artifact["summary"]["ambiguity_preserved_interactions"] >= 2


def test_contextual_interaction_matrix_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_contextual_interaction_matrix.py"),
        Path("scripts/build_accurate_intake_contextual_interaction_matrix.py"),
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
