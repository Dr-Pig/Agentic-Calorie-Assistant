from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_tea_egg_one",
    "listed_item_tea_egg_overnight_one",
    "listed_item_steamed_egg_microwave_cup",
    "listed_item_braised_egg_overnight_one",
    "listed_item_chicken_century_egg_one",
    "listed_item_duck_century_egg_one",
    "listed_item_duck_salted_egg_one",
    "listed_item_poached_egg_one",
    "listed_item_fried_egg_no_oil_one",
    "listed_item_scrambled_egg_serving",
    "listed_item_steamed_egg_cup",
    "listed_item_egg_white_100g",
    "listed_item_egg_yolk_one",
    "listed_item_spring_roll_wrapper_2pc",
    "listed_item_wonton_wrapper_10pc",
    "listed_item_dumpling_wrapper_10pc",
    "listed_item_preserved_mustard_greens_100g",
    "listed_item_egg_tofu_100g",
    "listed_item_frozen_onion_rings_100g",
    "listed_item_frozen_vegetarian_dumplings_5pc",
}


def test_listed_component_batch_043_loads_egg_protein_side_components() -> None:
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


def test_listed_component_batch_043_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 314
    expected = {
        "listed_item_tea_egg_one": (80, [65, 100]),
        "listed_item_steamed_egg_microwave_cup": (123, [85, 160]),
        "listed_item_frozen_onion_rings_100g": (276, [210, 350]),
        "listed_item_frozen_vegetarian_dumplings_5pc": (255, [185, 335]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
