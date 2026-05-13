from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_frozen_silver_roll_custard_one",
    "listed_item_frozen_shumai_3pc",
    "listed_item_frozen_crystal_bun_one",
    "listed_item_frozen_crystal_dumpling_3pc",
    "listed_item_frozen_vegetarian_chicken_nuggets_100g",
    "listed_item_frozen_small_sausage_3pc",
    "listed_item_frozen_beef_patty_one",
    "listed_item_frozen_chicken_nuggets_100g",
    "listed_item_frozen_squid_steak_one",
    "listed_item_frozen_tuna_cutlet_one",
    "listed_item_frozen_shrimp_pancake_one",
    "listed_item_frozen_scallop_crisp_one",
    "listed_item_frozen_squid_chunks_100g",
    "listed_item_frozen_swordfish_chunks_100g",
    "listed_item_frozen_oyster_roll_one",
    "listed_item_frozen_fish_roll_one",
    "listed_item_frozen_shrimp_roll_one",
    "listed_item_frozen_squid_rings_100g",
    "listed_item_frozen_squid_dumpling_3pc",
    "listed_item_frozen_squid_paste_100g",
}


def test_listed_component_batch_040_loads_frozen_components() -> None:
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


def test_listed_component_batch_040_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 350
    expected = {
        "listed_item_frozen_shumai_3pc": (165, [120, 235]),
        "listed_item_frozen_chicken_nuggets_100g": (228, [165, 320]),
        "listed_item_frozen_shrimp_roll_one": (122, [85, 175]),
        "listed_item_frozen_squid_rings_100g": (143, [105, 205]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
