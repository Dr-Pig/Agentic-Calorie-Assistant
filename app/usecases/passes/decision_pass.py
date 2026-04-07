"""
Decision Pass - Route decision and tool planning.

Responsibilities:
- Decide next action (clarify, resolve, lookup)
- Determine if clarification is blocking
- Choose appropriate tool plan

Best Practices:
- Does NOT produce nutrition answers
- Validates LLM output against strict schema
- Falls back to conservative clarification on failure
"""

from __future__ import annotations

from typing import Any

from ...agent.decision_llm import (
    DECISION_PROMPT,
    fallback_decision_result,
    normalize_decision_result,
)
from ...application.context_assembly import build_decision_payload
from ...application.evidence_assembly import (
    summarize_selected_evidence,
    tool_availability,
)
from ...application.pass_runner import run_pass
from ...schemas import DecisionPassResult
from .base import run_text_stage


PLANNER_MAX_TOKENS = 2048


async def run_decision_pass(
    provider: Any,
    request_id: str,
    user_input: str,
    task_meal_link_result: Any,
    canonical_meal_state: Any,
    filtered_knowledge: list[dict[str, Any]],
    request: Any,
    search_adapter: Any | None = None,
    llm_traces: list[dict[str, Any]] | None = None,
    debug_steps: list[dict[str, Any]] | None = None,
) -> tuple[DecisionPassResult, dict[str, Any]]:
    """
    Execute the decision pass.

    Returns:
        tuple: (decision_result, decision_payload)
    """
    llm_traces = llm_traces or []
    debug_steps = debug_steps or []

    available_tools = tool_availability(request, search_adapter=search_adapter)
    evidence_summary = summarize_selected_evidence(filtered_knowledge)

    fallback_decision = fallback_decision_result(meal_link_result=task_meal_link_result)
    decision_payload = build_decision_payload(
        user_input=user_input,
        meal_state=canonical_meal_state,
        meal_link_result=task_meal_link_result,
        selected_evidence_summary=evidence_summary,
        available_tools=available_tools,
    )

    decision_result, decision_envelope = await run_pass(
        provider=provider,
        stage="decision_pass",
        system_prompt=DECISION_PROMPT,
        user_payload=decision_payload,
        max_tokens=PLANNER_MAX_TOKENS,
        fallback_result=fallback_decision,
        normalize=lambda raw, fb: normalize_decision_result(dict(raw or {}), fallback=fb),
        dump=lambda r: r.model_dump(mode="json"),
        run_stage=run_text_stage,
        request_id=request_id,
        llm_traces=llm_traces,
        trigger_reason="decision_pass",
        handoff_contract={
            "meal_link_action": task_meal_link_result.meal_link_action,
            "target_meal_id": task_meal_link_result.target_meal_id,
            "selected_evidence_count": len(filtered_knowledge),
        },
        required_fields=["next_action", "tool_plan", "clarify_is_blocking", "can_proceed_without_clarify"],
        required_fields_source="normalized",
        nullable_required_fields=["clarify_priority"],
    )

    if decision_envelope.status != "success":
        debug_steps.append({
            "request_id": request_id,
            "step": "decision_pass",
            "error": decision_envelope.error,
        })

    return decision_result, decision_payload
