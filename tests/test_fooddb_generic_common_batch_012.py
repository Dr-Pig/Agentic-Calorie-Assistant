from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_snack_sweet_nian_gao_100g",
    "generic_snack_cantonese_taro_cake_slice",
    "generic_snack_salty_mochi_2pc",
    "generic_snack_taro_pastry_one",
    "generic_snack_lotus_paste_mooncake_small",
    "generic_snack_sweet_potato_pastry_one",
    "generic_snack_turnip_wheel_cake_one",
    "generic_snack_ox_tongue_pastry_one",
    "generic_dessert_egg_tart_one",
    "generic_snack_dorayaki_one",
    "generic_breakfast_waffle_one",
    "generic_bakery_dinner_roll_one",
    "generic_bakery_twin_bread_one",
    "generic_staple_meat_zongzi_one",
    "generic_staple_alkaline_zongzi_one",
    "generic_dessert_pork_tangyuan_bowl",
    "generic_staple_instant_rice_pack",
    "generic_staple_mi_tai_mu_bowl",
    "generic_staple_ban_tiao_bowl",
    "generic_staple_frozen_ham_pizza_half",
}


def test_generic_common_batch_012_loads_tfda_backed_prepared_staples() -> None:
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
        assert record["source_provenance"]["source_file"] == (
            "app/knowledge/tfda_per100g_source_evidence_tw.json"
        )
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "generic_range_estimate_with_refinement_not_exact"
        assert record["kcal_range"][0] <= record["kcal_point"] <= record["kcal_range"][1]


def test_generic_common_batch_012_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    item = by_id["generic_staple_meat_zongzi_one"]

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 114
    assert item["kcal_point"] == 467
    assert item["kcal_range"] == [360, 650]
    assert item["macro_visibility_status"] == "hidden_missing_source"
    assert item["macro_source_basis"] == "unknown"
    assert item["macro_confidence"] == "unknown"
