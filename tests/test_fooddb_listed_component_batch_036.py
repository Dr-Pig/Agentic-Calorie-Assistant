from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_five_spice_dried_tofu_100g",
    "listed_item_crab_stick_50g",
    "listed_item_milkfish_ball_100g",
    "listed_item_clam_ball_100g",
    "listed_item_swordfish_ball_100g",
    "listed_item_cod_ball_100g",
    "listed_item_shrimp_ball_100g",
    "listed_item_egg_dumpling_3pc",
    "listed_item_fish_dumpling_3pc",
    "listed_item_yan_dumpling_3pc",
    "listed_item_bamboo_shoot_slices_100g",
    "listed_item_canned_corn_kernels_80g",
    "listed_item_pickled_cucumber_50g",
    "listed_item_peanut_gluten_can_60g",
    "listed_item_mushroom_gluten_can_60g",
    "listed_item_bamboo_shoot_tuna_can_80g",
    "listed_item_sauerkraut_50g",
    "listed_item_golden_kimchi_50g",
    "listed_item_korean_kimchi_50g",
    "listed_item_mushroom_dumpling_3pc",
}


def test_listed_component_batch_036_loads_hotpot_and_basket_components() -> None:
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


def test_listed_component_batch_036_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 332
    expected = {
        "listed_item_five_spice_dried_tofu_100g": (192, [140, 270]),
        "listed_item_crab_stick_50g": (59, [40, 90]),
        "listed_item_milkfish_ball_100g": (203, [150, 285]),
        "listed_item_golden_kimchi_50g": (54, [35, 80]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
