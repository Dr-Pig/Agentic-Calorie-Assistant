from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_runtime_anchor_batch import (
    INTERNAL_SEED_BATCH_ANCHOR_IDS,
    apply_internal_seed_runtime_anchor_batch_to_small_anchor_store,
    build_existing_anchor_promotion_plan,
    build_fooddb_runtime_coverage_matrix,
    build_fooddb_status_packet,
    build_internal_seed_runtime_anchor_batch,
)


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def _pre_n3_payload() -> dict:
    payload = _small_anchor_payload()
    for item in payload["anchors"]:
        if item.get("anchor_id") in INTERNAL_SEED_BATCH_ANCHOR_IDS:
            for key in (
                "runtime_role",
                "runtime_estimate_allowed",
                "runtime_truth_allowed",
                "serving_basis",
                "portion_basis",
                "kcal_point",
                "kcal_range",
                "source_refs",
                "source_provenance",
                "approval_metadata",
                "range_policy",
                "runtime_usage_boundary",
            ):
                item.pop(key, None)
    return payload


EXPECTED_RUNTIME_VISIBLE_ANCHOR_IDS = {
    "single_item_tea_egg",
    "custom_drink_boba_milk_tea",
    "custom_drink_latte",
    "custom_drink_americano",
    "custom_drink_soy_milk",
    "custom_drink_fresh_milk_tea",
    "custom_drink_unsweetened_green_tea",
    "custom_drink_cola",
    "generic_meal_chicken_bento",
    "single_item_salt_crispy_chicken",
    "breakfast_staple_egg_pancake",
    "breakfast_staple_rice_roll",
    "breakfast_staple_sandwich",
    "stable_base_beef_noodle",
    "stable_base_zhajiangmian",
    "single_item_sweet_potato",
    "listed_item_tofu_dried",
    "listed_item_kelp",
    "listed_item_meatball",
    "listed_item_greens_home_cooked",
    "listed_item_tofu_skin",
    "listed_item_instant_noodle_prince",
    "listed_item_chicken_cutlet",
    "listed_item_tempura_taiwan",
    "listed_item_pig_blood_rice_cake",
    "listed_item_green_beans",
    "listed_item_chicken_home_cooked",
    "listed_item_baiye_tofu",
    "listed_item_squid",
    "listed_item_rice_sausage",
    "listed_item_oden_fishcake",
    "listed_item_cabbage",
    "listed_item_duck_blood",
    "listed_item_glass_noodles",
    "listed_item_mushroom",
    "generic_meal_gyudon",
    "stable_base_spicy_stinky_tofu",
    "rice_bowl_luroufan",
    "staple_dumplings",
    "staple_potstickers",
}


def test_coverage_matrix_distinguishes_runtime_existing_anchor_and_gap() -> None:
    matrix = build_fooddb_runtime_coverage_matrix(small_anchor_payload=_pre_n3_payload())
    by_id = {entry["anchor_id"]: entry for entry in matrix["coverage_entries"] if entry.get("anchor_id")}

    assert matrix["runtime_truth_changed"] is False
    assert by_id["custom_drink_boba_milk_tea"]["coverage_status"] == "runtime_visible"
    assert by_id["listed_item_tofu_dried"]["coverage_status"] == "runtime_visible"
    assert by_id["breakfast_staple_egg_pancake"]["coverage_status"] == (
        "existing_small_anchor_not_runtime"
    )
    assert by_id["generic_meal_chicken_bento"]["recommended_next_action"] == (
        "consider_internal_seed_batch_promotion"
    )
    assert all(entry["classification_source"] != "raw_text" for entry in matrix["coverage_entries"])


def test_promotion_plan_is_existing_small_anchor_only_and_narrow() -> None:
    plan = build_existing_anchor_promotion_plan(small_anchor_payload=_pre_n3_payload())

    assert plan["runtime_truth_changed"] is False
    assert plan["batch_policy"]["approval_mode"] == "internal_seed_batch_approved"
    assert plan["batch_policy"]["max_items"] == 8
    assert plan["forbidden_promotions"] == [
        "new_food",
        "tfda_per_100g_as_common_serving",
        "open_food_facts_runtime_truth",
        "usda_runtime_truth",
        "old_base_db_runtime_truth",
        "official_brand_exact_card_runtime_truth",
    ]
    candidates = {candidate["anchor_id"]: candidate for candidate in plan["candidates"]}
    assert set(candidates) == set(INTERNAL_SEED_BATCH_ANCHOR_IDS)
    assert all(candidate["existing_small_anchor_present"] is True for candidate in candidates.values())
    assert all(candidate["promotion_ready"] is True for candidate in candidates.values())
    assert candidates["generic_meal_chicken_bento"]["runtime_usage_boundary"] == (
        "generic_range_estimate_only_not_exact"
    )
    assert candidates["listed_item_greens_home_cooked"]["runtime_usage_boundary"] == (
        "listed_component_only_not_generic_vegetable_truth"
    )


def test_internal_seed_batch_anchors_have_runtime_metadata_without_external_promotion() -> None:
    batch = build_internal_seed_runtime_anchor_batch(small_anchor_payload=_pre_n3_payload())

    assert batch["runtime_truth_changed"] is True
    assert batch["source_policy"] == "existing_small_anchor_store_only"
    assert batch["summary"]["selected_runtime_anchor_count"] == len(INTERNAL_SEED_BATCH_ANCHOR_IDS)
    assert batch["summary"]["selected_runtime_anchor_count"] <= 8
    anchors = {anchor["anchor_id"]: anchor for anchor in batch["anchors"]}
    assert set(anchors) == set(INTERNAL_SEED_BATCH_ANCHOR_IDS)

    for anchor in anchors.values():
        assert anchor["runtime_role"] == "common_serving_anchor"
        assert anchor["runtime_truth_allowed"] is True
        assert anchor["runtime_estimate_allowed"] is True
        assert anchor["serving_basis"] == "common_serving"
        assert anchor["portion_basis"]["portion_unit"]
        assert anchor["kcal_point"] > 0
        assert anchor["kcal_range"][0] <= anchor["kcal_point"] <= anchor["kcal_range"][1]
        assert anchor["source_provenance"]["source_id"] == "existing_small_anchor_store_tw"
        assert anchor["approval_metadata"]["approval_mode"] == "internal_seed_batch_approved"
        assert anchor["approval_metadata"]["runtime_truth_allowed"] is True
        assert anchor["kcal_basis"]["runtime_value_source"] == "existing_mvp_anchor_baseline"
        assert not {
            "open_food_facts",
            "usda",
            "old_base_db",
            "official_brand",
            "tfda_per_100g_as_serving",
        }.intersection(set(anchor["source_posture_flags"]))


def test_apply_internal_seed_batch_updates_existing_records_only() -> None:
    payload = _pre_n3_payload()
    before_count = len(payload["anchors"])
    batch = build_internal_seed_runtime_anchor_batch(small_anchor_payload=payload)
    updated = apply_internal_seed_runtime_anchor_batch_to_small_anchor_store(payload, batch)

    assert len(updated["anchors"]) == before_count
    by_id = {item.get("anchor_id"): item for item in updated["anchors"] if item.get("anchor_id")}
    for anchor_id in INTERNAL_SEED_BATCH_ANCHOR_IDS:
        assert by_id[anchor_id]["runtime_role"] == "common_serving_anchor"
        assert by_id[anchor_id]["runtime_truth_allowed"] is True

    bare_baskets = [
        item for item in updated["anchors"] if item.get("record_kind") == "generic_semantic_only"
    ]
    assert bare_baskets
    assert all("runtime_truth_allowed" not in item for item in bare_baskets)


def test_status_packet_reports_runtime_anchors_without_claiming_integration_readiness() -> None:
    batch = build_internal_seed_runtime_anchor_batch(small_anchor_payload=_pre_n3_payload())
    updated = apply_internal_seed_runtime_anchor_batch_to_small_anchor_store(_pre_n3_payload(), batch)
    matrix = build_fooddb_runtime_coverage_matrix(small_anchor_payload=updated)
    status = build_fooddb_status_packet(
        small_anchor_payload=updated,
        coverage_matrix=matrix,
        runtime_batch=batch,
    )

    assert status["track"] == "FDB"
    assert status["pl_ce_files_changed"] is False
    assert status["real_fooddb_evidence_available"] is True
    assert status["product_loop_integration_claimed"] is False
    assert status["runtime_visible_anchor_count"] == 40
    assert set(status["runtime_visible_anchor_ids"]) == EXPECTED_RUNTIME_VISIBLE_ANCHOR_IDS


def test_fooddb_runtime_anchor_batch_cli_writes_roundtrippable_outputs(tmp_path: Path) -> None:
    small_anchor_path = tmp_path / "small_anchor_store_tw.json"
    coverage_path = tmp_path / "coverage.json"
    plan_path = tmp_path / "plan.json"
    batch_path = tmp_path / "batch.json"
    status_path = tmp_path / "status.json"
    small_anchor_path.write_text(
        json.dumps(_pre_n3_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_runtime_anchor_batch import main

    assert main(
        [
            "--small-anchor-store",
            str(small_anchor_path),
            "--coverage-output",
            str(coverage_path),
            "--promotion-plan-output",
            str(plan_path),
            "--runtime-batch-output",
            str(batch_path),
            "--status-output",
            str(status_path),
            "--update-small-anchor-store",
        ]
    ) == 0

    coverage = read_json_artifact(coverage_path)
    plan = read_json_artifact(plan_path)
    batch = read_json_artifact(batch_path)
    status = read_json_artifact(status_path)
    updated = read_json_artifact(small_anchor_path)
    by_id = {item.get("anchor_id"): item for item in updated["anchors"] if item.get("anchor_id")}

    assert coverage["runtime_truth_changed"] is False
    assert plan["runtime_truth_changed"] is False
    assert batch["runtime_truth_changed"] is True
    assert status["product_loop_integration_claimed"] is False
    assert by_id["single_item_tea_egg"]["runtime_role"] == "common_serving_anchor"
