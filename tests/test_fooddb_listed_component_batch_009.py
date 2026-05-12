from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_shrimp_roll",
    "listed_item_fish_roll",
    "listed_item_shrimp_cake",
    "listed_item_clam_ball",
    "listed_item_pearl_ball",
    "listed_item_snow_snail_dumpling",
    "listed_item_fish_roe_roll",
    "listed_item_oil_noodle_portion",
    "listed_item_inari_tofu_skin_piece",
    "listed_item_crystal_bun",
}


def test_listed_component_batch_009_loads_component_only_tfda_records() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id") or ""): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for anchor_id in BATCH_IDS:
        record = by_id[anchor_id]
        assert record["runtime_role"] == "common_serving_anchor"
        assert record["runtime_truth_allowed"] is True
        assert record["composition_posture"] == "listed_item_component"
        assert record["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert record["source_refs"][0]["external_source_role"] == "source_evidence_only"
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_file"] == (
            "app/knowledge/tfda_per100g_source_evidence_tw.json"
        )
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "listed_component_only"
        assert record["kcal_range"][0] <= record["kcal_point"] <= record["kcal_range"][1]


def test_listed_component_batch_009_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    item = by_id["listed_item_shrimp_roll"]

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 154
    assert item["kcal_point"] == 46
    assert item["kcal_range"] == [35, 70]
    assert item["macro_visibility_status"] == "hidden_missing_source"
    assert item["macro_source_basis"] == "unknown"
    assert item["macro_confidence"] == "unknown"
