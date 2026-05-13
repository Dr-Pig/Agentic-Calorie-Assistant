from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_drink_barley_black_tea_cup",
    "generic_drink_three_in_one_milk_tea_cup",
    "generic_drink_oolong_milk_tea_light_sugar_cup",
    "generic_drink_oolong_milk_tea_half_sugar_cup",
    "generic_breakfast_salty_soy_milk_bowl",
    "generic_staple_pork_potsticker_8pc",
    "generic_staple_pork_dumpling_10pc",
    "generic_staple_pork_chive_dumpling_10pc",
    "generic_dessert_unsweetened_tofu_pudding_bowl",
    "generic_bakery_hamburger_bun_one",
}


def test_generic_common_batch_004_loads_tfda_backed_breakfast_drinks() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id") or ""): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for anchor_id in BATCH_IDS:
        record = by_id[anchor_id]
        assert record["runtime_role"] == "common_serving_anchor"
        assert record["runtime_truth_allowed"] is True
        assert record["composition_posture"] == "estimable_with_refinement"
        assert record["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert record["source_refs"][0]["external_source_role"] == "source_evidence_only"
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "generic_range_estimate_with_refinement_not_exact"


def test_generic_common_batch_004_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    item = by_id["generic_drink_oolong_milk_tea_half_sugar_cup"]

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 374
    assert item["kcal_point"] == 312
    assert item["kcal_range"] == [230, 420]
    assert item["macro_visibility_status"] == "hidden_missing_source"
    assert item["macro_source_basis"] == "unknown"
    assert item["macro_confidence"] == "unknown"
