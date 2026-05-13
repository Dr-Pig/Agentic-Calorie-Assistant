from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_sauce_korean_sauce_serving",
    "generic_sauce_garlic_sauce_tbsp",
    "generic_sauce_spicy_garlic_sauce_tbsp",
    "generic_sauce_scallion_sauce_tbsp",
    "generic_sauce_sweet_sour_sauce_serving",
    "generic_sauce_ketchup_serving",
    "generic_sauce_ginger_sauce_tbsp",
    "generic_sauce_mushroom_sauce_serving",
    "generic_sauce_rice_bean_sauce_tbsp",
    "generic_sauce_garlic_black_bean_tbsp",
    "generic_sauce_bean_crumb_sauce_tbsp",
    "generic_sauce_red_yeast_sauce_tbsp",
    "generic_sauce_chive_flower_sauce_tbsp",
    "generic_sauce_xiangchun_sauce_tbsp",
    "generic_sauce_mapo_sauce_serving",
    "generic_sauce_shrimp_sauce_tbsp",
    "generic_sauce_salad_dressing_tbsp",
    "generic_sauce_egg_free_salad_dressing_tbsp",
    "generic_sauce_japanese_salad_dressing_serving",
    "generic_sauce_caesar_dressing_serving",
    "generic_spread_chocolate_sauce_serving",
    "generic_spread_grape_jam_serving",
    "generic_spread_pomelo_jam_serving",
    "generic_spread_mulberry_jam_serving",
    "generic_spread_white_sesame_bread_spread_tbsp",
    "generic_spread_black_sesame_bread_spread_tbsp",
}


def test_generic_common_batch_052_loads_generic_lane_closeout_anchors() -> None:
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


def test_generic_common_batch_052_closes_generic_lane_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 400
    expected = {
        "generic_sauce_korean_sauce_serving": (31, [20, 50]),
        "generic_sauce_garlic_black_bean_tbsp": (53, [35, 80]),
        "generic_sauce_salad_dressing_tbsp": (94, [65, 130]),
        "generic_spread_black_sesame_bread_spread_tbsp": (98, [65, 140]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
