from __future__ import annotations

from typing import Any

from .manager_decision_contract import PrimaryManagerDecision


def fallback_decision(
    *,
    raw_user_input: str,
    onboarding_payload: dict[str, Any] | None,
    onboarding_ready: bool,
) -> PrimaryManagerDecision:
    if onboarding_payload is not None:
        return PrimaryManagerDecision(
            intent_type="complete_onboarding",
            workflow_effect="seed_active_body_plan_and_day_budget",
            response_summary="Complete onboarding and seed the active body plan plus current-day budget.",
            tool_calls=("body.get_active_plan", "budget.get_today_summary"),
            llm_used=False,
            trace={"decision_source": "fallback_structured_onboarding"},
        )
    return PrimaryManagerDecision(
        intent_type="manager_unavailable",
        workflow_effect="safe_failure",
        response_summary="Manager provider is unavailable; no semantic decision was made.",
        tool_calls=(),
        llm_used=False,
        trace={"decision_source": "fallback_manager_unavailable_no_semantic_authority"},
    )


__all__ = [
    "PrimaryManagerDecision",
    "fallback_decision",
]
