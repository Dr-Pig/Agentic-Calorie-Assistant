from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_pastry_taro_yolk_puff_one",
    "generic_pastry_turnip_puff_one",
    "generic_snack_milao_serving",
    "generic_bakery_croissant_one",
    "generic_dessert_chocolate_cream_puff_one",
    "generic_dessert_portuguese_egg_tart_one",
    "generic_dessert_tiramisu_slice",
    "generic_dessert_black_forest_cake_slice",
    "generic_bakery_whole_grain_toast_two_slices",
    "generic_bakery_red_bean_toast_slice",
    "generic_dessert_sugar_donut_one",
    "generic_dessert_coffee_jelly_cup",
    "generic_dessert_fruit_jelly_cup",
    "generic_dessert_baked_pudding_cup",
    "generic_dessert_yellow_pudding_cup",
    "generic_drink_orange_juice_100pct_300ml",
    "generic_drink_apple_juice_100pct_300ml",
    "generic_drink_cola_can",
    "generic_drink_low_calorie_cola_can",
    "generic_drink_americano_unsweetened_360ml",
}


def test_generic_common_batch_041_loads_dessert_snack_drink_anchors() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id") or ""): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for anchor_id in BATCH_IDS:
        record = by_id[anchor_id]
        assert record["runtime_role"] == "common_serving_anchor"
        assert record["runtime_truth_allowed"] is True
        assert record["composition_posture"] == "estimable_with_refinement"
        assert record["serving_basis"] == "common_serving"
        assert record["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert record["source_refs"][0]["external_source_role"] == "source_evidence_only"
        assert record["source_refs"][0]["source_id"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_url"] == "https://data.gov.tw/dataset/8543"
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "generic_range_estimate_with_refinement_not_exact"
        assert record["kcal_range"][0] <= record["kcal_point"] <= record["kcal_range"][1]


def test_generic_common_batch_041_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 400
    expected = {
        "generic_bakery_croissant_one": (314, [245, 390]),
        "generic_dessert_portuguese_egg_tart_one": (224, [165, 300]),
        "generic_drink_cola_can": (169, [130, 215]),
        "generic_drink_americano_unsweetened_360ml": (9, [0, 20]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
