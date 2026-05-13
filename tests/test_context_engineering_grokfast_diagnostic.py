from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_grokfast_diagnostic import (
    run_context_engineering_grokfast_diagnostic,
)


def test_ce_grokfast_diagnostic_fake_provider_contract_passes() -> None:
    artifact = run_context_engineering_grokfast_diagnostic(
        provider=_FakeCEPlannerProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["artifact_type"] == "advanced_product_lab_ce_grokfast_live_diagnostic"
    assert artifact["status"] == "pass"
    assert artifact["diagnostic_evidence_class"] == "fake_contract"
    assert artifact["provider_invoked"] is True
    assert artifact["live_grokfast_diagnostic_pass"] is False
    assert artifact["case_count"] == 4
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["scheduler_delivery_allowed"] is False
    assert artifact["output_guard"] == {"status": "pass", "blockers": []}


def test_ce_grokfast_diagnostic_blocks_mutation_or_delivery_request() -> None:
    artifact = run_context_engineering_grokfast_diagnostic(
        provider=_FakeCEPlannerProvider(mutation_request=True),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert "case:ce-stress-021.mutation_request" in artifact["blockers"]


class _FakeCEPlannerProvider:
    def __init__(self, *, mutation_request: bool = False) -> None:
        self.mutation_request = mutation_request

    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-ce-grokfast", "configured": True}

    async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
        cases = []
        for case_id, capabilities in (
            ("ce-stress-021", ["pending_meal_intent"]),
            ("ce-stress-022", ["pending_meal_intent", "intake"]),
            ("ce-stress-025", ["query", "rescue"]),
            ("ce-stress-026", ["proactive", "memory", "rescue"]),
        ):
            cases.append(
                {
                    "case_id": case_id,
                    "selected_capabilities": capabilities,
                    "tool_call_order": [f"{capability}.run" for capability in capabilities],
                    "action_request": False,
                    "delivery_request": False,
                    "mutation_request": self.mutation_request and case_id == "ce-stress-021",
                    "risk_notes": "diagnostic only",
                }
            )
        return {
            "claim_scope": "diagnostic_only",
            "case_decisions": cases,
        }, {"stage": "advanced_product_lab_ce_grokfast_diagnostic", "provider": "fake"}
