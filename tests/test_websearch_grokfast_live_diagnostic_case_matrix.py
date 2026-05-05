from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application import websearch_grokfast_live_diagnostic_case_matrix as module
from app.nutrition.application.websearch_grokfast_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
    build_websearch_grokfast_live_diagnostic_case_matrix_artifact,
)


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_websearch_grokfast_live_case_matrix_is_plan_only_and_fixed() -> None:
    artifact = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()

    assert artifact["artifact_type"] == (
        "accurate_intake_websearch_grokfast_packet_live_diagnostic_case_matrix"
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
    assert artifact["packetizer_format_changed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert [case["case_id"] for case in artifact["cases"]] == list(REQUIRED_CASE_IDS)


def test_websearch_grokfast_live_case_matrix_covers_exact_and_negative_risks() -> None:
    by_id = _by_id(build_websearch_grokfast_live_diagnostic_case_matrix_artifact())

    assert by_id["websearch_official_exact_candidate"]["family"] == (
        "exact_candidate_candidate_only"
    )
    assert by_id["websearch_wrong_brand_official"]["family"] == "negative_wrong_brand"
    assert by_id["websearch_wrong_size_candidate"]["family"] == "negative_wrong_size"
    assert by_id["websearch_official_missing_nutrition"]["family"] == (
        "negative_missing_nutrition"
    )
    assert by_id["websearch_third_party_weak_source"]["family"] == "negative_weak_source"
    assert by_id["websearch_modifier_mismatch"]["family"] == "modifier_mismatch_guard"
    assert by_id["websearch_official_exact_candidate"]["websearch_candidate_only"] is True
    assert by_id["websearch_official_exact_candidate"]["runtime_truth_allowed"] is False
    assert by_id["websearch_wrong_brand_official"]["ledger_mutation_allowed"] is False


def test_websearch_grokfast_live_case_matrix_records_non_claims_and_summary() -> None:
    artifact = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()

    assert "not_full_self_use_gate" in artifact["non_claims"]
    assert "not_websearch_runtime_truth_gate" in artifact["non_claims"]
    assert "not_exact_card_promotion_gate" in artifact["non_claims"]
    assert "not_live_websearch_execution" in artifact["non_claims"]
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["exact_candidate_cases"] == 1
    assert artifact["summary"]["negative_case_count"] == 4
    assert artifact["summary"]["identity_mismatch_case_count"] == 2
    assert artifact["summary"]["missing_nutrition_case_count"] == 1
    assert artifact["summary"]["weak_source_case_count"] == 1
    assert artifact["summary"]["modifier_guard_cases"] == 1
    assert artifact["summary"]["runtime_truth_allowed_cases"] == 0
    assert artifact["summary"]["websearch_invoked_cases"] == 0
    assert artifact["summary"]["live_provider_invoked_cases"] == 0


def test_websearch_grokfast_live_case_matrix_rejects_happy_path_overfit() -> None:
    artifact = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases = cases[:1]

    blockers = module._validate(cases)

    assert "required_case_order_mismatch" in blockers
    assert "missing_family.negative_wrong_brand" in blockers
    assert "missing_family.negative_wrong_size" in blockers
    assert "missing_family.negative_missing_nutrition" in blockers
    assert "missing_family.negative_weak_source" in blockers
    assert "missing_family.modifier_mismatch_guard" in blockers


def test_websearch_grokfast_live_case_matrix_rejects_runtime_and_live_leaks() -> None:
    artifact = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[0] = {
        **dict(cases[0]),
        "live_provider_invoked": True,
        "websearch_invoked": True,
        "runtime_truth_allowed": True,
        "ledger_mutation_allowed": True,
        "exact_card_creation_allowed": True,
        "snippet_truth_allowed": True,
        "websearch_candidate_only": False,
    }

    blockers = module._validate(cases)

    case_id = "websearch_official_exact_candidate"
    assert f"{case_id}.live_provider_invoked" in blockers
    assert f"{case_id}.websearch_invoked" in blockers
    assert f"{case_id}.runtime_truth_allowed" in blockers
    assert f"{case_id}.ledger_mutation_allowed" in blockers
    assert f"{case_id}.exact_card_creation_allowed" in blockers
    assert f"{case_id}.snippet_truth_allowed" in blockers
    assert f"{case_id}.websearch_candidate_only_not_true" in blockers


def test_websearch_grokfast_live_case_matrix_rejects_weak_modifier_guard() -> None:
    artifact = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    modifier = dict(cases[-1])
    modifier["must_not_happen"] = ["runtime_ledger_mutation", "websearch_snippet_as_truth"]
    cases[-1] = modifier

    blockers = module._validate(cases)

    assert "websearch_modifier_mismatch.modifier_math_guard_missing" in blockers


def test_websearch_grokfast_live_case_matrix_cli_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "websearch_live_matrix.json"

    from scripts.build_accurate_intake_websearch_grokfast_live_diagnostic_case_matrix import (
        main,
    )

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["websearch_invoked"] is False


def test_websearch_grokfast_live_case_matrix_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_grokfast_live_diagnostic_case_matrix.py"),
        Path("scripts/build_accurate_intake_websearch_grokfast_live_diagnostic_case_matrix.py"),
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
        "exact_card_creation_allowed = True",
        "product_readiness_claimed = True",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source
