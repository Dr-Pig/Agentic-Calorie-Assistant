from __future__ import annotations

from app.runtime.contracts.proactive_gate import ProactiveGateInput, ProactiveGateResult
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("runtime.application.proactive_deterministic_gate")


def evaluate_proactive_deterministic_gate(gate_input: ProactiveGateInput) -> ProactiveGateResult:
    trace = {
        "llm_called": False,
        "scheduler_started": False,
        "message_sent": False,
        "checked_trigger_type": gate_input.trigger_type,
    }

    if not gate_input.user_allows_proactive:
        return _suppressed("user_proactive_disabled", trace)

    if gate_input.trigger_type in set(gate_input.suppressed_trigger_types):
        return _suppressed("suppressed_trigger_type", trace)

    if _inside_quiet_hours(
        gate_input.local_time,
        gate_input.quiet_hours_start,
        gate_input.quiet_hours_end,
    ):
        return _suppressed("quiet_hours", trace)

    if gate_input.now is not None and gate_input.cooldown_until is not None:
        if gate_input.now < gate_input.cooldown_until:
            return _suppressed("cooldown_active", trace)

    if gate_input.max_recent_send_count is not None:
        if gate_input.recent_send_count >= gate_input.max_recent_send_count:
            return _suppressed("recent_send_cap", trace)

    if not gate_input.minimum_evidence_ready:
        return _suppressed("minimum_evidence_missing", trace)

    if not gate_input.minimum_quality_ready:
        return _suppressed("minimum_quality_missing", trace)

    return ProactiveGateResult(
        allowed=True,
        status="allowed",
        skip_reason=None,
        trace=trace,
    )


def _suppressed(skip_reason: str, trace: dict[str, object]) -> ProactiveGateResult:
    return ProactiveGateResult(
        allowed=False,
        status="suppressed",
        skip_reason=skip_reason,
        trace=trace,
    )


def _inside_quiet_hours(
    local_time: str | None,
    quiet_hours_start: str | None,
    quiet_hours_end: str | None,
) -> bool:
    if not local_time or not quiet_hours_start or not quiet_hours_end:
        return False

    current = _parse_hh_mm(local_time)
    start = _parse_hh_mm(quiet_hours_start)
    end = _parse_hh_mm(quiet_hours_end)

    if start == end:
        return False
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _parse_hh_mm(value: str) -> int:
    try:
        hour_text, minute_text = value.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected HH:MM time, got {value!r}") from exc
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"Expected HH:MM time, got {value!r}")
    return hour * 60 + minute
