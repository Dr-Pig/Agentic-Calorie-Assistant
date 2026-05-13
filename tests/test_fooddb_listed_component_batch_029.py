from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_onsen_egg_one",
    "listed_item_boiled_chicken_egg_one",
    "listed_item_boiled_egg_white_one",
    "listed_item_boiled_egg_yolk_one",
    "listed_item_commercial_tea_egg_one",
    "listed_item_century_egg_one",
    "listed_item_braised_egg_one",
    "listed_item_commercial_braised_egg_one",
    "listed_item_iron_egg_one",
    "listed_item_poached_egg_no_oil_one",
    "listed_item_fried_egg_with_oil_one",
    "listed_item_steamed_egg_cup",
    "listed_modifier_shacha_powder_15g",
    "listed_modifier_curry_cube_20g",
    "listed_modifier_fried_shallot_10g",
    "listed_modifier_coconut_milk_30g",
    "listed_modifier_garlic_crisp_10g",
    "listed_modifier_bonito_powder_5g",
    "listed_modifier_pork_broth_cube_10g",
    "listed_modifier_chicken_broth_cube_10g",
}


def test_listed_component_batch_029_loads_egg_and_hotpot_modifiers() -> None:
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


def test_listed_component_batch_029_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 294
    expected = {
        "listed_item_onsen_egg_one": (76, [55, 105]),
        "listed_item_braised_egg_one": (101, [75, 145]),
        "listed_modifier_curry_cube_20g": (101, [70, 150]),
        "listed_modifier_fried_shallot_10g": (49, [35, 70]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
