from __future__ import annotations

from typing import Any


def manager_provider_round_count(react_trace: dict[str, Any]) -> int | None:
    call_topology = _list(react_trace.get("call_topology"))
    provider_rounds = [
        item for item in call_topology if _dict(item).get("operation") == "manager_provider_round"
    ]
    if provider_rounds:
        return len(provider_rounds)
    round_latencies = _list(react_trace.get("manager_round_latency_ms"))
    if not round_latencies:
        return None
    return sum(1 for latency_ms in round_latencies if int(latency_ms or 0) > 0)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []
