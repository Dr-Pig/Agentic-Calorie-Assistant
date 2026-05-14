from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from app.advanced_shadow_lab.product_lab_proactive_candidate import (
    product_lab_proactive_candidate,
)
from app.advanced_shadow_lab.product_lab_proactive_gate import (
    review_product_lab_proactive_candidates,
)


HOLDOUT_PATH = Path(
    "docs/quality/advanced_product_lab_proactive_adversarial_holdouts.yaml"
)


def test_proactive_adversarial_holdout_pack_covers_source_quality_risks() -> None:
    suite = _holdout_suite()

    assert suite["artifact_type"] == "advanced_product_lab_proactive_adversarial_holdouts"
    assert suite["raw_keyword_semantic_oracle_allowed"] is False
    assert suite["mainline_activation_enabled"] is False
    assert suite["case_count"] == len(suite["cases"]) == 5
    assert {case["case_type"] for case in suite["cases"]} == {
        "missing_user_relevant_reason",
        "stale_source",
        "prompt_injection_source",
        "low_value_source",
        "valid_source_not_undertriggered",
    }


def test_source_quality_holdouts_block_overtrigger_without_undertrigger() -> None:
    reports = {
        case["case_id"]: _review_case(case)
        for case in _holdout_suite()["cases"]
    }

    assert reports["pro-adv-001"]["review_decision"]["status"] == (
        "suppressed_context_or_data"
    )
    assert reports["pro-adv-001"]["suppression_reasons"] == [
        "missing_user_relevant_reason"
    ]
    assert reports["pro-adv-002"]["suppression_reasons"] == ["source_stale"]
    assert reports["pro-adv-003"]["suppression_reasons"] == [
        "source_prompt_injection_detected"
    ]
    assert reports["pro-adv-004"]["suppression_reasons"] == ["source_low_value"]
    assert reports["pro-adv-005"]["review_decision"]["status"] == (
        "candidate_for_human_review"
    )
    assert reports["pro-adv-005"]["suppression_reasons"] == []


def _review_case(case: Mapping[str, Any]) -> dict[str, Any]:
    artifact = review_product_lab_proactive_candidates(
        turn={"surface": "chat", "lab_now_minute": 780},
        candidates=[_candidate(case)],
        memory_context_pack={},
        prior_control_journal=[],
    )
    [review] = artifact["candidate_reviews"]
    return dict(review)


def _candidate(case: Mapping[str, Any]) -> dict[str, Any]:
    return product_lab_proactive_candidate(
        trigger_type=str(case.get("trigger_type") or "recommendation_prompt"),
        candidate_kind="adversarial_holdout_candidate",
        source_output_refs=[str(case["case_id"])],
        source_status="pass",
        control_model={
            "dismiss_reason_choices": ["too_frequent", "not_useful"],
            "snooze_window": {"minutes": 30},
            "next_signal_required": "material_source_quality_change",
        },
        next_signal_fallback="material_source_quality_change",
        wake_source_trace=dict(case.get("wake_source_trace") or {}),
        source_bridge_trace=dict(case.get("source_bridge_trace") or {}),
    )


def _holdout_suite() -> dict[str, Any]:
    return dict(yaml.safe_load(HOLDOUT_PATH.read_text(encoding="utf-8-sig")))
