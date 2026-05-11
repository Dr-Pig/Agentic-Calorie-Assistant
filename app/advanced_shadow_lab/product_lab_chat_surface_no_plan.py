from __future__ import annotations

from typing import Any, Mapping


def no_plan_degraded(packet: Mapping[str, Any]) -> dict[str, Any]:
    data = _mapping(packet.get("no_plan_degraded_packet"))
    if not data:
        return {}
    return {
        "intake_packet": dict(_mapping(data.get("intake_packet"))),
        "budget_query_packet": dict(_mapping(data.get("budget_query_packet"))),
        "today_ui_mirror": dict(_mapping(data.get("today_ui_mirror"))),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["no_plan_degraded"]
