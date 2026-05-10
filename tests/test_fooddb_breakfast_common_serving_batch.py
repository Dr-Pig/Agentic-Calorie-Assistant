from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)


BREAKFAST_COMMON_SERVING_IDS = {
    "breakfast_staple_scallion_pancake",
    "breakfast_staple_radish_cake",
    "breakfast_staple_steamed_bun",
    "breakfast_staple_xiaolongbao",
    "breakfast_staple_ham_egg_sandwich",
}

EXPECTED_CANONICAL_NAMES = {
    "breakfast_staple_scallion_pancake": "\u8525\u6cb9\u9905",
    "breakfast_staple_radish_cake": "\u863f\u8514\u7cd5",
    "breakfast_staple_steamed_bun": "\u9945\u982d",
    "breakfast_staple_xiaolongbao": "\u5c0f\u7c60\u5305",
    "breakfast_staple_ham_egg_sandwich": "\u706b\u817f\u86cb\u4e09\u660e\u6cbb",
}


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def test_breakfast_common_serving_batch_is_packet_ready_without_macro_guessing() -> None:
    payload = _small_anchor_payload()
    anchors = {
        anchor.get("anchor_id"): anchor
        for anchor in payload["anchors"]
        if isinstance(anchor, dict) and anchor.get("anchor_id")
    }

    assert BREAKFAST_COMMON_SERVING_IDS.issubset(anchors)

    for anchor_id in BREAKFAST_COMMON_SERVING_IDS:
        anchor = anchors[anchor_id]
        assert anchor["canonical_name"] == EXPECTED_CANONICAL_NAMES[anchor_id]
        assert "?" not in anchor["canonical_name"]
        assert all("?" not in alias for alias in anchor["aliases"])
        assert anchor["record_kind"] == "generic_anchor"
        assert anchor["runtime_role"] == "common_serving_anchor"
        assert anchor["runtime_truth_allowed"] is True
        assert anchor["runtime_usage_boundary"] == "generic_breakfast_staple_range_estimate_with_refinement"
        assert anchor["kcal_range"][0] <= anchor["kcal_point"] <= anchor["kcal_range"][1]
        assert anchor["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert anchor["source_refs"][0]["serving_basis"] == "per_100g"
        assert anchor["source_refs"][0]["external_source_role"] == "source_evidence_only"
        assert anchor["approval_metadata"]["approval_scope"] == (
            "tfda_breakfast_common_serving_batch"
        )
        assert anchor["kcal_basis"]["external_source_role"] == (
            "source_evidence_only_not_common_serving"
        )

    packet_ready = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/accurate_intake_approved_packet_ready_fooddb_artifact.json",
        selection_profile="full_current_shell",
    )
    items = {
        item["item_id"]: item
        for item in packet_ready["packet_ready_items"]
        if item.get("item_id") in BREAKFAST_COMMON_SERVING_IDS
    }

    assert set(items) == BREAKFAST_COMMON_SERVING_IDS
    assert packet_ready["summary"]["source_anchor_count"] == 72
    assert packet_ready["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 34
    for item in items.values():
        assert item["source_lane"] == "generic_common_serving"
        assert item["protein_g"] is None
        assert item["carbs_g"] is None
        assert item["fat_g"] is None
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
