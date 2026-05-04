from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_modifier_catalog import build_fooddb_modifier_catalog


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def test_modifier_catalog_reports_runtime_modifier_coverage_without_schema_change() -> None:
    catalog = build_fooddb_modifier_catalog(small_anchor_payload=_small_anchor_payload())

    assert catalog["artifact_type"] == "accurate_intake_fooddb_modifier_catalog"
    assert catalog["runtime_truth_changed"] is False
    assert catalog["manager_context_changed"] is False
    assert catalog["packetizer_format_changed"] is False
    assert catalog["summary"]["runtime_common_serving_anchor_count"] == 40
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


def test_modifier_catalog_manager_payload_is_compact_runtime_only() -> None:
    catalog = build_fooddb_modifier_catalog(small_anchor_payload=_small_anchor_payload())
    manager_catalog = catalog["manager_modifier_catalog"]

    assert manager_catalog["raw_source_rows_included"] is False
    assert manager_catalog["candidate_only_records_included"] is False
    assert len(manager_catalog["anchors"]) == 20
    for item in manager_catalog["anchors"]:
        assert set(item) == {"anchor_id", "canonical_name", "modifiers", "followup_hints"}
        assert item["modifiers"]


def test_modifier_catalog_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    output = tmp_path / "modifier_catalog.json"

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_modifier_catalog import main

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["summary"]["modifier_aware_anchor_count"] == 20
    assert artifact["product_loop_integration_claimed"] is False
