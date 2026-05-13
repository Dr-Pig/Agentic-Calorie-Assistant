from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_carp_100g",
    "listed_item_atlantic_salmon_skinless_100g",
    "listed_item_atlantic_salmon_taiwan_farmed_100g",
    "listed_item_atlantic_salmon_steak_middle_100g",
    "listed_item_white_cutlassfish_100g",
    "listed_item_raw_mackerel_100g",
    "listed_item_raw_taiwan_tilapia_fillet_100g",
    "listed_item_boiled_taiwan_tilapia_fillet_100g",
    "listed_item_panfried_taiwan_tilapia_fillet_100g",
    "listed_item_steamed_taiwan_tilapia_fillet_100g",
    "listed_item_grass_shrimp_100g",
    "listed_item_blue_shrimp_100g",
    "listed_item_red_shrimp_meat_100g",
    "listed_item_bighead_shrimp_meat_100g",
    "listed_item_ming_shrimp_meat_100g",
    "listed_item_green_mussel_100g",
    "listed_item_hard_clam_100g",
    "listed_item_octopus_100g",
    "listed_item_taiwan_squid_100g",
    "listed_item_spear_squid_100g",
}


def test_listed_component_batch_031_loads_fish_and_seafood_components() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id") or ""): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for anchor_id in BATCH_IDS:
        record = by_id[anchor_id]
        assert record["runtime_role"] == "common_serving_anchor"
        assert record["runtime_truth_allowed"] is True
        assert record["composition_posture"] == "listed_item_component"
        assert record["serving_basis"] == "common_serving"
        assert record["portion_basis"]["portion_grams"] == 100
        assert record["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert record["source_refs"][0]["external_source_role"] == "source_evidence_only"
        assert record["source_refs"][0]["source_id"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_url"] == "https://data.gov.tw/dataset/8543"
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "listed_component_only"
        assert record["kcal_range"][0] <= record["kcal_point"] <= record["kcal_range"][1]


def test_listed_component_batch_031_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 314
    expected = {
        "listed_item_atlantic_salmon_skinless_100g": (221, [165, 310]),
        "listed_item_white_cutlassfish_100g": (102, [75, 145]),
        "listed_item_panfried_taiwan_tilapia_fillet_100g": (162, [120, 230]),
        "listed_item_octopus_100g": (61, [45, 85]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
