from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import DecisionNextAction, PassExecutionStatus


class ToolCallRequest(BaseModel):
    tool_name: Literal[
        "resolve_exact_item",
        "get_meal_calibration",
        "resolve_ingredient_anchors",
        "search_official_nutrition",
        "read_official_doc_fragment",
        "extract_nutrition_table_fragment",
    ]
    query: str = ""
    identity_target: str | None = None
    reason: str = ""
    allowed_source_class: list[str] = Field(default_factory=list)
    extraction_target: str | None = None


class ToolCallResult(BaseModel):
    tool_name: str
    status: Literal["selected", "executed", "skipped", "not_needed"] = "selected"
    reason: str = ""
    latency_ms: int | None = None
    quality: Literal["high", "medium", "low", "unknown"] = "unknown"
    result_count: int = 0


class ToolRoutingDecision(BaseModel):
    next_action: DecisionNextAction = "run_clarify"
    tool_plan: Literal[
        "none",
        "resolve_exact_item",
        "get_meal_calibration",
        "resolve_ingredient_anchors",
        "search_official_nutrition",
        "read_official_doc_fragment",
    ] = "none"
    decision_confidence: Literal["high", "medium", "low"] = "low"
    tool_query_override: str | None = None
    tool_goal: str = ""
    missing_evidence_type: str = ""
    expected_success_condition: str = ""
    clarify_priority: str | None = None
    unresolved_info: list[str] = Field(default_factory=list)
    response_mode_hint: Literal["exact_answer", "rough_estimate_ok", "clarify_first"] = "rough_estimate_ok"
    clarify_is_blocking: bool = False
    can_proceed_without_clarify: bool = False


class ExecutionEnvelope(BaseModel):
    status: PassExecutionStatus = "failed"
    payload: dict[str, Any] = Field(default_factory=dict)
    fallback_used: bool = False
    error: str | None = None
