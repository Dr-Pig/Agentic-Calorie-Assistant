from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ManagerAction(str, Enum):
    call_tools = "call_tools"
    final = "final"

class IntentType(str, Enum):
    exact_lookup = "exact_lookup"
    estimate = "estimate"
    ask_followup = "ask_followup"
    correction = "correction"
    answer_budget = "answer_budget"
    answer_status = "answer_status"
    onboarding = "onboarding"

class Exactness(str, Enum):
    exact = "exact"
    anchored = "anchored"
    heuristic = "heuristic"
    unknown = "unknown"

class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class InternalAgentOutput(BaseModel):
    """The strictly typed contract that the LLM must output."""
    manager_action: ManagerAction
    intent: IntentType
    workflow_effect: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    final_action: str | None = None
    answer_contract: dict[str, Any] | None = None
    uncertainty_posture: str | None = None
    evidence_honesty_posture: str | None = None
    confidence: Confidence = Confidence.low
    exactness: Exactness = Exactness.unknown
    repair_ack: str | None = None  # Agent acknowledges repair instruction

class GuardResult(BaseModel):
    ok: bool
    repair_request: str | None = None
    failure_family: str | None = None
    details: list[str] = Field(default_factory=list)
    consumed_repair_budget: int = 0
