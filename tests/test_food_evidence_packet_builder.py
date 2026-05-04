from __future__ import annotations

from pathlib import Path

from app.nutrition.application.food_evidence_packet_builder import (
    build_food_evidence_recall_packet,
    is_compact_food_evidence_packet,
)
from app.nutrition.application.fooddb_retrieval_policy import retrieve_fooddb_candidates
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _records():
    return LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE).load_records()


def test_food_evidence_recall_packet_is_compact_and_manager_facing() -> None:
    retrieval = retrieve_fooddb_candidates("large boba", retrieval_records=_records())

    packet = build_food_evidence_recall_packet(
        packet_id="case:boba",
        raw_user_input="large boba",
        retrieval_result=retrieval,
    )

    assert packet["packet_type"] == "food_evidence_recall_packet_v1"
    assert packet["packet_id"] == "case:boba"
    assert packet["runtime_mutation_allowed"] is False
    assert packet["truth_selection_forbidden"] is True
    assert packet["raw_source_rows_included"] is False
    assert packet["candidate_only_records_included"] is False
    assert packet["full_fooddb_included"] is False

    item = packet["evidence_items"][0]
    assert item["anchor_id"] == "custom_drink_boba_milk_tea"
    assert item["ranking_reasons"]
    assert item["modifier_compatibility"] == {"cup_size": "compatible"}
    assert set(item["source_provenance"]) <= {"source_id", "source_file", "source_url"}
    assert "raw_row_hash" not in item["source_provenance"]
    assert set(item["approval_metadata"]) <= {
        "approval_mode",
        "approval_scope",
        "policy_version",
        "runtime_truth_allowed",
    }


def test_food_evidence_recall_packet_keeps_bare_basket_followup_boundary() -> None:
    retrieval = retrieve_fooddb_candidates(
        "\u6211\u5403\u6ef7\u5473",
        retrieval_records=_records(),
    )

    packet = build_food_evidence_recall_packet(
        packet_id="case:bare_luwei",
        raw_user_input="\u6211\u5403\u6ef7\u5473",
        retrieval_result=retrieval,
    )

    assert packet["retrieval_boundary"] == "bare_basket_ask_followup_no_estimate"
    assert packet["evidence_items"] == []
    assert packet["followup_hints"]
    assert packet["manager_may_use_for"] == [
        "grounded_food_evidence",
        "followup_or_uncertainty_decision",
        "disambiguation",
    ]
    assert "runtime_mutation" in packet["manager_must_not_use_for"]


def test_compact_packet_check_rejects_structural_raw_source_leakage() -> None:
    retrieval = retrieve_fooddb_candidates("large boba", retrieval_records=_records())
    packet = build_food_evidence_recall_packet(
        packet_id="case:boba",
        raw_user_input="large boba",
        retrieval_result=retrieval,
    )
    assert is_compact_food_evidence_packet(packet) is True

    packet["evidence_items"][0]["source_provenance"]["raw_row_hash"] = "leaked"
    assert is_compact_food_evidence_packet(packet) is False

    packet = build_food_evidence_recall_packet(
        packet_id="case:boba",
        raw_user_input="large boba",
        retrieval_result=retrieval,
    )
    packet["raw_source_rows"] = [{"source_id": "raw"}]
    assert is_compact_food_evidence_packet(packet) is False
