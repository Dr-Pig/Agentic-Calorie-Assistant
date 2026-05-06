from __future__ import annotations

from typing import Any

_SUMMARY_MINIMUMS = (
    ("inventory_backed_tool_count", 10, "inventory_backed_tool_count_too_low", "inventory backed count too low"),
    ("read_only_tool_count", 7, "read_only_tool_count_too_low", "read-only count too low"),
    ("direct_lane_bridge_count", 7, "direct_lane_bridge_count_too_low", "direct lane bridge count too low"),
)


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary")
    return dict(value) if isinstance(value, dict) else {}


def pre_live_contract_blockers(payload: dict[str, Any]) -> list[str]:
    summary = _summary(payload)
    return [
        f"non_fooddb_manager_tool_contract_{suffix}"
        for key, minimum, suffix, _ in _SUMMARY_MINIMUMS
        if int(summary.get(key) or 0) < minimum
    ]


def candidate_contract_blockers(payload: dict[str, Any]) -> list[str]:
    summary = _summary(payload)
    return [
        f"non-fooddb manager tool contract {message}"
        for key, minimum, _, message in _SUMMARY_MINIMUMS
        if int(summary.get(key) or 0) < minimum
    ]


__all__ = [
    "candidate_contract_blockers",
    "pre_live_contract_blockers",
]
