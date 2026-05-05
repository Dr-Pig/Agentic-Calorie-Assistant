from __future__ import annotations

from pathlib import Path

from app.nutrition.application.fooddb_manager_packet_smoke import (
    FOODDB_PACKET_SMOKE_CASES,
)


EXPECTED_CASE_IDS = {
    "boba_large_half_sugar",
    "boba_typo",
    "bare_luwei",
    "listed_luwei_components",
    "chicken_bento_less_rice",
}


def test_fooddb_grokfast_live_diagnostic_case_matrix_is_plan_only() -> None:
    from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_matrix import (
        build_fooddb_grokfast_live_diagnostic_case_matrix,
    )

    artifact = build_fooddb_grokfast_live_diagnostic_case_matrix()

    assert (
        artifact["artifact_type"]
        == "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix_v1"
    )
    assert artifact["classification"] == "live_diagnostic_plan_only"
    assert artifact["track"] == "FDB"
    assert artifact["claim_scope"] == "fooddb_grokfast_packet_narrow_seam_case_matrix"
    assert artifact["live_provider_invoked"] is False
    assert artifact["live_websearch_invoked"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["full_self_use_gate"] is False
    assert artifact["websearch_exact_card_gate"] is False
    assert artifact["final_response_quality_gate"] is False
    assert artifact["production_readiness"] is False
    assert artifact["next_required_slice"] == "fooddb_modifier_seam_guard_repair"


def test_fooddb_grokfast_live_diagnostic_case_matrix_covers_existing_narrow_cases() -> None:
    from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_matrix import (
        build_fooddb_grokfast_live_diagnostic_case_matrix,
    )

    artifact = build_fooddb_grokfast_live_diagnostic_case_matrix()
    cases = artifact["cases"]

    assert {case["case_id"] for case in cases} == EXPECTED_CASE_IDS
    assert len(cases) == len(FOODDB_PACKET_SMOKE_CASES) == 5
    assert artifact["summary"]["case_count"] == 5
    assert artifact["summary"]["live_provider_case_count"] == 0
    assert artifact["summary"]["websearch_case_count"] == 0
    assert artifact["summary"]["ledger_mutation_allowed_case_count"] == 0
    assert artifact["summary"]["runtime_truth_allowed_case_count"] == 0
    assert artifact["summary"]["expected_runtime_evidence_in_packet_case_count"] == 4
    assert set(artifact["summary"]["case_ids"]) == EXPECTED_CASE_IDS

    expected_inputs = {case.case_id: case.raw_input for case in FOODDB_PACKET_SMOKE_CASES}
    expected_postures = {
        case.case_id: case.expected_behavior for case in FOODDB_PACKET_SMOKE_CASES
    }
    for case in cases:
        assert case["user_utterance"] == expected_inputs[case["case_id"]]
        assert case["expected_manager_posture"] == expected_postures[case["case_id"]]
        assert case["live_provider_invoked"] is False
        assert case["websearch_invoked"] is False
        assert case["ledger_mutation_allowed"] is False
        assert case["runtime_truth_allowed"] is False
        assert "invent_nutrition_source" in case["must_not_happen"]
        assert "intake_ledger_mutation" in case["must_not_happen"]
        assert "why_needed" in case and case["why_needed"]
        assert "known_gap_covered" in case and case["known_gap_covered"]
        assert "known_gap_not_covered" in case and case["known_gap_not_covered"]


def test_fooddb_grokfast_live_diagnostic_case_matrix_names_high_risk_boundaries() -> None:
    from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_matrix import (
        build_fooddb_grokfast_live_diagnostic_case_matrix,
    )

    artifact = build_fooddb_grokfast_live_diagnostic_case_matrix()
    by_id = {case["case_id"]: case for case in artifact["cases"]}

    assert by_id["boba_large_half_sugar"]["family"] == "modifier_guard"
    assert "unsupported_modifier_kcal_adjustment" in by_id["boba_large_half_sugar"][
        "must_not_happen"
    ]
    assert by_id["boba_typo"]["family"] == "alias_typo_recall"
    assert "typo_match_as_exact_truth" in by_id["boba_typo"]["must_not_happen"]
    assert by_id["bare_luwei"]["family"] == "bare_basket_followup"
    assert by_id["bare_luwei"]["runtime_truth_allowed"] is False
    assert by_id["bare_luwei"]["expected_runtime_evidence_in_packet"] is False
    assert "estimate_bare_basket" in by_id["bare_luwei"]["must_not_happen"]
    assert by_id["listed_luwei_components"]["family"] == "listed_basket_components"
    assert by_id["listed_luwei_components"]["expected_runtime_evidence_in_packet"] is True
    assert "estimate_unapproved_component" in by_id["listed_luwei_components"][
        "must_not_happen"
    ]
    assert by_id["chicken_bento_less_rice"]["family"] == "generic_meal_modifier_guard"
    assert "exact_bento_claim" in by_id["chicken_bento_less_rice"]["must_not_happen"]

    for case in artifact["cases"]:
        assert {
            "packet_type",
            "accepted_candidates",
            "rejected_candidates",
            "ambiguity_reason",
            "followup_hints",
            "confidence",
            "runtime_boundary",
        }.issubset(set(case["expected_packet_fields"]))


def test_fooddb_grokfast_live_diagnostic_case_matrix_declares_non_claims_and_later_gaps() -> None:
    from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_matrix import (
        build_fooddb_grokfast_live_diagnostic_case_matrix,
    )

    artifact = build_fooddb_grokfast_live_diagnostic_case_matrix()

    assert {
        "not_full_self_use_gate",
        "not_websearch_exact_card_gate",
        "not_final_response_quality_gate",
        "not_production_readiness",
        "not_private_self_use_approval",
        "no_live_provider_call",
        "no_live_websearch_call",
        "no_runtime_mutation",
    }.issubset(set(artifact["non_claims"]))
    assert artifact["later_expansion_candidates"]["generic_anchor"] == [
        "\u8336\u8449\u86cb",
        "\u725b\u8089\u9eb5",
    ]
    assert {
        "wrong_brand",
        "wrong_size",
        "official_missing_nutrition",
    }.issubset(set(artifact["later_expansion_candidates"]["exact_card_websearch"]))


def test_fooddb_grokfast_live_diagnostic_case_matrix_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_grokfast_live_diagnostic_case_matrix import (
        main,
    )

    output = tmp_path / "case_matrix.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert (
        artifact["artifact_type"]
        == "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix_v1"
    )
    assert artifact["summary"]["case_count"] == 5
    assert artifact["live_provider_invoked"] is False


def test_fooddb_grokfast_live_diagnostic_case_matrix_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/fooddb_grokfast_live_diagnostic_case_matrix.py"),
        Path("scripts/build_accurate_intake_fooddb_grokfast_live_diagnostic_case_matrix.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "requests.",
        "httpx.",
        "Tavily",
        "tavily",
        "allow_live",
        "run_live",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
