from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_proactive_latency_cost_omission import (
    build_product_lab_proactive_latency_cost_omission_report,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from tests.test_advanced_product_lab_runtime import _turn


def test_latency_cost_omission_report_records_usage_and_degraded_omission() -> None:
    active = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("latency-cost-active"),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )
    quiet = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            **_turn("latency-cost-quiet"),
            "proactive_gate_context": {"local_time": "23:15"},
        },
        fixture_inputs=build_product_lab_fixture_inputs(),
    )
    live_diagnostic = {
        "artifact_type": "advanced_product_lab_proactive_feedback_live_diagnostic",
        "status": "pass",
        "provider_profile_id": (
            "builderspace-grok-4-fast-advanced-shadow-lab-live-diagnostic"
        ),
        "live_provider_used": True,
        "provider_trace_summary": {"usage_present": True, "provider": "builderspace"},
    }

    report = build_product_lab_proactive_latency_cost_omission_report(
        turn_artifacts=[active, quiet],
        live_diagnostic_artifact=live_diagnostic,
    )

    assert report["artifact_type"] == (
        "advanced_product_lab_proactive_latency_cost_omission_report"
    )
    assert report["status"] == "pass"
    assert report["provider_cost_posture"] == {
        "provider_profile_id": (
            "builderspace-grok-4-fast-advanced-shadow-lab-live-diagnostic"
        ),
        "live_provider_used": True,
        "usage_present": True,
        "cost_amount_claimed": False,
    }
    assert report["omission_trace_count"] == 2
    assert report["omitted_trigger_types"] == [
        "recommendation_prompt",
        "rescue_nudge",
    ]
    assert report["degraded_omission_behavior"] == (
        "omit_candidates_without_retry_expansion"
    )
    assert report["retry_expansion_attempted"] is False
    assert report["canonical_product_mutation_allowed"] is False
    assert report["blockers"] == []
