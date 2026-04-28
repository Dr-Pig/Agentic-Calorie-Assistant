from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PrimaryManagerDecision:
    intent_type: str
    workflow_effect: str
    response_summary: str
    pending_followup: str | None = None
    tool_calls: tuple[str, ...] = field(default_factory=tuple)
    llm_used: bool = False
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Bundle2ManagerDecision1:
    intent_type: str
    clarify_posture: str
    tool_plan: tuple[str, ...]
    target_attachment: dict[str, Any]
    pending_followup_resolution_mode: str | None = None
    workflow_effect: str = "none"
    llm_used: bool = False
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Bundle2ManagerDecision2:
    final_action: str
    workflow_effect: str
    llm_used: bool = False
    trace: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "PrimaryManagerDecision",
    "Bundle2ManagerDecision1",
    "Bundle2ManagerDecision2",
]
