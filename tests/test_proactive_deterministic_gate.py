from datetime import datetime, timedelta, timezone

from app.runtime.application.proactive_deterministic_gate import (
    evaluate_proactive_deterministic_gate,
)
from app.runtime.contracts.proactive_gate import ProactiveGateInput


def test_quiet_hours_suppresses_cross_midnight_trigger() -> None:
    result = evaluate_proactive_deterministic_gate(
        ProactiveGateInput(
            trigger_type="dinner_recommendation",
            local_time="23:30",
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
        )
    )

    assert result.allowed is False
    assert result.status == "suppressed"
    assert result.skip_reason == "quiet_hours"


def test_suppression_takes_precedence_over_missing_evidence() -> None:
    result = evaluate_proactive_deterministic_gate(
        ProactiveGateInput(
            trigger_type="reflection_prompt",
            suppressed_trigger_types=["reflection_prompt"],
            minimum_evidence_ready=False,
        )
    )

    assert result.allowed is False
    assert result.skip_reason == "suppressed_trigger_type"


def test_cooldown_and_recent_send_cap_block_trigger() -> None:
    now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    cooldown_result = evaluate_proactive_deterministic_gate(
        ProactiveGateInput(
            trigger_type="rescue_followup",
            now=now,
            cooldown_until=now + timedelta(hours=2),
        )
    )
    recent_cap_result = evaluate_proactive_deterministic_gate(
        ProactiveGateInput(
            trigger_type="meal_reminder",
            recent_send_count=3,
            max_recent_send_count=3,
        )
    )

    assert cooldown_result.skip_reason == "cooldown_active"
    assert recent_cap_result.skip_reason == "recent_send_cap"


def test_minimum_evidence_gate_blocks_without_calling_llm() -> None:
    result = evaluate_proactive_deterministic_gate(
        ProactiveGateInput(
            trigger_type="dinner_recommendation",
            minimum_evidence_ready=False,
        )
    )

    assert result.allowed is False
    assert result.skip_reason == "minimum_evidence_missing"
    assert result.trace["llm_called"] is False


def test_minimum_quality_gate_blocks_without_scheduler_or_message_send() -> None:
    result = evaluate_proactive_deterministic_gate(
        ProactiveGateInput(
            trigger_type="dinner_recommendation",
            minimum_quality_ready=False,
        )
    )

    assert result.allowed is False
    assert result.skip_reason == "minimum_quality_missing"
    assert result.trace["scheduler_started"] is False
    assert result.trace["message_sent"] is False


def test_trigger_is_allowed_when_all_deterministic_checks_pass() -> None:
    result = evaluate_proactive_deterministic_gate(
        ProactiveGateInput(
            trigger_type="dinner_recommendation",
            local_time="18:30",
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
            minimum_evidence_ready=True,
        )
    )

    assert result.allowed is True
    assert result.status == "allowed"
    assert result.skip_reason is None
