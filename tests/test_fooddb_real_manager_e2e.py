from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.application.fooddb_real_manager_e2e import (
    build_fooddb_real_manager_e2e,
)


def _artifact() -> dict:
    return build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )


def _case_by_id(artifact: dict, case_id: str) -> dict:
    return {case["case_id"]: case for case in artifact["cases"]}[case_id]


def test_real_fooddb_manager_e2e_consumes_full_packet_ready_records() -> None:
    artifact = build_fooddb_real_manager_e2e(approved_packet_ready_artifact=_artifact())

    assert artifact["artifact_type"] == "accurate_intake_fooddb_real_manager_e2e"
    assert artifact["claim_scope"] == "real_fooddb_packet_ready_manager_evidence_path"
    assert artifact["live_provider_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_attempted"] is False
    assert artifact["summary"]["case_count"] == 8
    assert artifact["summary"]["pass_count"] == 8
    assert artifact["summary"]["source_lane_counts"] == {
        "exact_item_card": 7,
        "generic_common_serving": 34,
        "listed_component": 34,
        "basket_family_semantic_only": 4,
    }

    exact = _case_by_id(artifact, "exact_macro_visible_chocolate_milk")
    exact_item = exact["manager_evidence_packet"]["evidence_items"][0]
    assert exact["status"] == "pass"
    assert exact_item["source_lane"] == "exact_item_card"
    assert exact_item["macro_visibility_status"] == "visible"
    assert exact_item["protein_g"] == 12
    assert exact_item["carbs_g"] == 48
    assert exact_item["fat_g"] == 6
    assert exact["final_response_basis"]["macro_basis"]["allowed_macro_claims"] == {
        "protein_g": 12,
        "carbs_g": 48,
        "fat_g": 6,
    }

    jiucai_he = _case_by_id(artifact, "exact_macro_visible_jiucai_he")
    jiucai_item = jiucai_he["manager_evidence_packet"]["evidence_items"][0]
    assert jiucai_he["status"] == "pass"
    assert jiucai_item["source_lane"] == "exact_item_card"
    assert jiucai_item["anchor_id"] == "exact_7eleven_jiucai_he_135g"
    assert jiucai_he["final_response_basis"]["macro_basis"]["allowed_macro_claims"] == {
        "protein_g": 8,
        "carbs_g": 40,
        "fat_g": 10,
    }


def test_real_fooddb_manager_e2e_preserves_macro_missing_and_basket_boundaries() -> None:
    artifact = build_fooddb_real_manager_e2e(approved_packet_ready_artifact=_artifact())

    fried_rice = _case_by_id(artifact, "generic_fried_rice_macro_hidden")
    fried_rice_item = fried_rice["manager_evidence_packet"]["evidence_items"][0]
    assert fried_rice["status"] == "pass"
    assert fried_rice_item["source_lane"] == "generic_common_serving"
    assert fried_rice_item["anchor_id"] == "staple_fried_rice"
    assert fried_rice_item["macro_visibility_status"] == "hidden_missing_source"
    assert fried_rice["final_response_basis"]["macro_basis"]["allowed_macro_claims"] == {}

    congee = _case_by_id(artifact, "generic_cantonese_congee_macro_hidden")
    congee_item = congee["manager_evidence_packet"]["evidence_items"][0]
    assert congee["status"] == "pass"
    assert congee_item["source_lane"] == "generic_common_serving"
    assert congee_item["anchor_id"] == "stable_base_cantonese_congee"
    assert congee_item["macro_visibility_status"] == "hidden_missing_source"
    assert congee["final_response_basis"]["macro_basis"]["allowed_macro_claims"] == {}

    boba = _case_by_id(artifact, "generic_macro_hidden_boba")
    boba_item = boba["manager_evidence_packet"]["evidence_items"][0]
    assert boba["status"] == "pass"
    assert boba_item["source_lane"] == "generic_common_serving"
    assert boba_item["macro_visibility_status"] == "hidden_missing_source"
    assert boba_item["protein_g"] is None
    assert boba["final_response_basis"]["macro_basis"]["allowed_macro_claims"] == {}
    assert "invented_macro" in boba["final_response_basis"]["forbidden_claims"]

    listed = _case_by_id(artifact, "listed_luwei_components")
    listed_items = listed["manager_evidence_packet"]["evidence_items"]
    assert listed["status"] == "pass"
    assert [item["source_lane"] for item in listed_items] == [
        "listed_component",
        "listed_component",
        "listed_component",
    ]
    assert all(item["macro_visibility_status"] == "hidden_missing_source" for item in listed_items)
    assert listed["final_response_basis"]["macro_basis"]["allowed_macro_claims"] == {}

    bare = _case_by_id(artifact, "bare_luwei_followup_only")
    packet = bare["manager_evidence_packet"]
    assert bare["status"] == "pass"
    assert packet["retrieval_boundary"] == "bare_basket_ask_followup_no_estimate"
    assert packet["evidence_items"] == []
    assert packet["followup_hints"]
    assert bare["final_response_basis"]["action_status"] == "ask_followup_no_mutation"


def test_real_fooddb_manager_e2e_cli_writes_roundtrippable_artifact(tmp_path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_real_manager_e2e import main

    output = tmp_path / "fooddb_real_manager_e2e.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_real_manager_e2e"
    assert artifact["summary"]["pass_count"] == 8
    assert artifact["live_provider_used"] is False
