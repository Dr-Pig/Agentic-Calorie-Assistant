"""
Final Response Pass - User-facing reply generation.

Responsibilities:
- Generate natural language reply from structured results
- Decide on follow-up questions
- Ensure reply consistency with nutrition results

Best Practices:
- Does NOT change nutrition values
- Follows strict output format
- Sanitizes all LLM output before use
"""

from __future__ import annotations

from typing import Any

from ...agent.final_response_llm import (
    FINAL_RESPONSE_PROMPT,
    fallback_final_response_result,
    normalize_final_response_result,
    sanitize_final_response_result,
)
from ...agent.nutrition_resolution_llm import _normalize_confidence
from ...application.context_assembly import build_four_pass_final_response_payload
from ...application.pass_runner import run_pass
from .base import run_text_stage


PRIMARY_MAX_TOKENS = 8192


async def run_final_response_pass(
    provider: Any,
    request_id: str,
    user_input: str,
    task_meal_link_result: Any,
    decision_result: Any,
    nutrition_result: Any,
    active_meal_summary: dict[str, Any],
    llm_traces: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], bool]:
    """
    Execute the final response pass.

    Returns:
        tuple: (final_response_result, asked_follow_up)
    """
    llm_traces = llm_traces or []

    payload = build_four_pass_final_response_payload(
        user_input=user_input,
        task_meal_link_result=task_meal_link_result,
        decision_result=decision_result,
        nutrition_result=nutrition_result,
        active_meal_summary=active_meal_summary,
    )

    fallback = fallback_final_response_result(
        user_input=user_input,
        primary_result={
            "answer_payload": dict(getattr(nutrition_result, "answer_payload", {}) or {}),
            "unresolved_info": list(getattr(nutrition_result, "unresolved_info", []) or []),
            "response_mode_hint": (
                "clarify_first"
                if str(getattr(nutrition_result, "resolution_mode", "")) == "cannot_estimate_yet"
                else "rough_estimate_ok"
            ),
        },
    )

    final_result, _ = await run_pass(
        provider=provider,
        stage="final_response_pass",
        system_prompt=FINAL_RESPONSE_PROMPT,
        user_payload=payload,
        max_tokens=PRIMARY_MAX_TOKENS,
        fallback_result=fallback,
        normalize=normalize_final_response_result,
        dump=lambda r: r.model_dump(mode="json"),
        run_stage=run_text_stage,
        request_id=request_id,
        llm_traces=llm_traces,
        trigger_reason="final_response_four_pass",
        handoff_contract={
            "meal_link_action": getattr(task_meal_link_result, "meal_link_action", ""),
            "next_action": getattr(decision_result, "next_action", ""),
            "resolution_mode": getattr(nutrition_result, "resolution_mode", ""),
        },
        required_fields=["reply_text", "asked_follow_up"],
        required_fields_source="normalized",
    )

    # Sanitize against zero-kcal markers
    sanitized = sanitize_final_response_result(
        result=final_result,
        nutrition_result=nutrition_result,
        fallback=fallback,
    )

    return sanitized, sanitized.asked_follow_up
