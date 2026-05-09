from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_manager_packet_smoke import (
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
)


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def _case_by_id(artifact: dict, case_id: str) -> dict:
    return {case["case_id"]: case for case in artifact["cases"]}[case_id]


def test_fooddb_manager_packet_smoke_builds_compact_packets_for_mvp_cases() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(_small_anchor_payload())
    artifact = build_fooddb_manager_packet_smoke(retrieval_records=records)

    assert artifact["artifact_type"] == "accurate_intake_fooddb_manager_packet_smoke"
    assert artifact["claim_scope"] == "deterministic_fooddb_manager_packet_smoke"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["runtime_packetizer_contract_changed"] is False
    assert artifact["manager_recall_packet_shape_changed"] is True
    assert artifact["packetizer_format_changed"] is False
    assert artifact["summary"]["case_count"] == 5
    assert artifact["summary"]["compact_packet_structural_leak_check"] == "enabled"

    for case in artifact["cases"]:
        packet = case["manager_evidence_packet"]
        assert packet["packet_type"] == "fooddb_manager_evidence_packet_v1"
        assert packet["raw_source_rows_included"] is False
        assert packet["candidate_only_records_included"] is False
        assert packet["full_fooddb_included"] is False
        assert packet["runtime_mutation_allowed"] is False
        assert packet["truth_selection_forbidden"] is True
        for item in packet["evidence_items"]:
            assert set(item) == {
                "anchor_id",
                "canonical_name",
                "query_component",
                "match_path",
                "confidence",
                "requires_manager_disambiguation",
                "runtime_role",
                "runtime_truth_allowed",
                "kcal_point",
                "kcal_range",
                "serving_basis",
                "portion_basis",
                "runtime_usage_boundary",
                "followup_hints",
                "source_provenance",
                "approval_metadata",
                "modifier_compatibility",
                "ranking_reasons",
            }
            assert item["runtime_truth_allowed"] is True
            assert item["source_provenance"]["source_id"]
            assert "raw_row_hash" not in item["source_provenance"]
            assert item["approval_metadata"]["runtime_truth_allowed"] is True
            assert isinstance(item["ranking_reasons"], list)


def test_fooddb_manager_packet_smoke_classifies_boba_basket_and_bento_cases() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(_small_anchor_payload())
    artifact = build_fooddb_manager_packet_smoke(retrieval_records=records)

    boba = _case_by_id(artifact, "boba_large_half_sugar")
    assert boba["manager_expected_behavior"] == "estimate_from_packet_with_uncertainty"
    assert boba["manager_evidence_packet"]["modifier_hints"] == {
        "cup_size": "large",
        "sugar_level": "half_sugar",
    }
    assert [item["anchor_id"] for item in boba["manager_evidence_packet"]["evidence_items"]] == [
        "custom_drink_boba_milk_tea"
    ]

    typo = _case_by_id(artifact, "boba_typo")
    assert typo["manager_expected_behavior"] == "estimate_or_confirm_from_fuzzy_packet"
    assert typo["manager_evidence_packet"]["evidence_items"][0]["match_path"] == "fuzzy_alias"
    assert typo["manager_evidence_packet"]["evidence_items"][0]["requires_manager_disambiguation"] is True

    bare = _case_by_id(artifact, "bare_luwei")
    assert bare["manager_expected_behavior"] == "ask_followup_no_mutation"
    assert bare["manager_evidence_packet"]["retrieval_boundary"] == "bare_basket_ask_followup_no_estimate"
    assert bare["manager_evidence_packet"]["evidence_items"] == []
    assert bare["manager_evidence_packet"]["followup_hints"]

    listed = _case_by_id(artifact, "listed_luwei_components")
    assert listed["manager_expected_behavior"] == "estimate_listed_components_only"
    assert [item["anchor_id"] for item in listed["manager_evidence_packet"]["evidence_items"]] == [
        "listed_item_kelp",
        "listed_item_meatball",
        "listed_item_tofu_dried",
    ]

    bento = _case_by_id(artifact, "chicken_bento_less_rice")
    assert bento["manager_expected_behavior"] == "generic_range_estimate_with_followup_hints"
    assert [item["anchor_id"] for item in bento["manager_evidence_packet"]["evidence_items"]] == [
        "generic_meal_chicken_bento"
    ]


def test_fooddb_manager_packet_smoke_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_approved_packet_ready_fooddb_artifact import (
        main as build_approved_artifact,
    )
    from scripts.build_accurate_intake_fooddb_manager_packet_smoke import main

    approved = tmp_path / "approved_packet_ready_fooddb.json"
    output = tmp_path / "fooddb_packet_smoke.json"

    assert build_approved_artifact(["--output", str(approved)]) == 0
    assert main(["--approved-packet-ready-artifact", str(approved), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_manager_packet_smoke"
    assert artifact["summary"]["compact_packet_pass_count"] == 5
    assert artifact["summary"]["approved_packet_ready_case_count"] == 3


def test_fooddb_manager_packet_smoke_consumes_approved_packet_ready_triad() -> None:
    records = build_runtime_retrieval_records_from_small_anchor_payload(_small_anchor_payload())
    approved_artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_min1.json"
    )

    artifact = build_fooddb_manager_packet_smoke(
        retrieval_records=records,
        approved_packet_ready_artifact=approved_artifact,
    )

    assert artifact["summary"]["approved_packet_ready_case_count"] == 3
    assert artifact["summary"]["approved_packet_ready_lane_counts"] == {
        "exact_item_card": 1,
        "generic_common_serving": 1,
        "listed_component": 1,
    }
    by_lane = {
        case["source_lane"]: case
        for case in artifact["approved_packet_ready_cases"]
    }
    exact = by_lane["exact_item_card"]
    assert exact["manager_evidence_packet"]["runtime_mutation_allowed"] is False
    assert exact["tool_result_envelope"]["runtime_mutation_allowed"] is False
    assert "runtime_mutation" in exact["tool_result_envelope"]["manager_must_not_use_for"]
    assert "inventing_macro" in exact["tool_result_envelope"]["manager_must_not_use_for"]
    assert exact["final_response_basis"]["macro_basis"] == {
        "macro_visibility_status": "visible",
        "allowed_macro_claims": {
            "protein_g": 12,
            "carbs_g": 48,
            "fat_g": 6,
        },
    }

    generic = by_lane["generic_common_serving"]
    assert generic["manager_evidence_packet"]["evidence_items"][0]["kcal_range"] == [650, 900]
    assert generic["manager_evidence_packet"]["evidence_items"][0]["protein_g"] is None
    assert generic["final_response_basis"]["macro_basis"] == {
        "macro_visibility_status": "hidden_missing_source",
        "allowed_macro_claims": {},
    }
    assert "invented_macro" in generic["final_response_basis"]["forbidden_claims"]

    component = by_lane["listed_component"]
    assert component["manager_evidence_packet"]["evidence_items"][0]["kcal_range"] == [70, 120]
    assert component["manager_evidence_packet"]["evidence_items"][0]["fat_g"] is None
    assert component["final_response_basis"]["macro_basis"] == {
        "macro_visibility_status": "hidden_missing_source",
        "allowed_macro_claims": {},
    }
    assert component["final_response_basis"]["packet_is_not_mutation_authority"] is True
