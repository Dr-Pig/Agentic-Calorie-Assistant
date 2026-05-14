from __future__ import annotations

from pathlib import Path
from typing import Any

from app.advanced_shadow_lab.product_lab_proactive_send_skip_live_diagnostic import (
    run_product_lab_proactive_send_skip_live_diagnostic,
)
from tests.test_product_lab_proactive_send_skip_fixture import _proactive_artifact


class _FakeSendSkipLiveProvider:
    def __init__(self, *, mutation_request: bool = False) -> None:
        self.mutation_request = mutation_request

    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-grokfast-send-skip", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "claim_scope": "diagnostic_only",
            "provider_decisions": [
                {
                    "candidate_id": "recommendation_prompt:0",
                    "send_or_skip": "send",
                    "reason_summary": "App-open recommendation help is relevant.",
                    "chat_first_copy": "要不要我幫你挑一個現在可行的選項？",
                    "skip_reason": "",
                    "reason_codes": ["app_open", "qualified_offer"],
                    "delivery_request": False,
                    "scheduler_request": False,
                    "notification_request": False,
                    "mutation_request": self.mutation_request,
                },
                {
                    "candidate_id": "rescue_nudge:1",
                    "send_or_skip": "skip",
                    "reason_summary": "Rescue nudge is too interruptive here.",
                    "chat_first_copy": "",
                    "skip_reason": "interrupt_cost_too_high",
                    "reason_codes": ["high_interrupt_cost"],
                    "delivery_request": False,
                    "scheduler_request": False,
                    "notification_request": False,
                    "mutation_request": False,
                },
            ],
        }, {
            "stage": "advanced_product_lab_proactive_send_skip_grokfast_diagnostic",
            "provider": "fake",
            "usage": {"total_tokens": 123},
        }


def test_proactive_send_skip_live_diagnostic_fake_provider_passes(tmp_path: Path) -> None:
    artifact = run_product_lab_proactive_send_skip_live_diagnostic(
        pre_delivery_review=_proactive_artifact()["pre_delivery_review"],
        provider=_FakeSendSkipLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        output_path=tmp_path / "send_skip.json",
    )

    assert artifact["artifact_type"] == (
        "advanced_product_lab_proactive_send_skip_grokfast_live_diagnostic"
    )
    assert artifact["status"] == "pass"
    assert artifact["provider_invoked"] is True
    assert artifact["live_provider_used"] is False
    assert artifact["live_grokfast_diagnostic_pass"] is False
    assert artifact["validation_artifact"]["send_candidate_ids"] == [
        "recommendation_prompt:0"
    ]
    assert artifact["provider_trace_summary"]["usage_present"] is True
    assert artifact["scheduler_delivery_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_proactive_send_skip_live_diagnostic_blocks_validator_failures() -> None:
    artifact = run_product_lab_proactive_send_skip_live_diagnostic(
        pre_delivery_review=_proactive_artifact()["pre_delivery_review"],
        provider=_FakeSendSkipLiveProvider(mutation_request=True),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "validation.provider_decision[recommendation_prompt:0].mutation_request_not_allowed"
    ]
    assert artifact["live_provider_used"] is False


def test_live_invoked_artifact_keeps_live_provider_used_after_false_flags() -> None:
    artifact = run_product_lab_proactive_send_skip_live_diagnostic(
        pre_delivery_review=_proactive_artifact()["pre_delivery_review"],
        provider=_FakeSendSkipLiveProvider(),
        provider_mode="builderspace-grok-4-fast-advanced-shadow-lab-live-diagnostic",
        live_invoked=True,
    )

    assert artifact["status"] == "pass"
    assert artifact["live_provider_used"] is True
    assert artifact["live_grokfast_diagnostic_pass"] is True
