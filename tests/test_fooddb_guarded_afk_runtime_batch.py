from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_guarded_afk_runtime_batch import (
    POLICY_VERSION,
    build_guarded_afk_runtime_anchor_batch,
    apply_guarded_afk_runtime_anchor_batch_to_small_anchor_store,
)


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def _pre_guarded_afk_payload() -> dict:
    payload = _small_anchor_payload()
    guarded_keys = (
        "runtime_role",
        "runtime_estimate_allowed",
        "runtime_truth_allowed",
        "serving_basis",
        "portion_basis",
        "kcal_point",
        "kcal_range",
        "source_refs",
        "source_provenance",
        "source_posture_flags",
        "approval_metadata",
        "range_policy",
        "runtime_usage_boundary",
        "kcal_basis",
    )
    for item in payload["anchors"]:
        approval = item.get("approval_metadata") or {}
        if approval.get("policy_version") == POLICY_VERSION:
            for key in guarded_keys:
                item.pop(key, None)
    return payload


def test_guarded_afk_runtime_batch_promotes_existing_non_runtime_anchors_only() -> None:
    batch = build_guarded_afk_runtime_anchor_batch(small_anchor_payload=_pre_guarded_afk_payload())

    assert batch["artifact_type"] == "accurate_intake_fooddb_guarded_afk_runtime_anchor_batch"
    assert batch["runtime_truth_changed"] is True
    assert batch["source_policy"] == "existing_small_anchor_store_only"
    assert batch["summary"]["selected_runtime_anchor_count"] == 31
    assert batch["summary"]["selected_runtime_anchor_count"] <= 40
    assert batch["summary"]["new_food_count"] == 0
    assert batch["summary"]["source_evidence_only_count"] == 0
    assert batch["summary"]["exact_card_count"] == 0
    assert batch["forbidden_promotions"] == [
        "new_food",
        "tfda_per_100g_as_common_serving",
        "open_food_facts_runtime_truth",
        "usda_runtime_truth",
        "old_base_db_runtime_truth",
        "official_brand_exact_card_runtime_truth",
    ]


def test_guarded_afk_runtime_batch_anchors_have_required_runtime_metadata() -> None:
    batch = build_guarded_afk_runtime_anchor_batch(small_anchor_payload=_pre_guarded_afk_payload())

    for anchor in batch["anchors"]:
        assert anchor["runtime_role"] == "common_serving_anchor"
        assert anchor["runtime_truth_allowed"] is True
        assert anchor["runtime_estimate_allowed"] is True
        assert anchor["serving_basis"] == "common_serving"
        assert anchor["portion_basis"]["portion_unit"]
        assert anchor["portion_basis"]["derived_from"] == [
            "existing_small_anchor_store",
            "guarded_afk_batch_policy",
        ]
        assert anchor["kcal_range"][0] <= anchor["kcal_point"] <= anchor["kcal_range"][1]
        assert anchor["source_provenance"]["source_id"] == "existing_small_anchor_store_tw"
        assert anchor["approval_metadata"]["approval_mode"] == "guarded_afk_batch_policy_approved"
        assert anchor["approval_metadata"]["runtime_truth_allowed"] is True
        assert anchor["kcal_basis"]["runtime_value_source"] == "existing_mvp_anchor_baseline"


def test_guarded_afk_runtime_batch_preserves_basket_and_exact_boundaries() -> None:
    batch = build_guarded_afk_runtime_anchor_batch(small_anchor_payload=_pre_guarded_afk_payload())
    by_id = {anchor["anchor_id"]: anchor for anchor in batch["anchors"]}

    assert by_id["listed_item_tofu_skin"]["runtime_usage_boundary"] == "listed_component_only"
    assert by_id["listed_item_chicken_cutlet"]["runtime_usage_boundary"] == "listed_component_only"
    assert by_id["stable_base_beef_noodle"]["runtime_usage_boundary"] == (
        "generic_range_estimate_with_refinement_not_exact"
    )
    assert by_id["custom_drink_fresh_milk_tea"]["runtime_usage_boundary"] == (
        "generic_drink_range_estimate_with_refinement"
    )
    assert by_id["single_item_salt_crispy_chicken"]["runtime_usage_boundary"] == (
        "generic_single_item_range_estimate_with_refinement"
    )


def test_apply_guarded_afk_batch_updates_existing_records_without_promoting_semantic_baskets() -> None:
    payload = _pre_guarded_afk_payload()
    batch = build_guarded_afk_runtime_anchor_batch(small_anchor_payload=payload)
    updated = apply_guarded_afk_runtime_anchor_batch_to_small_anchor_store(payload, batch)

    runtime = [
        item
        for item in updated["anchors"]
        if item.get("record_kind") == "generic_anchor"
        and item.get("runtime_role") == "common_serving_anchor"
        and item.get("runtime_truth_allowed") is True
    ]
    semantic = [item for item in updated["anchors"] if item.get("record_kind") == "generic_semantic_only"]
    assert len(runtime) == 40
    assert len(semantic) == 4
    assert all(item.get("runtime_truth_allowed") is not True for item in semantic)


def test_guarded_afk_runtime_batch_cli_writes_and_updates_store(tmp_path: Path) -> None:
    small_anchor_path = tmp_path / "small_anchor_store_tw.json"
    output = tmp_path / "batch.json"
    small_anchor_path.write_text(
        json.dumps(_pre_guarded_afk_payload(), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_guarded_afk_runtime_batch import main

    assert main(
        [
            "--small-anchor-store",
            str(small_anchor_path),
            "--output",
            str(output),
            "--update-small-anchor-store",
        ]
    ) == 0

    batch = read_json_artifact(output)
    updated = read_json_artifact(small_anchor_path)
    runtime = [item for item in updated["anchors"] if item.get("runtime_truth_allowed") is True]
    assert batch["summary"]["selected_runtime_anchor_count"] == 31
    assert len(runtime) == 40
