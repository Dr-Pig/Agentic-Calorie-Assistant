from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_staple_ham_fried_rice_plate",
    "generic_staple_shrimp_fried_rice_plate",
    "generic_breakfast_white_mantou_one",
    "generic_breakfast_taro_mantou_one",
    "generic_breakfast_nut_mantou_one",
    "generic_snack_sauerkraut_pork_bun_one",
    "generic_snack_vegetable_bun_one",
    "generic_dessert_sesame_tangyuan_bowl",
    "generic_dessert_peanut_tangyuan_bowl",
    "generic_dessert_peanut_soup_bowl",
}


def test_generic_common_batch_008_loads_tfda_backed_common_meals() -> None:
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


def test_generic_common_batch_008_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    item = by_id["generic_staple_ham_fried_rice_plate"]

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 214
    assert item["kcal_point"] == 648
    assert item["kcal_range"] == [520, 820]
    assert item["macro_visibility_status"] == "hidden_missing_source"
    assert item["macro_source_basis"] == "unknown"
    assert item["macro_confidence"] == "unknown"
