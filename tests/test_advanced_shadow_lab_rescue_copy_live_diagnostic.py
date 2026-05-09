from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.rescue_copy_live_diagnostic import (
    run_rescue_copy_live_diagnostic,
)


class FakeRescueCopyDiagnosticProvider:
    def __init__(self, response: Mapping[str, Any] | None = None) -> None:
        self.response = dict(response or _default_model_response())
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-rescue-copy", "configured": True}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        self.calls.append({"stage": kwargs.get("stage")})
        return dict(self.response), {
            "stage": "advanced_shadow_rescue_copy_live_diagnostic",
            "provider": "fake",
        }


def test_rescue_copy_live_diagnostic_records_fake_provider_artifact(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "rescue_copy_live_diagnostic.json"

    artifact = run_rescue_copy_live_diagnostic(
        rescue_shaping_input_packet=_shaping_input_packet(),
        output_path=output_path,
        provider=FakeRescueCopyDiagnosticProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert json.loads(output_path.read_text(encoding="utf-8")) == artifact
    assert artifact["artifact_type"] == (
        "advanced_shadow_rescue_copy_live_diagnostic_artifact"
    )
    assert artifact["status"] == "pass"
    assert artifact["target_surface"] == "rescue_proposal_copy_posture"
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["live_invoked"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["provider_invoked"] is True
    assert artifact["runtime_connected"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["output_guard"]["status"] == "pass"
    assert artifact["model_output_summary"] == {
        "proposal_headline_present": True,
        "proposal_summary_present": True,
        "coaching_frame_present": True,
        "claim_scope": "diagnostic_copy_only",
        "reason_codes": ["future_oriented", "no_shame", "review_only"],
    }
    assert artifact["deterministic_option_summary"] == {
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
    }
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["rescue_committed"] is False
    assert artifact["proposal_committed"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_enabled"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert "private rescue story" not in serialized
    assert "hidden body plan detail" not in serialized


def test_rescue_copy_live_diagnostic_blocks_model_authority_language() -> None:
    provider = FakeRescueCopyDiagnosticProvider(
        response={
            "proposal_headline": "I sent the rescue plan.",
            "proposal_summary": "This committed a two-day budget change.",
            "coaching_frame": "Saved it to your plan.",
            "recommended_days": 2,
            "daily_kcal_adjustment": -150,
            "cap_mode": "standard_15_percent",
            "special_posture": "standard_spread",
            "claim_scope": "user_facing",
            "action_request": True,
            "delivery_request": True,
            "mutation_request": True,
            "reason_codes": ["unsafe_action"],
        }
    )

    artifact = run_rescue_copy_live_diagnostic(
        rescue_shaping_input_packet=_shaping_input_packet(),
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert artifact["output_guard"]["status"] == "blocked"
    assert artifact["blockers"] == [
        "model_output.claim_scope_not_diagnostic",
        "model_output.action_request_not_allowed",
        "model_output.delivery_request_not_allowed",
        "model_output.mutation_request_not_allowed",
        "model_output.delivery_language_present",
        "model_output.mutation_language_present",
    ]
    assert artifact["rescue_committed"] is False
    assert artifact["proposal_committed"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_rescue_copy_live_diagnostic_blocks_deterministic_option_override() -> None:
    provider = FakeRescueCopyDiagnosticProvider(
        response={**_default_model_response(), "recommended_days": 5}
    )

    artifact = run_rescue_copy_live_diagnostic(
        rescue_shaping_input_packet=_shaping_input_packet(),
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["model_output.recommended_days_override"]
    assert artifact["day_budget_mutated"] is False
    assert artifact["body_plan_mutated"] is False


def test_rescue_copy_live_diagnostic_blocks_input_claim_drift() -> None:
    provider = FakeRescueCopyDiagnosticProvider()
    packet = _shaping_input_packet()
    packet["proposal_committed"] = True
    packet["day_budget_mutated"] = True

    artifact = run_rescue_copy_live_diagnostic(
        rescue_shaping_input_packet=packet,
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert provider.calls == []
    assert artifact["status"] == "blocked"
    assert artifact["provider_invoked"] is False
    assert artifact["blockers"] == [
        "rescue_shaping_input_packet.proposal_committed",
        "rescue_shaping_input_packet.day_budget_mutated",
    ]
    assert artifact["live_provider_used"] is False
    assert artifact["proposal_committed"] is False


def test_rescue_copy_live_diagnostic_runner_is_manual_env_gated() -> None:
    source = Path(
        "scripts/run_advanced_shadow_lab_rescue_copy_live_diagnostic.py"
    ).read_text(encoding="utf-8")

    assert "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC" in source
    assert "--allow-live-provider" in source
    assert "app.runtime.interface.provider_runtime" not in source
    assert "app.routes" not in source
    assert "scheduler" not in source.lower()
    assert "rescue_committed=True" not in source
    assert "proposal_committed=True" not in source
    assert "user_facing_behavior_changed=True" not in source


def _shaping_input_packet() -> dict[str, object]:
    return {
        "artifact_type": "rescue_proposal_shaping_input_shadow_packet",
        "status": "pass",
        "shaping_input_envelope": {
            "deterministic_option": {
                "recommended_days": 2,
                "daily_kcal_adjustment": -150,
                "cap_mode": "standard_15_percent",
                "special_posture": "standard_spread",
                "guardrail_notes": ["stay_above_safety_floor"],
            },
            "review_context": {
                "budget_context": {
                    "current_date": "2026-05-10",
                    "overshoot_kcal": 300,
                    "private_note": "private rescue story",
                },
                "body_plan_context": {
                    "target_days_count": 5,
                    "safety_floor_kcal": 1200,
                    "debug": "hidden body plan detail",
                },
            },
        },
        "runtime_effect_allowed": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "manager_context_injected": False,
        "proactive_sent": False,
        "recommendation_served": False,
    }


def _default_model_response() -> dict[str, object]:
    return {
        "proposal_headline": "Recover the rest of the week with a small adjustment.",
        "proposal_summary": "Use a review-only two-day offset and keep the tone neutral.",
        "coaching_frame": "Frame this as planning, not punishment.",
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
        "claim_scope": "diagnostic_copy_only",
        "action_request": False,
        "delivery_request": False,
        "mutation_request": False,
        "reason_codes": ["future_oriented", "no_shame", "review_only"],
    }
