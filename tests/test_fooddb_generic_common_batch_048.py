from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_drink_black_plum_juice_300ml",
    "generic_drink_black_date_tea_500ml",
    "generic_drink_starfruit_juice_300ml",
    "generic_drink_grapefruit_juice_300ml",
    "generic_drink_pineapple_juice_300ml",
    "generic_drink_lemon_juice_300ml",
    "generic_drink_apple_juice_300ml",
    "generic_drink_mixed_fruit_vinegar_300ml",
    "generic_drink_low_sugar_sarsaparilla_can",
    "generic_drink_mixed_soda_can",
    "generic_drink_vitamin_soda_can",
    "generic_drink_unsweetened_coffee_can",
    "generic_drink_apple_black_tea_500ml",
    "generic_drink_oolong_tea_half_sugar_700ml",
    "generic_drink_oolong_tea_full_sugar_700ml",
    "generic_drink_oolong_milk_tea_full_sugar_700ml",
    "generic_drink_boba_milk_tea_half_sugar_700ml",
    "generic_drink_boba_milk_tea_full_sugar_700ml",
    "generic_drink_jasmine_tea_500ml",
    "generic_drink_chrysanthemum_tea_500ml",
}


def test_generic_common_batch_048_loads_drink_variety_anchors() -> None:
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


def test_generic_common_batch_048_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 374
    expected = {
        "generic_drink_black_plum_juice_300ml": (172, [120, 230]),
        "generic_drink_oolong_tea_half_sugar_700ml": (148, [90, 240]),
        "generic_drink_boba_milk_tea_half_sugar_700ml": (585, [430, 760]),
        "generic_drink_unsweetened_coffee_can": (13, [0, 35]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
