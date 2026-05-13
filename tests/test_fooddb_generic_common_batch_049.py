from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_snack_sesame_egg_roll_serving",
    "generic_snack_instant_noodle_crisps_pack",
    "generic_snack_peanut_milk_chocolate_serving",
    "generic_snack_hazelnut_milk_chocolate_serving",
    "generic_snack_sugar_coated_chocolate_serving",
    "generic_snack_white_chocolate_candy_serving",
    "generic_snack_dark_chocolate_85_serving",
    "generic_snack_black_sesame_candy_piece",
    "generic_snack_milk_soft_candy_serving",
    "generic_snack_chocolate_milk_soft_candy_serving",
    "generic_snack_toffee_serving",
    "generic_snack_lotus_root_candy_serving",
    "generic_snack_loquat_candy_serving",
    "generic_snack_bitter_tea_candy_serving",
    "generic_snack_ginger_candy_serving",
    "generic_snack_chocolate_filled_candy_serving",
    "generic_snack_red_bean_ball_piece",
    "generic_snack_green_bean_ball_piece",
    "generic_snack_marshmallow_serving",
    "generic_snack_sweet_potato_preserve_serving",
}


def test_generic_common_batch_049_loads_snack_sweets_anchors() -> None:
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


def test_generic_common_batch_049_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 334
    expected = {
        "generic_snack_sesame_egg_roll_serving": (164, [120, 220]),
        "generic_snack_instant_noodle_crisps_pack": (238, [170, 310]),
        "generic_snack_dark_chocolate_85_serving": (146, [105, 205]),
        "generic_snack_sweet_potato_preserve_serving": (135, [95, 190]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
