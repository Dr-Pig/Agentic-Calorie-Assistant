from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_cabbage_100g",
    "listed_item_bok_choy_100g",
    "listed_item_water_spinach_100g",
    "listed_item_broccoli_100g",
    "listed_item_baby_corn_100g",
    "listed_item_enoki_mushroom_100g",
    "listed_item_king_oyster_mushroom_100g",
    "listed_item_fresh_shiitake_100g",
    "listed_item_mung_bean_sprouts_100g",
    "listed_item_pork_blood_100g",
    "listed_item_chicken_breast_100g",
    "listed_item_skinless_chicken_thigh_100g",
    "listed_item_shrimp_meat_100g",
    "listed_item_tilapia_fillet_100g",
    "listed_item_salmon_slice_100g",
    "listed_item_winter_melon_150g",
    "listed_item_spinach_100g",
    "listed_item_romaine_lettuce_100g",
    "listed_item_sweet_potato_leaves_100g",
    "listed_item_green_bell_pepper_100g",
}


def test_listed_component_batch_017_loads_daily_basket_components() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id") or ""): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for anchor_id in BATCH_IDS:
        record = by_id[anchor_id]
        assert record["runtime_role"] == "common_serving_anchor"
        assert record["runtime_truth_allowed"] is True
        assert record["composition_posture"] == "listed_item_component"
        assert record["serving_basis"] == "common_serving"
        assert record["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert record["source_refs"][0]["external_source_role"] == "source_evidence_only"
        assert record["source_refs"][0]["source_id"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_url"] == "https://data.gov.tw/dataset/8543"
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "listed_component_only"
        assert record["kcal_range"][0] <= record["kcal_point"] <= record["kcal_range"][1]


def test_listed_component_batch_017_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    item = by_id["listed_item_chicken_breast_100g"]

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 114
    assert item["kcal_point"] == 119
    assert item["kcal_range"] == [90, 160]
    assert item["macro_visibility_status"] == "hidden_missing_source"
    assert item["macro_source_basis"] == "unknown"
    assert item["macro_confidence"] == "unknown"
