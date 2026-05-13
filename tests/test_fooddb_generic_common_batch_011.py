from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_staple_beef_dumplings_10pc",
    "generic_staple_vegetarian_dumplings_10pc",
    "generic_staple_cabbage_dumplings_10pc",
    "generic_staple_mackerel_dumplings_10pc",
    "generic_snack_taro_bun_one",
    "generic_snack_red_bean_bun_one",
    "generic_snack_sesame_bun_one",
    "generic_snack_lotus_seed_bun_one",
    "generic_snack_bamboo_shoot_bun_one",
    "generic_dim_sum_shaomai_6pc",
    "generic_staple_tube_rice_pudding_one",
    "generic_staple_tube_rice_pudding_large",
    "generic_staple_inari_sushi_2pc",
    "generic_soup_corn_soup_packet",
    "generic_breakfast_oatmeal_packet",
    "generic_drink_almond_tea_packet",
    "generic_dessert_sesame_paste_packet",
    "generic_breakfast_mixed_nut_cereal_packet",
    "generic_dim_sum_pork_soup_buns_6pc",
    "generic_dim_sum_crystal_dumplings_6pc",
}


def test_generic_common_batch_011_loads_tfda_backed_dumpling_and_snack_meals() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id") or ""): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for anchor_id in BATCH_IDS:
        record = by_id[anchor_id]
        assert record["runtime_role"] == "common_serving_anchor"
        assert record["runtime_truth_allowed"] is True
        assert record["composition_posture"] == "estimable_with_refinement"
        assert record["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert record["source_refs"][0]["external_source_role"] == "source_evidence_only"
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "generic_range_estimate_with_refinement_not_exact"
        assert record["kcal_range"][0] <= record["kcal_point"] <= record["kcal_range"][1]


def test_generic_common_batch_011_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    item = by_id["generic_staple_beef_dumplings_10pc"]

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 374
    assert item["kcal_point"] == 532
    assert item["kcal_range"] == [430, 700]
    assert item["macro_visibility_status"] == "hidden_missing_source"
    assert item["macro_source_basis"] == "unknown"
    assert item["macro_confidence"] == "unknown"
