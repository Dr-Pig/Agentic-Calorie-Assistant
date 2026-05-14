from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_SET = ROOT / "docs" / "quality" / "runtime_lab_memory_edd_golden_set.yaml"


def test_runtime_lab_memory_golden_set_tracks_closure_artifacts() -> None:
    contract = yaml.safe_load(GOLDEN_SET.read_text(encoding="utf-8-sig"))

    alignment = contract["runtime_lab_closure_alignment"]

    assert contract["version"] == 1.4
    assert alignment["status"] == "active_runtime_lab_alignment"
    assert alignment["complete_lab_allowed"] is True
    assert alignment["mainline_activation_enabled"] is False
    assert alignment["required_artifacts"] == [
        "advanced_product_lab_memory_record_dogfood_summary",
        "advanced_product_lab_memory_record_readiness_report",
        "advanced_product_lab_memory_record_integrated_e2e_artifact",
        "advanced_product_lab_memory_record_live_diagnostic_artifact",
        "advanced_product_lab_memory_record_holdout_report",
        "advanced_product_lab_memory_record_closure_pack",
        "advanced_product_lab_activation_wall_audit",
        "advanced_product_lab_live_edd_decision_pack",
    ]
    assert alignment["next_required_slice"] == (
        "real_dogfood_trace_calibration_when_available"
    )


def test_runtime_lab_memory_golden_set_records_negative_holdout_contract() -> None:
    contract = yaml.safe_load(GOLDEN_SET.read_text(encoding="utf-8-sig"))
    holdout = contract["runtime_lab_closure_alignment"]["negative_holdout_contract"]

    assert holdout["case_count"] == 5
    assert holdout["ignored_case_ids"] == []
    assert holdout["strength_by_record_id"] == {
        "negative-bitter-melon": "block",
        "negative-spicy": "block",
        "negative-vegetarian": "downrank",
        "negative-bland": "downrank",
        "negative-eggplant": "block",
    }
    assert holdout["confirmed_negative_before_positive_boost"] is True
    assert holdout["new_memory_mechanism_required"] is False
