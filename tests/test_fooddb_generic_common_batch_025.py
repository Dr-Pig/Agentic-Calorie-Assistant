from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_staple_puli_rice_noodle_serving",
    "generic_staple_thin_rice_noodle_serving",
    "generic_staple_zhuoshui_rice_noodle_serving",
    "generic_staple_long_wheat_noodle_serving",
    "generic_staple_red_wheat_noodle_serving",
    "generic_noodle_chicken_thread_noodle_pack",
    "generic_noodle_pot_yi_noodle_pack",
    "generic_noodle_dry_egg_noodle_serving",
    "generic_noodle_frozen_udon_serving",
    "generic_dim_sum_flower_roll_one",
    "generic_dim_sum_milk_custard_silver_roll_one",
    "generic_staple_beef_pie_one",
    "generic_staple_pork_pie_one",
    "generic_dessert_sweet_fermented_rice_bowl",
    "generic_dessert_purple_fermented_rice_bowl",
    "generic_snack_lemon_dried_fruit_serving",
    "generic_drink_oat_milk_cup",
    "generic_drink_three_in_one_coffee_packet",
    "generic_drink_papaya_milk_cup",
    "generic_drink_unsweetened_fresh_milk_tea_cup",
}


def test_generic_common_batch_025_loads_tfda_backed_everyday_staples() -> None:
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
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_file"] == (
            "app/knowledge/tfda_per100g_source_evidence_tw.json"
        )
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "generic_range_estimate_with_refinement_not_exact"
        assert record["kcal_range"][0] <= record["kcal_point"] <= record["kcal_range"][1]


def test_generic_common_batch_025_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 294
    expected = {
        "generic_noodle_frozen_udon_serving": (251, [190, 340]),
        "generic_staple_beef_pie_one": (334, [260, 460]),
        "generic_drink_papaya_milk_cup": (206, [150, 300]),
        "generic_drink_unsweetened_fresh_milk_tea_cup": (133, [90, 210]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
