from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_ready_retort_rice_porridge_bowl",
    "generic_ready_brown_rice_porridge_bowl",
    "generic_ready_glutinous_rice_porridge_bowl",
    "generic_ready_black_glutinous_rice_porridge_bowl",
    "generic_pantry_rice_porridge_powder_serving",
    "generic_pantry_red_carrot_noodles_serving",
    "generic_pantry_spinach_noodles_serving",
    "generic_ready_frozen_egg_crepe_wrapper",
    "generic_bakery_coffin_bread_slab",
    "generic_ready_frozen_cream_croquette",
    "generic_pantry_sago_serving",
    "generic_side_taiwanese_kimchi_serving",
    "generic_side_soy_jube_serving",
    "generic_drink_soy_yogurt_milk_300ml",
    "generic_drink_dha_soy_milk_300ml",
    "generic_ready_frozen_squid_thick_soup_bowl",
    "generic_pantry_seafood_cream_soup_powder",
    "generic_pantry_vegetable_mushroom_cereal_serving",
    "generic_pantry_brown_rice_bran_serving",
    "generic_pantry_fortified_oat_milk_powder_serving",
}


def test_generic_common_batch_050_loads_pantry_ready_anchors() -> None:
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


def test_generic_common_batch_050_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 400
    expected = {
        "generic_ready_retort_rice_porridge_bowl": (183, [135, 240]),
        "generic_ready_frozen_egg_crepe_wrapper": (137, [95, 190]),
        "generic_drink_soy_yogurt_milk_300ml": (205, [150, 285]),
        "generic_pantry_vegetable_mushroom_cereal_serving": (155, [110, 220]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
