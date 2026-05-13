from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_market_frozen_ham_fried_rice_pack",
    "generic_market_frozen_shrimp_fried_rice_pack",
    "generic_market_inari_sushi_serving",
    "generic_dim_sum_pork_soup_dumplings_6pc",
    "generic_dim_sum_frozen_char_siu_bao_one",
    "generic_dim_sum_frozen_beef_bao_one",
    "generic_dim_sum_pickled_mustard_pork_bao_one",
    "generic_dim_sum_taro_bao_one",
    "generic_dim_sum_red_bean_bao_one",
    "generic_dim_sum_sesame_bao_one",
    "generic_dim_sum_lotus_seed_bao_one",
    "generic_dim_sum_mala_cake_slice",
    "generic_side_cantonese_radish_cake_slice",
    "generic_side_ningbo_rice_cake_serving",
    "generic_dessert_sesame_tangyuan_4pc",
    "generic_dessert_peanut_tangyuan_4pc",
    "generic_dim_sum_pearl_meatball_4pc",
    "generic_hotpot_chicken_meatballs_serving",
    "generic_hotpot_squid_balls_serving",
    "generic_breakfast_nut_mantou_one",
}


def test_generic_common_batch_035_loads_tfda_backed_market_meals() -> None:
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
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["source_provenance"]["source_url"] == "https://data.gov.tw/dataset/8543"
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "generic_range_estimate_with_refinement_not_exact"
        assert record["kcal_range"][0] <= record["kcal_point"] <= record["kcal_range"][1]


def test_generic_common_batch_035_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 254
    expected = {
        "generic_market_frozen_ham_fried_rice_pack": (556, [420, 730]),
        "generic_market_inari_sushi_serving": (386, [290, 510]),
        "generic_dim_sum_pork_soup_dumplings_6pc": (411, [310, 560]),
        "generic_dessert_sesame_tangyuan_4pc": (421, [320, 580]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
