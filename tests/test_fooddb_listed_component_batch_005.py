from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_swordfish_ball",
    "listed_item_cod_fish_ball",
    "listed_item_spiced_tofu_cube",
    "listed_item_shacha_tofu_slice",
    "listed_item_shredded_dried_tofu",
    "listed_item_canned_mushroom_seitan",
    "listed_item_squid_ring",
    "listed_item_soaked_squid",
    "listed_item_tofu_skin_sheet",
    "listed_item_small_triangle_oil_tofu",
}


def test_listed_component_batch_005_loads_component_only_tfda_records() -> None:
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
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "listed_component_only"


def test_listed_component_batch_005_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    item = by_id["listed_item_squid_ring"]

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 350
    assert item["kcal_point"] == 43
    assert item["kcal_range"] == [30, 70]
    assert item["macro_visibility_status"] == "hidden_missing_source"
    assert item["macro_source_basis"] == "unknown"
    assert item["macro_confidence"] == "unknown"
