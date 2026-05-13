from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_taiwan_tilapia_fillet_100g",
    "listed_item_grilled_taiwan_tilapia_fillet_100g",
    "listed_item_long_grilled_taiwan_tilapia_fillet_100g",
    "listed_item_microwaved_taiwan_tilapia_fillet_100g",
    "listed_item_bigeye_scad_100g",
    "listed_item_bigeye_tuna_100g",
    "listed_item_taiwan_spanish_mackerel_100g",
    "listed_item_cod_fillet_100g",
    "listed_item_dried_small_fish_20g",
    "listed_item_giant_freshwater_prawn_100g",
    "listed_item_whiteleg_shrimp_meat_100g",
    "listed_item_fantail_shrimp_meat_100g",
    "listed_item_red_shrimp_meat_100g",
    "listed_item_red_crab_100g",
    "listed_item_oyster_100g",
    "listed_item_clam_meat_100g",
    "listed_item_argentine_squid_100g",
    "listed_item_small_squid_100g",
    "listed_item_dried_squid_20g",
    "listed_item_dried_scallop_20g",
}


def test_listed_component_batch_044_loads_seafood_protein_components() -> None:
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


def test_listed_component_batch_044_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 314
    expected = {
        "listed_item_taiwan_tilapia_fillet_100g": (109, [80, 155]),
        "listed_item_taiwan_spanish_mackerel_100g": (180, [135, 250]),
        "listed_item_whiteleg_shrimp_meat_100g": (73, [50, 110]),
        "listed_item_dried_scallop_20g": (48, [35, 70]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
