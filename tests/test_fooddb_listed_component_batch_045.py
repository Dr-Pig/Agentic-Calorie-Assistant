from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_canned_corn_sauce_100g",
    "listed_item_preserved_bamboo_shoot_100g",
    "listed_item_dried_cabbage_30g",
    "listed_modifier_douchi_20g",
    "listed_modifier_spicy_fermented_tofu_20g",
    "listed_item_natto_100g",
    "listed_item_salted_crispy_fava_beans_30g",
    "listed_item_garlic_almonds_30g",
    "listed_item_honey_pine_nuts_20g",
    "listed_item_sweet_walnuts_20g",
    "listed_item_honey_cashews_30g",
    "listed_item_cinnamon_watermelon_seeds_30g",
    "listed_item_soy_sauce_watermelon_seeds_30g",
    "listed_item_licorice_sunflower_seeds_30g",
    "listed_item_salted_sunflower_seeds_30g",
    "listed_item_candied_lotus_seeds_30g",
    "listed_item_smoked_shark_100g",
    "listed_item_processed_conch_100g",
}


def test_listed_component_batch_045_loads_side_modifier_components() -> None:
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


def test_listed_component_batch_045_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 332
    expected = {
        "listed_item_canned_corn_sauce_100g": (62, [45, 90]),
        "listed_modifier_douchi_20g": (43, [30, 65]),
        "listed_item_garlic_almonds_30g": (189, [140, 240]),
        "listed_item_processed_conch_100g": (105, [75, 150]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
