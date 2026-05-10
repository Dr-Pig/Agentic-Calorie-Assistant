from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.food_evidence_tfda_promotion import SELECTED_PORTION_DEFAULTS
from app.nutrition.application.fooddb_rebuild_drill import build_fooddb_rebuild_drill


def _write_tfda_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "id": "boba-drill",
            "variant": SELECTED_PORTION_DEFAULTS["custom_drink_boba_milk_tea"]["canonical_name"],
            "kcal": 83.5,
            "serving_basis": {
                "unit_type": "g",
                "amount": 100,
                "label": "per_100g_edible_portion",
            },
        }
    ]
    (root / "tfda_base_candidates.json").write_text(
        json.dumps(rows, ensure_ascii=False),
        encoding="utf-8",
    )


def test_fooddb_rebuild_drill_proves_packet_ready_rebuild_from_raw_source(tmp_path: Path) -> None:
    _write_tfda_fixture(tmp_path)

    artifact = build_fooddb_rebuild_drill(scan_roots=[tmp_path])

    assert artifact["artifact_type"] == "accurate_intake_fooddb_rebuild_drill"
    assert artifact["claim_scope"] == "fooddb_rebuild_drill_only"
    assert artifact["status"] == "pass"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["tracked_files_updated"] is False
    assert artifact["summary"]["candidate_count"] == 1
    assert artifact["summary"]["validator_passed_count"] == 1
    assert artifact["summary"]["selected_runtime_anchor_count"] == 1
    assert artifact["summary"]["packet_ready_status"] == "approved_packet_ready_fooddb_artifact_ready"
    assert artifact["summary"]["packet_ready_lane_counts"] == {
        "exact_item_card": 1,
        "generic_common_serving": 1,
        "listed_component": 1,
    }
    assert artifact["rebuild_checks"] == {
        "raw_to_candidate": "pass",
        "candidate_to_validation": "pass",
        "validation_to_auto_eligible": "pass",
        "promotion_to_selected_anchor": "pass",
        "selected_anchor_to_packet_ready": "pass",
        "macro_contract_preserved": "pass",
        "source_refs_preserved": "pass",
    }
    assert artifact["blockers"] == []


def test_fooddb_rebuild_drill_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    _write_tfda_fixture(tmp_path)
    output = tmp_path / "fooddb_rebuild_drill.json"

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_rebuild_drill import main

    assert main(["--scan-root", str(tmp_path), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_rebuild_drill"
    assert artifact["status"] == "pass"
    assert artifact["summary"]["candidate_count"] == 1
