from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_calibration_packets import (
    with_calibration_chat_packet,
)
from app.advanced_shadow_lab.product_lab_exercise_packets import (
    with_exercise_budget_chat_packet,
)
from app.advanced_shadow_lab.product_lab_no_plan_packets import (
    with_no_plan_degraded_chat_packets,
)
from app.advanced_shadow_lab.product_lab_planned_event_packets import (
    with_planned_event_chat_packet,
    with_planned_event_guidance_chat_packet,
)
from app.advanced_shadow_lab.product_lab_swap_packets import (
    with_swap_suggestion_chat_packet,
)
from app.advanced_shadow_lab.product_lab_weekly_insight_packets import (
    with_weekly_insight_chat_packet,
)


def product_chat_packets(
    allowed_packets: list[Mapping[str, Any]],
    *,
    recommendation: Mapping[str, Any],
    calibration: Mapping[str, Any],
    no_plan_degraded: Mapping[str, Any],
    planned_event_guidance: Mapping[str, Any],
    planned_event_rescue: Mapping[str, Any],
    exercise_budget: Mapping[str, Any],
    weekly_insight: Mapping[str, Any],
    proactive: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    packets = with_swap_suggestion_chat_packet(allowed_packets, recommendation)
    packets = with_calibration_chat_packet(packets, calibration)
    packets = with_planned_event_guidance_chat_packet(packets, planned_event_guidance)
    packets = with_planned_event_chat_packet(packets, planned_event_rescue)
    packets = with_exercise_budget_chat_packet(packets, exercise_budget)
    packets = with_weekly_insight_chat_packet(packets, weekly_insight, proactive)
    return with_no_plan_degraded_chat_packets(packets, no_plan_degraded)


def product_outputs_applied(artifacts: list[Mapping[str, Any] | None]) -> bool:
    return any(bool(artifact) for artifact in artifacts)


def product_lab_runtime_capabilities(
    *,
    memory_pack: Mapping[str, Any],
    packet: Mapping[str, Any],
    calibration: Mapping[str, Any],
    no_plan_degraded: Mapping[str, Any],
    planned_event_guidance: Mapping[str, Any],
    exercise_budget: Mapping[str, Any],
    weekly_insight: Mapping[str, Any],
) -> dict[str, bool]:
    return {
        "memory_tools_enabled": memory_pack.get("memory_tools_enabled") is True,
        "memory_context_injected": memory_pack.get("memory_context_injected") is True,
        "recommendation_served_to_lab": packet.get("status") == "pass",
        "rescue_served_to_lab": packet.get("status") == "pass",
        "calibration_served_to_lab": calibration.get("proposal_presented_to_lab") is True,
        "no_plan_degraded_served_to_lab": no_plan_degraded.get("status") == "pass",
        "planned_event_guidance_served_to_lab": planned_event_guidance.get("status") == "pass",
        "exercise_budget_served_to_lab": exercise_budget.get("status") == "pass",
        "weekly_insight_served_to_lab": weekly_insight.get("lab_chat_delivery_allowed") is True,
        "proactive_chat_packet_served_to_lab": packet.get("status") == "pass",
        "mainline_activation_enabled": False,
    }


__all__ = [
    "product_chat_packets",
    "product_lab_runtime_capabilities",
    "product_outputs_applied",
]
