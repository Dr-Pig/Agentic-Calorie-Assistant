from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_sauce_light_soy_sauce_tbsp",
    "generic_sauce_low_sodium_soy_sauce_tbsp",
    "generic_sauce_low_sodium_high_iron_soy_sauce_tbsp",
    "generic_sauce_soy_paste_tbsp",
    "generic_sauce_black_bean_soy_paste_tbsp",
    "generic_sauce_scallop_sauce_tbsp",
    "generic_sauce_italian_cheese_sauce_serving",
    "generic_sauce_zhajiang_serving",
    "generic_sauce_vegetarian_zhajiang_serving",
    "generic_sauce_instant_sesame_noodle_packet",
    "generic_sauce_tomato_pasta_sauce_serving",
    "generic_sauce_five_flavor_sauce_serving",
    "generic_sauce_satay_tbsp",
    "generic_sauce_vegetarian_satay_tbsp",
    "generic_sauce_yellow_mustard_tbsp",
    "generic_sauce_wasabi_serving",
    "generic_sauce_kumquat_serving",
    "generic_sauce_seafood_sauce_serving",
    "generic_sauce_sweet_bean_sauce_serving",
    "generic_sauce_teriyaki_sauce_serving",
}


def test_generic_common_batch_051_loads_sauce_modifier_anchors() -> None:
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


def test_generic_common_batch_051_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 400
    expected = {
        "generic_sauce_soy_paste_tbsp": (21, [10, 35]),
        "generic_sauce_zhajiang_serving": (154, [100, 230]),
        "generic_sauce_satay_tbsp": (108, [70, 150]),
        "generic_sauce_teriyaki_sauce_serving": (68, [40, 105]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
