from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.food_evidence_tfda_promotion import (
    build_tfda_batch_promotion_artifact,
)
from app.nutrition.infrastructure.local_seed_evidence_store import LocalSeedNutritionEvidenceStore


def _candidate(
    candidate_id: str,
    label: str,
    *,
    kcal: float = 100,
    source_class: str = "taiwan_tfda_open_data",
    source_id: str = "tfda_fda_food_nutrition_2024",
) -> dict:
    return {
        "candidate_id": candidate_id,
        "source_id": source_id,
        "source_class": source_class,
        "evidence_role": "generic_anchor_candidate",
        "promotion_status": "candidate",
        "runtime_truth_allowed": False,
        "canonical_label": label,
        "aliases": [],
        "brand": None,
        "category": "\u98f2\u6599\u985e",
        "serving_basis": {"unit_type": "g", "amount": 100, "label": "per_100g_edible_portion"},
        "kcal_point": kcal,
        "source_provenance": {
            "source_id": source_id,
            "source_file": "FDA_food_nutrition_2024.xlsx",
            "row_index": 1576,
            "record_id": candidate_id,
            "source_url": "https://data.gov.tw/dataset/8543",
            "raw_row_hash": f"hash-{candidate_id}",
        },
    }


def _candidate_artifact(candidates: list[dict]) -> dict:
    return {
        "artifact_type": "accurate_intake_food_evidence_candidates",
        "candidates": candidates,
    }


def _auto_batch(candidate_ids: list[str]) -> dict:
    return {
        "artifact_type": "accurate_intake_food_auto_eligible_candidate_batch",
        "auto_eligible_candidates": [
            {
                "candidate_id": candidate_id,
                "source_class": "taiwan_tfda_open_data",
                "evidence_role": "generic_anchor_candidate",
                "promotion_status": "auto_eligible_packet_candidate",
                "runtime_truth_allowed": False,
                "packet_ready": False,
            }
            for candidate_id in candidate_ids
        ],
    }


def test_tfda_promotion_keeps_per_100g_evidence_out_of_runtime_estimates() -> None:
    artifact = build_tfda_batch_promotion_artifact(
        candidate_artifact=_candidate_artifact(
            [
                _candidate("boba", "\u73cd\u73e0\u5976\u8336(\u53bb\u51b0,\u534a\u7cd6)", kcal=83.5),
                _candidate(
                    "off",
                    "packaged",
                    source_class="open_food_facts",
                    source_id="openfoodfacts_taiwan_small",
                ),
            ]
        ),
        auto_eligible_artifact=_auto_batch(["boba", "off"]),
    )

    assert artifact["claim_scope"] == "tfda_batch_promotion_with_selected_runtime_anchors"
    assert artifact["food_kb_truth_updated"] is True
    assert artifact["runtime_truth_changed"] is True
    assert artifact["nutrition_seed_created"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["packet_truth_created"] is False
    assert artifact["summary"]["source_evidence_count"] == 1
    evidence = artifact["source_evidence_records"][0]
    assert evidence["runtime_role"] == "source_evidence_only"
    assert evidence["serving_basis"]["label"] == "per_100g_edible_portion"
    assert evidence["runtime_estimate_allowed"] is False
    assert evidence["packetizer_common_serving_allowed"] is False


def test_tfda_promotion_creates_only_selected_common_serving_anchors_with_approval_metadata() -> None:
    artifact = build_tfda_batch_promotion_artifact(
        candidate_artifact=_candidate_artifact(
            [
                _candidate("boba", "\u73cd\u73e0\u5976\u8336(\u53bb\u51b0,\u534a\u7cd6)", kcal=83.5),
                _candidate("dougan", "\u5c0f\u65b9\u8c46\u5e72", kcal=154.5),
                _candidate("egg_skin", "\u51b7\u51cd\u86cb\u9905\u76ae", kcal=228.2),
            ]
        ),
        auto_eligible_artifact=_auto_batch(["boba", "dougan", "egg_skin"]),
    )

    anchors = {
        anchor["anchor_id"]: anchor
        for anchor in artifact["selected_common_serving_anchors"]
    }
    assert set(anchors) == {"custom_drink_boba_milk_tea", "listed_item_tofu_dried"}
    boba = anchors["custom_drink_boba_milk_tea"]
    assert boba["runtime_role"] == "common_serving_anchor"
    assert boba["runtime_estimate_allowed"] is True
    assert boba["portion_basis"]["derived_from"] == [
        "tfda_per_100g_source_evidence",
        "mvp_portion_default_policy",
    ]
    assert boba["approval_metadata"]["approval_mode"] == "batch_policy_approved"
    assert boba["approval_metadata"]["policy_version"] == "food_evidence_tfda_batch_promotion_v1"
    assert boba["range_policy"]["uncertainty_category"] == (
        "high_variance_customizable_drink_or_meal"
    )
    assert artifact["excluded_auto_eligible_candidates"]["egg_skin"] == (
        "no_selected_mvp_portion_default"
    )


def test_tracked_tfda_source_evidence_is_not_loaded_as_small_anchor_runtime() -> None:
    source_path = Path("app/knowledge/tfda_per100g_source_evidence_tw.json")
    assert source_path.exists()
    source_artifact = json.loads(source_path.read_text(encoding="utf-8-sig"))
    assert source_artifact["runtime_estimate_allowed"] is False
    assert source_artifact["packetizer_common_serving_allowed"] is False
    assert source_artifact["records"]
    assert all(
        record["runtime_role"] == "source_evidence_only"
        and record["runtime_estimate_allowed"] is False
        for record in source_artifact["records"]
    )

    store_records = LocalSeedNutritionEvidenceStore().load_small_anchor_records()
    assert not any(record.get("record_kind") == "source_evidence_only" for record in store_records)


def test_selected_runtime_anchors_are_common_serving_not_per_100g() -> None:
    anchors = {
        item["anchor_id"]: item
        for item in json.loads(
            Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig")
        )["anchors"]
        if item.get("record_kind") == "generic_anchor"
    }
    selected = {
        "custom_drink_boba_milk_tea": "high_variance_customizable_drink_or_meal",
        "listed_item_tofu_dried": "moderate_prepared_item",
    }

    for anchor_id, uncertainty_category in selected.items():
        anchor = anchors[anchor_id]
        assert anchor["runtime_role"] == "common_serving_anchor"
        assert anchor["runtime_estimate_allowed"] is True
        assert anchor["serving_basis"] == "common_serving"
        assert anchor["portion_basis"]["portion_unit"]
        assert anchor["range_policy"]["uncertainty_category"] == uncertainty_category
        assert anchor["approval_metadata"]["policy_version"] == (
            "food_evidence_tfda_batch_promotion_v1"
        )
        assert all(ref["runtime_role"] == "source_evidence_only" for ref in anchor["source_refs"])


def test_tfda_promotion_cli_writes_roundtrippable_outputs(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidates.json"
    auto_path = tmp_path / "auto.json"
    source_output = tmp_path / "tfda_source.json"
    anchor_output = tmp_path / "anchors.json"
    report_output = tmp_path / "promotion.json"
    candidate_path.write_text(
        json.dumps(
            _candidate_artifact(
                [_candidate("boba", "\u73cd\u73e0\u5976\u8336(\u53bb\u51b0,\u534a\u7cd6)", kcal=83.5)]
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    auto_path.write_text(json.dumps(_auto_batch(["boba"]), ensure_ascii=False), encoding="utf-8")

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_tfda_batch_promotion import main

    assert main(
        [
            "--candidate-json",
            str(candidate_path),
            "--auto-eligible-json",
            str(auto_path),
            "--source-evidence-output",
            str(source_output),
            "--anchor-output",
            str(anchor_output),
            "--report-output",
            str(report_output),
        ]
    ) == 0

    source_artifact = read_json_artifact(source_output)
    anchor_artifact = read_json_artifact(anchor_output)
    report = read_json_artifact(report_output)
    assert source_artifact["records"][0]["runtime_estimate_allowed"] is False
    assert anchor_artifact["anchors"][0]["runtime_estimate_allowed"] is True
    assert report["summary"]["selected_runtime_anchor_count"] == 1
