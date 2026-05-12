from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_milkfish_belly_100g",
    "listed_item_salmon_sashimi_100g",
    "listed_item_salmon_belly_100g",
    "listed_item_white_salmon_slice_100g",
    "listed_item_red_salmon_slice_100g",
    "listed_item_sweetfish_100g",
    "listed_item_silver_fish_100g",
    "listed_item_crab_leg_meat_100g",
    "listed_item_snail_meat_100g",
    "listed_item_char_siu_100g",
    "listed_item_braised_pork_elbow_100g",
    "listed_item_preserved_pork_belly_100g",
    "listed_item_preserved_pork_leg_100g",
    "listed_item_smoked_pork_liver_100g",
    "listed_item_spicy_beef_jerky_30g",
    "listed_item_beef_sausage_one",
    "listed_item_konjac_garlic_sausage_one",
    "listed_item_sweet_sour_pork_100g",
    "listed_item_tuna_patty_100g",
    "listed_item_scallop_crisp_100g",
}


def test_listed_component_batch_026_loads_seafood_and_protein_components() -> None:
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


def test_listed_component_batch_026_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 254
    expected = {
        "listed_item_milkfish_belly_100g": (342, [260, 470]),
        "listed_item_salmon_sashimi_100g": (222, [170, 310]),
        "listed_item_spicy_beef_jerky_30g": (100, [70, 150]),
        "listed_item_beef_sausage_one": (149, [110, 220]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
