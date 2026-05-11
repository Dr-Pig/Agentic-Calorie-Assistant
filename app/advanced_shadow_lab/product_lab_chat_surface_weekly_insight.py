from __future__ import annotations

from typing import Any, Mapping


def weekly_insight_report(packet: Mapping[str, Any]) -> dict[str, Any]:
    if str(packet.get("trigger_type") or "") != "weekly_insight":
        return {}
    return dict(_mapping(packet.get("weekly_insight_report")))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["weekly_insight_report"]
