from __future__ import annotations

import json
from pathlib import Path

from app.composition import accurate_intake_correction_removal_fixture_flow as module
from app.composition.accurate_intake_correction_removal_fixture_flow import (
    build_correction_removal_fixture_flow_artifact,
)


REQUIRED_SCENARIOS = [
    "remove_previous_item_ambiguous",
    "remove_named_item_candidate",
    "modify_drink_sugar_candidate",
    "modify_rice_portion_candidate",
    "correct_previous_identity_ambiguous",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(scenario["scenario_id"]): scenario
        for scenario in artifact["scenarios"]  # type: ignore[index]
    }


def test_correction_removal_fixture_flow_is_diagnostic_and_depends_on_context_wall() -> None:
    artifact = build_correction_removal_fixture_flow_artifact()

    assert artifact["artifact_type"] == "accurate_intake_correction_removal_fixture_flow"
    assert artifact["status"] == "pass"
    assert artifact["context_conditioned_intent_wall_required"] is True
    assert artifact["context_conditioned_intent_wall_status"] == "pass"
    assert artifact["semantic_owner"] == "fixture_manager_structured_decision"
    assert artifact["fixture_manager_used"] is True
    assert artifact["manager_fixture_semantic_source"] == "fixture_manager_structured_decision"
    assert artifact["candidate_or_ambiguity_render_ready"] is True
    assert artifact["context_conditioned_intent_wall_scenario_links_valid"] is True
    assert artifact["frontend_render_only"] is True
    assert artifact["frontend_selects_target"] is False
    assert artifact["deterministic_selected_target"] is False
    assert artifact["deterministic_selected_intent"] is False
    assert artifact["mutation_authority"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["private_self_use_approved"] is False
    assert [scenario["scenario_id"] for scenario in artifact["scenarios"]] == REQUIRED_SCENARIOS
    forbidden_true_flags = [
        "frontend_selects_target",
        "deterministic_selected_target",
        "deterministic_selected_intent",
        "mutation_authority",
        "manager_context_packet_schema_changed",
        "live_llm_invoked",
        "fooddb_truth_updated",
        "fooddb_evidence_used",
        "websearch_evidence_used",
        "web_tavily_used",
        "production_db_used",
        "real_fooddb_pass_claimed",
        "dogfood_pass",
        "web_readiness_claimed",
        "product_readiness_claimed",
        "private_self_use_approved",
    ]
    for flag in forbidden_true_flags:
        assert artifact[flag] is False


def test_correction_removal_fixture_flow_preserves_ambiguity_and_renders_candidates_only() -> None:
    artifact = build_correction_removal_fixture_flow_artifact()
    by_id = _by_id(artifact)

    remove_previous = by_id["remove_previous_item_ambiguous"]
    correct_identity = by_id["correct_previous_identity_ambiguous"]
    remove_named = by_id["remove_named_item_candidate"]

    assert remove_previous["ui_expected_state"] == "show_ambiguity"
    assert remove_previous["ambiguity_preserved"] is True
    assert remove_previous["target_candidate_count"] >= 2
    assert remove_previous["frontend_selects_target"] is False
    assert remove_previous["deterministic_selected_target"] is False

    assert correct_identity["ui_expected_state"] == "show_ambiguity"
    assert correct_identity["ambiguity_preserved"] is True
    assert correct_identity["target_candidate_count"] >= 2
    assert correct_identity["requires_manager_or_clarification"] is True

    assert remove_named["ui_expected_state"] == "show_candidate_list"
    assert remove_named["target_resolution_status"] == "candidate_supported"
    assert remove_named["target_candidate_count"] == 1
    assert remove_named["frontend_render_source"] == "backend_structured_context"
    candidate = remove_named["target_candidates"][0]  # type: ignore[index]
    assert candidate["read_only"] is True
    assert candidate["mutation_authority"] is False
    assert candidate["frontend_selectable_as_final_target"] is False


def test_correction_removal_fixture_flow_covers_modification_candidates_without_mutation() -> None:
    artifact = build_correction_removal_fixture_flow_artifact()
    by_id = _by_id(artifact)

    drink = by_id["modify_drink_sugar_candidate"]
    rice = by_id["modify_rice_portion_candidate"]

    for scenario in (drink, rice):
        assert scenario["ui_expected_state"] == "show_candidate_list"
        assert scenario["target_resolution_status"] == "candidate_supported"
        assert scenario["target_candidate_count"] == 1
        assert scenario["manager_fixture_decision"]["semantic_source"] == "fixture_manager_structured_decision"  # type: ignore[index]
        assert scenario["frontend_selects_target"] is False
        assert scenario["deterministic_selected_target"] is False
        assert scenario["mutation_authority"] is False


def test_correction_removal_fixture_flow_rejects_candidate_flow_without_candidates() -> None:
    artifact = build_correction_removal_fixture_flow_artifact()
    scenarios = list(artifact["scenarios"])  # type: ignore[index]
    remove_named = next(
        scenario for scenario in scenarios if scenario["scenario_id"] == "remove_named_item_candidate"
    )
    remove_named["target_candidate_count"] = 0
    remove_named["target_candidates_present"] = False

    blockers = module._validate(scenarios, context_wall_status="pass")

    assert "remove_named_item_candidate.candidate_target_missing" in blockers


def test_correction_removal_fixture_flow_rejects_stale_context_wall_links() -> None:
    artifact = build_correction_removal_fixture_flow_artifact()
    scenarios = list(artifact["scenarios"])  # type: ignore[index]

    blockers = module._validate(
        scenarios,
        context_wall_status="pass",
        context_wall_scenarios={},
    )

    assert "remove_previous_item_ambiguous.context_wall_scenario_missing" in blockers


def test_correction_removal_fixture_flow_rejects_frontend_target_selection() -> None:
    artifact = build_correction_removal_fixture_flow_artifact()
    scenarios = list(artifact["scenarios"])  # type: ignore[index]
    scenarios[0]["frontend_selects_target"] = True

    blockers = module._validate(scenarios, context_wall_status="pass")

    assert "remove_previous_item_ambiguous.frontend_selects_target" in blockers


def test_correction_removal_fixture_flow_cli_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "correction_removal_fixture_flow.json"

    from scripts.run_accurate_intake_correction_removal_fixture_flow import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["summary"]["scenario_count"] == len(REQUIRED_SCENARIOS)


def test_correction_removal_fixture_flow_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_correction_removal_fixture_flow.py"),
        Path("scripts/run_accurate_intake_correction_removal_fixture_flow.py"),
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
        "frontend_selects_target = True",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source


def test_ci_runs_correction_removal_fixture_flow() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "test_accurate_intake_correction_removal_fixture_flow.py" in workflow
    assert "run_accurate_intake_correction_removal_fixture_flow.py" in workflow
    assert "accurate_intake_correction_removal_fixture_flow_ci.json" in workflow
    assert "accurate-intake-correction-removal-fixture-flow-report" in workflow
