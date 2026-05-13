from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "generic_snack_rice_cracker_serving",
    "generic_snack_strawberry_sandwich_cookie_serving",
    "generic_snack_pancake_one",
    "generic_snack_corn_crackers_serving",
    "generic_dessert_phoenix_eye_cake_piece",
    "generic_dessert_cheesecake_slice",
    "generic_dessert_sponge_cake_slice",
    "generic_dessert_honey_cake_plain_slice",
    "generic_dessert_honey_cake_chocolate_slice",
    "generic_dessert_honey_cake_cheese_slice",
    "generic_dessert_date_walnut_cake_piece",
    "generic_dessert_red_bean_milk_popsicle_one",
    "generic_dessert_peanut_tofu_pudding_bowl",
    "generic_dessert_unsweetened_tofu_pudding_bowl",
    "generic_snack_sugar_roasted_chestnuts_serving",
    "generic_snack_peanut_candy_piece",
    "generic_snack_peanut_gong_candy_piece",
    "generic_snack_lactic_acid_candy_serving",
    "generic_snack_fruit_gummy_serving",
    "generic_snack_qq_fruit_gummy_serving",
}


def test_generic_common_batch_038_loads_tfda_backed_desserts_and_drinks() -> None:
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


def test_generic_common_batch_038_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["generic_common_serving"] == 274
    expected = {
        "generic_dessert_cheesecake_slice": (235, [170, 330]),
        "generic_dessert_red_bean_milk_popsicle_one": (129, [90, 190]),
        "generic_dessert_peanut_tofu_pudding_bowl": (146, [95, 230]),
        "generic_snack_fruit_gummy_serving": (123, [90, 175]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
