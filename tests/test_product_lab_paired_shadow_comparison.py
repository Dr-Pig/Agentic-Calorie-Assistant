from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_paired_shadow_comparison import (
    build_product_lab_paired_shadow_comparison,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from tests.test_advanced_product_lab_runtime import _turn


def test_paired_shadow_comparison_aligns_candidate_only_and_lab_chat_delivery() -> None:
    turn = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("paired-shadow-default"),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    report = build_product_lab_paired_shadow_comparison(turn)

    assert report["artifact_type"] == "advanced_product_lab_paired_shadow_comparison"
    assert report["status"] == "pass"
    assert report["comparison_paths"] == [
        "baseline_product_outputs",
        "candidate_only_pre_delivery",
        "lab_chat_delivery",
    ]
    assert report["baseline_product_outputs"] == {
        "recommendation_present": True,
        "rescue_present": True,
        "canonical_product_mutation_allowed": False,
    }
    assert report["candidate_only_ids"] == ["recommendation_prompt:0", "rescue_nudge:1"]
    assert report["lab_chat_delivery_ids"] == [
        "recommendation_prompt:0",
        "rescue_nudge:1",
    ]
    assert report["shadow_comparison_passed"] is True
    assert report["mainline_activation_enabled"] is False
    assert report["blockers"] == []


def test_paired_shadow_comparison_keeps_suppressed_candidates_omitted_from_chat() -> None:
    turn = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            **_turn("paired-shadow-quiet"),
            "proactive_gate_context": {"local_time": "23:15"},
        },
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    report = build_product_lab_paired_shadow_comparison(turn)

    assert report["status"] == "pass"
    assert report["candidate_only_ids"] == []
    assert report["lab_chat_delivery_ids"] == []
    assert report["omitted_trigger_types"] == [
        "recommendation_prompt",
        "rescue_nudge",
    ]
    assert report["shadow_comparison_passed"] is True
