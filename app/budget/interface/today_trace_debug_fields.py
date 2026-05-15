from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestDebugFields:
    request_id: str
    trace_link: str
    text: str


@dataclass(frozen=True)
class PayloadDebugFields:
    estimated_kcal: int
    route_target: str
    action_taken: str


@dataclass(frozen=True)
class ManagerDecisionDebugFields:
    should_render: bool
    clarify_posture: str
    final_action: str


@dataclass(frozen=True)
class EvidenceDebugFields:
    eligibility: str
    why_not_exact: str


@dataclass(frozen=True)
class MacroDebugFields:
    macro_display: str
    macro_reason: str


@dataclass(frozen=True)
class LatencyDebugFields:
    latency_total_ms: int
    slowest_step_name: str


@dataclass(frozen=True)
class TraceDebugFields:
    label: str
    request: RequestDebugFields
    payload: PayloadDebugFields
    manager: ManagerDecisionDebugFields
    evidence: EvidenceDebugFields
    macro: MacroDebugFields
    latency: LatencyDebugFields


__all__ = [
    "EvidenceDebugFields",
    "LatencyDebugFields",
    "MacroDebugFields",
    "ManagerDecisionDebugFields",
    "PayloadDebugFields",
    "RequestDebugFields",
    "TraceDebugFields",
]
