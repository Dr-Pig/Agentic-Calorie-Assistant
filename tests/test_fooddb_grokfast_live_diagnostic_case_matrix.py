from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application import fooddb_grokfast_live_diagnostic_case_matrix as module
from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
    build_fooddb_grokfast_live_diagnostic_case_matrix_artifact,
)


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_fooddb_grokfast_live_case_matrix_is_plan_only_and_fixed() -> None:
    artifact = build_fooddb_grokfast_live_diagnostic_case_matrix_artifact()

    assert artifact["artifact_type"] == (
        "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix"
    )
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "live_diagnostic_plan_only"
    assert artifact["diagnostic_only"] is True
    assert artifact["plan_only"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_invoked"] is False
    assert artifact["websearch_invoked"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert [case["case_id"] for case in artifact["cases"]] == list(REQUIRED_CASE_IDS)


def test_fooddb_grokfast_live_case_matrix_covers_required_risk_families() -> None:
    by_id = _by_id(build_fooddb_grokfast_live_diagnostic_case_matrix_artifact())

    assert by_id["boba_large_half_sugar"]["family"] == "modifier_guard"
    assert by_id["boba_typo"]["family"] == "fuzzy_alias"
    assert by_id["bare_luwei"]["family"] == "bare_basket_followup"
    assert by_id["listed_luwei_components"]["family"] == "listed_basket_components"
    assert by_id["chicken_bento_less_rice"]["family"] == "generic_anchor_modifier_guard"
    assert by_id["bare_luwei"]["expected_manager_posture"] == "ask_followup_no_mutation"
    assert by_id["bare_luwei"]["expected_runtime_evidence_in_packet"] is False
    assert by_id["listed_luwei_components"]["expected_runtime_evidence_in_packet"] is True


def test_fooddb_grokfast_live_case_matrix_records_non_claims() -> None:
    artifact = build_fooddb_grokfast_live_diagnostic_case_matrix_artifact()

    assert "not_full_self_use_gate" in artifact["non_claims"]
    assert "not_websearch_exact_card_gate" in artifact["non_claims"]
    assert "not_final_response_quality_gate" in artifact["non_claims"]
    assert artifact["summary"]["case_count"] == 5
    assert artifact["summary"]["websearch_cases"] == 0
    assert artifact["summary"]["exact_card_cases"] == 0


def test_fooddb_grokfast_live_case_matrix_rejects_ad_hoc_or_unsafe_cases() -> None:
    artifact = build_fooddb_grokfast_live_diagnostic_case_matrix_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[0] = {
        **dict(cases[0]),
        "case_id": "ad_hoc_easy_fooddb_live_case",
        "live_provider_invoked": True,
        "websearch_invoked": True,
        "ledger_mutation_allowed": True,
        "runtime_truth_allowed": True,
    }

    blockers = module._validate(cases)

    assert "required_case_order_mismatch" in blockers
    assert "ad_hoc_easy_fooddb_live_case.live_provider_invoked" in blockers
    assert "ad_hoc_easy_fooddb_live_case.websearch_invoked" in blockers
    assert "ad_hoc_easy_fooddb_live_case.ledger_mutation_allowed" in blockers
    assert "ad_hoc_easy_fooddb_live_case.runtime_truth_allowed" in blockers


def test_fooddb_grokfast_live_case_matrix_rejects_bare_basket_runtime_evidence() -> None:
    artifact = build_fooddb_grokfast_live_diagnostic_case_matrix_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[2] = {
        **dict(cases[2]),
        "expected_runtime_evidence_in_packet": True,
        "expected_manager_posture": "estimate_from_packet",
    }

    blockers = module._validate(cases)

    assert "bare_luwei.bare_basket_runtime_evidence_expected" in blockers
    assert "bare_luwei.bare_basket_posture_not_followup" in blockers


def test_fooddb_grokfast_live_case_matrix_cli_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "fooddb_live_matrix.json"

    from scripts.build_accurate_intake_fooddb_grokfast_live_diagnostic_case_matrix import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["live_provider_invoked"] is False


def test_fooddb_grokfast_live_case_matrix_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/nutrition/application/fooddb_grokfast_live_diagnostic_case_matrix.py"),
        Path("scripts/build_accurate_intake_fooddb_grokfast_live_diagnostic_case_matrix.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "ManagerContextPacket",
        "live_llm_invoked = True",
        "live_provider_invoked = True",
        "websearch_invoked = True",
        "runtime_truth_allowed = True",
        "ledger_mutation_allowed = True",
        "product_readiness_claimed = True",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source
