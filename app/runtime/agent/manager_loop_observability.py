from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from app.runtime.agent.manager_payload_utils import json_safe


def with_phase_a_repair_trace(
    guard_outcome: dict[str, Any],
    *,
    repair_attempted: bool,
    repair_result: str,
) -> dict[str, Any]:
    updated = dict(guard_outcome)
    preflight = updated.get("phase_a_transition_guard_preflight")
    if isinstance(preflight, dict):
        updated["phase_a_transition_guard_preflight"] = {
            **preflight,
            "repair_attempted": repair_attempted,
            "repair_result": repair_result,
        }
    return updated


@dataclass
class ManagerLoopObservability:
    started_at: float = field(default_factory=perf_counter)
    call_topology: list[dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def start() -> float:
        return perf_counter()

    @staticmethod
    def elapsed_ms(started_at: float) -> int:
        return max(0, int(round((perf_counter() - started_at) * 1000)))

    def record_provider_round(self, stage: str, round_index: int, started_at: float) -> int:
        latency_ms = self.elapsed_ms(started_at)
        self.call_topology.append(
            {
                "operation": "manager_provider_round",
                "stage": stage,
                "round_index": round_index,
                "duration_ms": latency_ms,
            }
        )
        return latency_ms

    def record_tool_batch(self, *, round_index: int, tool_calls: list[dict[str, Any]], started_at: float) -> None:
        self.call_topology.append(
            {
                "operation": "tool_batch",
                "stage": "manager_tool_execution",
                "round_index": round_index,
                "duration_ms": self.elapsed_ms(started_at),
                "tool_names": [str(item.get("name") or item.get("tool_name") or "") for item in tool_calls],
                "tool_count": len(tool_calls),
            }
        )

    def record_guard(self, *, round_index: int, guard_outcome: dict[str, Any], started_at: float) -> None:
        self.call_topology.append(
            {
                "operation": "guard_check",
                "stage": "manager_transition_guard",
                "round_index": round_index,
                "duration_ms": self.elapsed_ms(started_at),
                "guard_ok": bool(guard_outcome.get("ok")),
                "failure_family": guard_outcome.get("failure_family"),
            }
        )

    def result_kwargs(self) -> dict[str, Any]:
        return {
            "call_topology": json_safe(self.call_topology),
            "total_latency_ms": self.elapsed_ms(self.started_at),
        }


__all__ = ["ManagerLoopObservability", "with_phase_a_repair_trace"]
