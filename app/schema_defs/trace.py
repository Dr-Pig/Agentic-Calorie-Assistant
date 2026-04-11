from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import LogicalModelRole, StageTraceStatus
from .intake import ToolCallRequest, ToolCallResult


class ContextPackTrace(BaseModel):
    sections: list[dict[str, Any]] = Field(default_factory=list)
    total_estimated_tokens: int = 0


class ToolDecisionTrace(BaseModel):
    available_tools: list[str] = Field(default_factory=list)
    candidate_tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    executed_tool_calls: list[ToolCallResult] = Field(default_factory=list)


class StageTraceEvent(BaseModel):
    request_id: str
    stage: str
    status: StageTraceStatus = "ok"
    attempt_index: int = 1
    provider: str | None = None
    provider_role: str | None = None
    logical_model_role: LogicalModelRole
    model_id: str | None = None
    timestamp: str
    trigger_reason: str | None = None
    fallback_mode: str | None = None
