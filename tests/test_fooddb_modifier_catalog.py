from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_modifier_priority import (
    CATALOG_SUPPORTED_REPORT_ONLY_POSTURE,
    NON_P0_STAGED_POSTURE,
    P0_MODIFIERS,
    build_staged_policy_modifier_labels,
)
from app.nutrition.application.fooddb_modifier_catalog import build_fooddb_modifier_catalog


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def test_modifier_catalog_reports_runtime_modifier_coverage_without_schema_change() -> None:
    catalog = build_fooddb_modifier_catalog(small_anchor_payload=_small_anchor_payload())

    assert catalog["artifact_type"] == "accurate_intake_fooddb_modifier_catalog"
    assert catalog["runtime_truth_changed"] is False
    assert catalog["manager_context_changed"] is False
    assert catalog["packetizer_format_changed"] is False
    assert catalog["summary"]["runtime_common_serving_anchor_count"] == 51
    assert catalog["summary"]["modifier_aware_anchor_count"] == 20
    assert catalog["summary"]["modifier_name_count"] >= 10


def test_modifier_catalog_groups_known_modifier_names() -> None:
    catalog = build_fooddb_modifier_catalog(small_anchor_payload=_small_anchor_payload())
    groups = catalog["modifier_groups"]

    assert groups["sugar_level"]["anchor_count"] == 3
    assert groups["cup_size"]["anchor_count"] == 6
    assert groups["piece_count"]["anchor_count"] == 2
    assert groups["rice_portion"]["anchor_count"] == 2
    assert "custom_drink_boba_milk_tea" in groups["sugar_level"]["anchor_ids"]
    assert "staple_dumplings" in groups["piece_count"]["anchor_ids"]


def test_modifier_catalog_surfaces_p0_priority_groups_and_support_matrix() -> None:
    catalog = build_fooddb_modifier_catalog(small_anchor_payload=_small_anchor_payload())

    assert catalog["summary"]["p0_modifier_count"] == len(P0_MODIFIERS)
    assert catalog["summary"]["p0_supported_anchor_count"] == 8
    priority_groups = catalog["modifier_priority_groups"]
    assert priority_groups["P0"] == list(P0_MODIFIERS)
    assert priority_groups["unsupported_or_not_yet_covered"] == []
    assert {"piece_count", "size", "milk_type"} <= set(
        priority_groups["observed_runtime_non_p0_modifier_names"]
    )
    assert len(priority_groups["observed_runtime_non_p0_modifier_names"]) == 14
    assert priority_groups["policy_staged_modifier_labels"] == build_staged_policy_modifier_labels()

    matrix = catalog["p0_support_matrix"]
    assert sorted(matrix) == list(P0_MODIFIERS)
    assert matrix["sugar_level"] == {
        "modifier_name": "sugar_level",
        "priority": "P0",
        "supported": True,
        "anchor_count": 3,
        "anchor_ids": [
            "custom_drink_boba_milk_tea",
            "custom_drink_fresh_milk_tea",
            "custom_drink_soy_milk",
        ],
        "supported_values": ["full_sugar", "half_sugar", "unsweetened"],
        "followup_hints": ["ask_cup_size", "ask_sugar_level"],
        "activation_posture": CATALOG_SUPPORTED_REPORT_ONLY_POSTURE,
    }
    assert matrix["cup_size"]["anchor_count"] == 6
    assert matrix["cup_size"]["supported_values"] == ["large", "medium", "small"]
    assert set(matrix["rice_portion"]["anchor_ids"]) == {
        "generic_meal_chicken_bento",
        "rice_bowl_luroufan",
    }
    assert matrix["rice_portion"]["supported_values"] == ["full", "half", "large", "regular", "small"]


def test_modifier_catalog_surfaces_compact_p0_anchor_coverage_and_staged_non_p0_posture() -> None:
    catalog = build_fooddb_modifier_catalog(small_anchor_payload=_small_anchor_payload())

    p0_coverage = catalog["p0_anchor_coverage"]
    assert len(p0_coverage) == 8
    by_anchor_id = {item["anchor_id"]: item for item in p0_coverage}
    assert by_anchor_id["custom_drink_americano"]["p0_modifiers"] == ["cup_size"]
    assert by_anchor_id["custom_drink_americano"]["followup_hints"] == ["ask_cup_size"]
    assert by_anchor_id["rice_bowl_luroufan"]["p0_modifiers"] == ["rice_portion"]
    assert "ask_rice_portion" in by_anchor_id["rice_bowl_luroufan"]["followup_hints"]
    assert "custom_drink_boba_milk_tea" in by_anchor_id

    non_p0_posture = catalog["non_p0_posture"]
    assert non_p0_posture["treated_as_p0"] == []
    assert non_p0_posture["posture"] == NON_P0_STAGED_POSTURE
    assert non_p0_posture["runtime_truth_promoted"] is False
    assert {"add_ons", "piece_count", "size"} <= set(non_p0_posture["observed_runtime_modifier_names"])
    assert len(non_p0_posture["observed_runtime_modifier_names"]) == 14
    assert non_p0_posture["policy_staged_modifier_labels"] == build_staged_policy_modifier_labels()


def test_modifier_catalog_manager_payload_is_compact_runtime_only() -> None:
    catalog = build_fooddb_modifier_catalog(small_anchor_payload=_small_anchor_payload())
    manager_catalog = catalog["manager_modifier_catalog"]

    assert manager_catalog["raw_source_rows_included"] is False
    assert manager_catalog["candidate_only_records_included"] is False
    assert len(manager_catalog["anchors"]) == 20
    for item in manager_catalog["anchors"]:
        assert set(item) == {"anchor_id", "canonical_name", "modifiers", "followup_hints"}
        assert item["modifiers"]
        for modifier in item["modifiers"]:
            assert set(modifier) == {"name", "values"}


def test_modifier_catalog_manager_payload_drops_raw_modifier_fields() -> None:
    payload = _small_anchor_payload()
    for anchor in payload["anchors"]:
        if anchor.get("anchor_id") == "custom_drink_boba_milk_tea":
            anchor["major_modifiers"][0]["raw_source"] = {"leak": True}
            anchor["major_modifiers"][0]["candidate_records"] = [{"leak": True}]

    catalog = build_fooddb_modifier_catalog(small_anchor_payload=payload)
    manager_catalog = catalog["manager_modifier_catalog"]
    serialized_anchors = json.dumps(manager_catalog["anchors"])

    assert "raw_source" not in serialized_anchors
    assert "candidate_records" not in serialized_anchors


def test_modifier_catalog_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    output = tmp_path / "modifier_catalog.json"

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_modifier_catalog import main

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["summary"]["modifier_aware_anchor_count"] == 20
    assert artifact["product_loop_integration_claimed"] is False
