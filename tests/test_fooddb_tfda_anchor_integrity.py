from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_tfda_anchor_integrity import (
    build_tfda_anchor_integrity_report,
)


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def _tfda_source_payload() -> dict:
    return json.loads(Path("app/knowledge/tfda_per100g_source_evidence_tw.json").read_text(encoding="utf-8"))


def test_tfda_runtime_anchor_integrity_preserves_source_and_macro_boundaries() -> None:
    report = build_tfda_anchor_integrity_report(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
    )

    assert report["artifact_type"] == "accurate_intake_fooddb_tfda_anchor_integrity_report"
    assert report["status"] == "pass"
    assert report["runtime_truth_changed"] is False
    assert report["summary"] == {
            "tfda_runtime_anchor_count": 44,
            "source_ref_match_count": 44,
            "macro_hidden_count": 44,
            "cjk_name_valid_count": 44,
        "blocker_count": 0,
    }
    assert report["blockers"] == []
    assert {
        row["anchor_id"]
        for row in report["anchor_checks"]
        if row["anchor_id"].startswith("breakfast_staple_")
    } == {
        "breakfast_staple_scallion_pancake",
        "breakfast_staple_radish_cake",
        "breakfast_staple_steamed_bun",
        "breakfast_staple_xiaolongbao",
        "breakfast_staple_ham_egg_sandwich",
    }
    for row in report["anchor_checks"]:
        assert row["source_ref_found"] is True
        assert row["source_role_boundary_ok"] is True
        assert row["source_kcal_matches"] is True
        assert row["macro_hidden_not_invented"] is True
        assert row["cjk_name_valid"] is True
