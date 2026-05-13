from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_decision_pack import (
    build_context_engineering_decision_pack,
    context_engineering_decision_pack_blockers,
)


def test_context_engineering_decision_pack_opens_proactive_entry_gate() -> None:
    pack = build_context_engineering_decision_pack()

    assert pack["artifact_type"] == "advanced_product_lab_ce_stress_decision_pack"
    assert pack["status"] == "pass"
    assert pack["proactive_entry_gate"]["status"] == "ready_for_proactive_train"
    assert pack["proactive_entry_gate"]["allowed_next_train"] == (
        "advanced_product_lab_proactive_context_engineering"
    )
    assert pack["fixture_gate_status"] == "pass"
    assert pack["holdout_gate_status"] == "pass"
    assert pack["final_response_boundary_status"] == "pass"
    assert pack["live_grokfast_diagnostic_status"] == "pass"
    assert pack["mainline_activation_enabled"] is False
    assert pack["production_scheduler_delivery_allowed"] is False
    assert pack["blockers"] == []


def test_context_engineering_decision_pack_blocks_without_live_pass() -> None:
    blockers = context_engineering_decision_pack_blockers(
        fixture_status="pass",
        holdout_status="pass",
        final_response_status="pass",
        live_evidence={
            "status": "blocked",
            "live_provider_used": False,
            "live_grokfast_diagnostic_pass": False,
        },
    )

    assert blockers == [
        "live_grokfast_diagnostic.status_not_pass",
        "live_grokfast_diagnostic.live_provider_not_used",
        "live_grokfast_diagnostic.pass_flag_false",
    ]
