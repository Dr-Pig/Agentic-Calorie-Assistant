from __future__ import annotations

import json
from pathlib import Path

from app.composition import accurate_intake_context_live_diagnostic_case_matrix as module
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    build_context_live_diagnostic_case_matrix_artifact,
)


REQUIRED_CASE_IDS = [
    "context_live_001_general_chat_no_mutation",
    "context_live_002_simple_food_log_candidate",
    "context_live_003_pending_followup_answer",
    "context_live_004_remove_previous_item",
    "context_live_005_remove_older_meal_item",
    "context_live_006_query_previous_drink_no_mutation",
    "context_live_007_daily_target_update",
    "context_live_008_meal_estimate_not_target",
    "context_live_009_simultaneous_log_and_modify",
    "context_live_010_cancel_do_not_log",
    "context_live_011_ambiguous_back_reference",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_context_live_diagnostic_case_matrix_defines_required_cases_without_live_calls() -> None:
    artifact = build_context_live_diagnostic_case_matrix_artifact()

    assert artifact["artifact_type"] == "accurate_intake_context_live_diagnostic_case_matrix"
    assert artifact["status"] == "pass"
    assert artifact["claim_scope"] == "pl_ce_context_live_diagnostic_case_selection_contract"
    assert artifact["diagnostic_only"] is True
    assert artifact["plan_only"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_invoked"] is False
    assert artifact["live_provider_approved"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert [case["case_id"] for case in artifact["cases"]] == REQUIRED_CASE_IDS


def test_context_live_diagnostic_case_matrix_covers_user_intent_boundaries() -> None:
    by_id = _by_id(build_context_live_diagnostic_case_matrix_artifact())

    assert by_id["context_live_001_general_chat_no_mutation"]["expected_manager_intent"] == "general_chat"
    assert by_id["context_live_003_pending_followup_answer"]["pending_pin_expected"] is True
    assert by_id["context_live_004_remove_previous_item"]["target_candidates_expected"] is True
    assert by_id["context_live_005_remove_older_meal_item"]["expected_manager_intent"] == (
        "older_meal_removal_candidate"
    )
    assert by_id["context_live_006_query_previous_drink_no_mutation"]["expected_workflow_effect"] == "query_only"
    assert by_id["context_live_007_daily_target_update"]["expected_workflow_effect"] == "target_update_candidate"
    assert by_id["context_live_008_meal_estimate_not_target"]["expected_workflow_effect"] == (
        "meal_estimate_context"
    )
    assert by_id["context_live_009_simultaneous_log_and_modify"]["expected_workflow_effect"] == (
        "compound_requires_manager_decomposition"
    )
    assert by_id["context_live_010_cancel_do_not_log"]["expected_manager_intent"] == (
        "cancel_pending_logging_candidate"
    )
    assert by_id["context_live_011_ambiguous_back_reference"]["ambiguity_expected"] is True


def test_context_live_diagnostic_case_matrix_rejects_ad_hoc_or_unsafe_cases() -> None:
    artifact = build_context_live_diagnostic_case_matrix_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[0] = {
        **dict(cases[0]),
        "case_id": "ad_hoc_easy_live_case",
        "live_provider_invoked": True,
        "fooddb_used": True,
        "mutation_allowed": True,
    }

    blockers = module._validate(cases)

    assert "required_case_order_mismatch" in blockers
    assert "ad_hoc_easy_live_case.live_provider_invoked" in blockers
    assert "ad_hoc_easy_live_case.fooddb_used" in blockers
    assert "ad_hoc_easy_live_case.mutation_allowed" in blockers


def test_context_live_diagnostic_case_matrix_rejects_missing_context_requirements() -> None:
    artifact = build_context_live_diagnostic_case_matrix_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[3] = {**dict(cases[3]), "expected_context_fields": ["context_policy_version"]}

    blockers = module._validate(cases)

    assert "context_live_004_remove_previous_item.target_candidates_not_required" in blockers


def test_context_live_diagnostic_case_matrix_cli_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "context_live_matrix.json"

    from scripts.build_accurate_intake_context_live_diagnostic_case_matrix import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["compound_cases"] == 1


def test_context_live_diagnostic_case_matrix_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_context_live_diagnostic_case_matrix.py"),
        Path("scripts/build_accurate_intake_context_live_diagnostic_case_matrix.py"),
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
        "live_provider_invoked = True",
        "fooddb_used = True",
        "manager_context_packet_schema_changed = True",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source
