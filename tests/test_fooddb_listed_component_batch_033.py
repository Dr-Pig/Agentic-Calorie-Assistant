from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_chicken_sausage_small_one",
    "listed_item_chicken_floss_30g",
    "listed_item_pork_aspic_100g",
    "listed_item_fish_paste_100g",
    "listed_item_mackerel_fish_floss_30g",
    "listed_item_fish_floss_30g",
    "listed_item_duck_shang_100g",
    "listed_item_tea_duck_100g",
    "listed_item_cooked_goose_leg_meat_100g",
    "listed_modifier_beef_sauce_20g",
    "listed_modifier_beef_steak_sauce_20g",
    "listed_modifier_lamb_stew_sauce_30g",
    "listed_modifier_pork_rib_sauce_20g",
    "listed_modifier_fried_chicken_powder_15g",
    "listed_modifier_steamed_pork_powder_15g",
    "listed_item_duck_egg_one",
    "listed_item_red_duck_egg_one",
    "listed_item_duck_egg_white_one",
    "listed_item_duck_egg_yolk_one",
    "listed_item_goose_egg_one",
}


def test_listed_component_batch_033_loads_protein_and_modifier_components() -> None:
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


def test_listed_component_batch_033_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 332
    expected = {
        "listed_item_chicken_sausage_small_one": (160, [115, 230]),
        "listed_item_duck_shang_100g": (304, [230, 425]),
        "listed_modifier_fried_chicken_powder_15g": (48, [35, 70]),
        "listed_item_duck_egg_one": (131, [95, 185]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
