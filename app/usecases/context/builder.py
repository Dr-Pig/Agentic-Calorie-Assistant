"""
Context Builder - Assemble context for each LLM pass.

Responsibilities:
- Build structured context for each LLM pass
- Manage context size and token budget
- Format context consistently

Best Practices:
- Context is read-only from LLM perspective
- Each pass gets exactly what it needs
- Token budgets enforced before pass
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...application.context_assembly import (
    build_boundary_features,
    build_decision_payload,
    build_four_pass_final_response_payload,
    build_nutrition_resolution_payload,
    build_planner_context_payload,
    build_task_meal_link_payload,
    estimate_token_count,
    knowledge_context,
    render_conversation_state_prompt,
    risk_context,
)
from ...application.evidence_assembly import summarize_selected_evidence


@dataclass
class ContextBudget:
    """Token budget for a context."""
    max_tokens: int = 4000
    current_tokens: int = 0

    def can_fit(self, additional_tokens: int) -> bool:
        return (self.current_tokens + additional_tokens) <= self.max_tokens

    def add(self, tokens: int) -> None:
        self.current_tokens += tokens


class ContextBuilder:
    """
    Builds context for each LLM pass.

    Best Practices:
    - Pass-specific context building
    - Token budget awareness
    - Consistent formatting
    """

    def __init__(self, max_context_tokens: int = 4000):
        self.max_context_tokens = max_context_tokens

    def build_planner_context(
        self,
        user_input: str,
        thin_sanitized_input: str,
        allow_search: bool,
        conversation_state: Any,
    ) -> tuple[dict[str, Any], str]:
        """
        Build context for planner pass.

        Returns:
            tuple: (planner_payload, context_string)
        """
        # Build planner context payload
        payload = build_planner_context_payload(
            raw_user_input=user_input,
            thin_sanitized_input=thin_sanitized_input,
            allow_search=allow_search,
            state=conversation_state,
        )

        # Render conversation state as prompt
        context_str = render_conversation_state_prompt(conversation_state)

        return payload, context_str

    def build_task_meal_link_context(
        self,
        user_input: str,
        conversation_state: Any,
        meal_log_summaries: list[dict[str, Any]],
        boundary_features: dict[str, Any],
    ) -> dict[str, Any]:
        """Build context for task/meal link pass."""
        return build_task_meal_link_payload(
            user_input=user_input,
            state=conversation_state,
            meal_log_summaries=meal_log_summaries,
            boundary_features=boundary_features,
        )

    def build_decision_context(
        self,
        user_input: str,
        task_meal_link_result: Any,
        canonical_meal_state: Any,
        filtered_knowledge: list[dict[str, Any]],
        available_tools: list[str],
    ) -> dict[str, Any]:
        """Build context for decision pass."""
        evidence_summary = summarize_selected_evidence(filtered_knowledge)
        return build_decision_payload(
            user_input=user_input,
            meal_state=canonical_meal_state,
            meal_link_result=task_meal_link_result,
            selected_evidence_summary=evidence_summary,
            available_tools=available_tools,
        )

    def build_nutrition_resolution_context(
        self,
        user_input: str,
        task_meal_link_result: Any,
        decision_result: Any,
        normalized_evidence: list[dict[str, Any]],
        calibration_packet: dict[str, Any] | None,
        canonical_meal_state: Any,
        active_meal_context_allowed: bool,
        latest_log: Any | None,
    ) -> dict[str, Any]:
        """Build context for nutrition resolution pass."""
        payload = build_nutrition_resolution_payload(
            meal_state=canonical_meal_state,
            meal_link_result=task_meal_link_result,
            decision_result=decision_result,
            normalized_evidence=normalized_evidence,
            calibration_packet=calibration_packet,
            user_input=user_input,
        )
        # Add old components for continuation
        if latest_log and active_meal_context_allowed:
            payload["old_components"] = list(latest_log.components_json or [])
        else:
            payload["old_components"] = []
        return payload

    def build_final_response_context(
        self,
        user_input: str,
        task_meal_link_result: Any,
        decision_result: Any,
        nutrition_result: Any,
        active_meal_summary: dict[str, Any],
    ) -> dict[str, Any]:
        """Build context for final response pass."""
        return build_four_pass_final_response_payload(
            user_input=user_input,
            task_meal_link_result=task_meal_link_result,
            decision_result=decision_result,
            nutrition_result=nutrition_result,
            active_meal_summary=active_meal_summary,
        )

    def build_evidence_context(
        self,
        filtered_knowledge: list[dict[str, Any]],
        risk_packet: dict[str, Any],
    ) -> tuple[str, str]:
        """
        Build evidence and risk context strings.

        Returns:
            tuple: (evidence_context, risk_context)
        """
        evidence = knowledge_context(filtered_knowledge[:5])
        risk = risk_context(risk_packet)
        return evidence, risk

    def estimate_context_size(self, context: Any) -> int:
        """Estimate token count for a context object."""
        return estimate_token_count(context)


def build_audit_context(
    request: Any,
    request_id: str,
    debug_steps: list[dict[str, Any]],
    llm_traces: list[dict[str, Any]],
    quality_signals: dict[str, Any],
    trace_contract: dict[str, Any],
    token_usage: dict[str, Any],
) -> dict[str, Any]:
    """Build context for audit trail."""
    return {
        "request_id": request_id,
        "timestamp": None,  # Filled by caller
        "request": {
            "user_id": getattr(request, "user_id", "anonymous"),
            "text": request.text,
            "allow_search": request.allow_search,
        },
        "debug_steps": debug_steps,
        "llm_traces": llm_traces,
        "quality_signals": quality_signals,
        "trace_contract": trace_contract,
        "token_usage": token_usage,
    }
