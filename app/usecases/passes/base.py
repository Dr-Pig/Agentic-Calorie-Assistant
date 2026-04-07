"""
Base classes and types for LLM Passes.

Best Practices:
- Each pass has a single responsibility
- Passes receive context and return structured results
- Tool calls are abstracted from pass logic
- Validation happens at pass boundaries
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar, Generic

from pydantic import BaseModel


class PassResult(BaseModel):
    """Base class for pass execution results."""
    success: bool = False
    data: dict[str, Any] = {}
    error: str | None = None
    fallback_used: bool = False


@dataclass(frozen=True)
class PassConfig:
    """Configuration for a pass."""
    name: str
    max_tokens: int = 2048
    temperature: float = 0.1
    timeout_seconds: int = 30


@dataclass
class PassContext:
    """
    Shared context passed through all passes.

    This object flows through the entire pipeline,
    allowing each pass to read and write state.
    """
    request_id: str
    user_id: str
    user_input: str
    allow_search: bool = True

    # State accumulated through passes
    planner_result: dict[str, Any] | None = None
    task_meal_link_result: dict[str, Any] | None = None
    decision_result: dict[str, Any] | None = None
    nutrition_result: dict[str, Any] | None = None
    final_response_result: dict[str, Any] | None = None

    # Evidence gathered
    retrieved_knowledge: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    used_search: bool = False
    search_query: str | None = None

    # Quality signals
    quality_signals: dict[str, Any] = field(default_factory=dict)
    debug_steps: list[dict[str, Any]] = field(default_factory=list)
    llm_traces: list[dict[str, Any]] = field(default_factory=list)

    # Conversation state
    conversation_state: dict[str, Any] | None = None
    canonical_meal_state: dict[str, Any] | None = None

    # Control flags
    retry_triggered: bool = False
    retry_reason: str | None = None


T = TypeVar("T", bound=PassResult)


def sanitize_confidence(value: Any) -> str:
    """Sanitize confidence value to one of: high, medium, low."""
    if value is None:
        return "low"
    normalized = str(value).strip().lower()
    if normalized in {"high", "medium", "low"}:
        return normalized
    if "high" in normalized and "low" not in normalized:
        return "high"
    if "low" in normalized and "high" not in normalized:
        return "low"
    return "medium"


def sanitize_literal(value: Any, valid_values: set[str], default: str) -> str:
    """Sanitize a literal value to one of the valid values."""
    if value is None:
        return default
    normalized = str(value).strip().lower()
    return normalized if normalized in valid_values else default


async def run_text_stage(
    p: Any,
    *,
    stage: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_tokens: int,
    attempt_index: int | None = None,
    trigger_reason: str | None = None,
    handoff_contract: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Shared LLM completion stage for all passes.

    Best Practices:
    - Single implementation prevents drift
    - Captures full trace for observability
    - Consistent error handling
    """
    raw, trace = await p.complete_with_trace(
        system_prompt=system_prompt,
        user_payload=user_payload,
        stage=stage,
        max_tokens=max_tokens,
    )
    merged = trace or {}
    if attempt_index is not None:
        merged = {"attempt_index": attempt_index, **merged}
    if trigger_reason:
        merged = {"trigger_reason": trigger_reason, **merged}
    if handoff_contract:
        merged = {"handoff_contract": handoff_contract, **merged}
    return raw or {}, merged
