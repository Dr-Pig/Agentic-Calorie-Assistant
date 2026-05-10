from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.application.fooddb_retrieval_policy import retrieve_fooddb_candidates
from app.nutrition.application.fooddb_retrieval_records import (
    build_runtime_retrieval_records_from_packet_ready_artifact,
)


def _packet_ready_artifact() -> dict:
    return build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )


def test_packet_ready_artifact_builds_role_aware_retrieval_records() -> None:
    records = build_runtime_retrieval_records_from_packet_ready_artifact(_packet_ready_artifact())

    assert len(records) == 63
    lane_counts = {
        "exact_item_card": 0,
        "generic_common_serving": 0,
        "listed_component": 0,
    }
    for record in records:
        lane_counts[record.source_lane] += 1

    assert lane_counts == {
        "exact_item_card": 4,
        "generic_common_serving": 25,
        "listed_component": 34,
    }


def test_role_aware_retrieval_prefers_exact_packet_with_macro_fields() -> None:
    records = build_runtime_retrieval_records_from_packet_ready_artifact(_packet_ready_artifact())

    result = retrieve_fooddb_candidates("\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73", retrieval_records=records)

    assert result["truth_selection_forbidden"] is True
    candidate = result["accepted_candidates"][0]
    assert candidate["anchor_id"] == "exact_unified_chocolate_milk_400ml"
    assert candidate["source_lane"] == "exact_item_card"
    assert candidate["macro_visibility_status"] == "visible"
    assert candidate["protein_g"] == 12
    assert candidate["carbs_g"] == 48
    assert candidate["fat_g"] == 6
    assert "source_lane:exact_item_card" in candidate["ranking_reasons"]


def test_role_aware_retrieval_preserves_generic_and_listed_boundaries() -> None:
    records = build_runtime_retrieval_records_from_packet_ready_artifact(_packet_ready_artifact())

    drink = retrieve_fooddb_candidates("\u73cd\u73e0\u5976\u8336", retrieval_records=records)
    assert drink["accepted_candidates"][0]["anchor_id"] == "custom_drink_boba_milk_tea"
    assert drink["accepted_candidates"][0]["source_lane"] == "generic_common_serving"
    assert drink["accepted_candidates"][0]["macro_visibility_status"] == "hidden_missing_source"

    basket = retrieve_fooddb_candidates("\u6ef7\u5473 \u8c46\u5e72 \u6d77\u5e36", retrieval_records=records)
    assert basket["retrieval_boundary"] == "listed_basket_component_recall"
    assert [item["source_lane"] for item in basket["accepted_candidates"]] == [
        "listed_component",
        "listed_component",
    ]
    assert basket["runtime_mutation_allowed"] is False
