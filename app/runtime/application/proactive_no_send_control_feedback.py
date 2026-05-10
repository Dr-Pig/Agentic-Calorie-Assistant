from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_no_send_control_feedback"
)

FALSE_FLAGS = {
    "runtime_effect_allowed": False,
    "proactive_sent": False,
    "scheduler_enabled": False,
    "live_delivery_allowed": False,
    "push_or_line_delivery_connected": False,
    "manager_context_injected": False,
    "manager_context_packet_changed": False,
    "recommendation_served": False,
    "rescue_committed": False,
    "proposal_committed": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "meal_thread_mutated": False,
    "durable_memory_written": False,
    "durable_snooze_written": False,
    "mutation_changed": False,
    "user_facing_behavior_changed": False,
}


def evaluate_no_send_control_feedback(
    *,
    trigger_type: str,
    prior_interactions: list[Mapping[str, Any]],
    observed_signals: list[str],
    explicit_trigger_opt_out: bool = False,
) -> dict[str, Any]:
    matched, ignored = _matched_interactions(trigger_type, prior_interactions)
    next_signal = _latest_next_signal(matched)
    observed = _first_observed_signal(next_signal, observed_signals)
    reasons = _suppression_reasons(
        explicit_trigger_opt_out=explicit_trigger_opt_out,
        matched=matched,
        next_signal=next_signal,
        next_signal_observed=observed,
    )
    return {
        "artifact_type": "proactive_no_send_control_feedback",
        "artifact_schema_version": "1.0",
        "status": "suppressed" if reasons else "not_suppressed",
        "owner": "app/runtime",
        "consumer": "future_proactive_no_send_shadow_simulation",
        "retirement_trigger": "approved_proactive_scheduler_runtime_activation_plan",
        "trigger_type": trigger_type,
        "matched_interaction_count": len(matched),
        "ignored_interaction_count": ignored,
        "suppression_reasons": reasons,
        "review_decision": _review_decision(
            reasons,
            explicit_trigger_opt_out=explicit_trigger_opt_out,
        ),
        "next_signal_required": next_signal,
        "next_signal_observed": observed,
        "non_claims": [
            "not_durable_suppression",
            "not_scheduler_state",
            "not_user_facing_delivery",
            "not_runtime_mutation",
        ],
        **dict(FALSE_FLAGS),
    }


def _matched_interactions(
    trigger_type: str,
    prior_interactions: list[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], int]:
    matched: list[Mapping[str, Any]] = []
    ignored = 0
    for interaction in prior_interactions:
        if interaction.get("artifact_type") != "proactive_no_send_interaction_model_artifact":
            ignored += 1
            continue
        if interaction.get("status") != "pass":
            ignored += 1
            continue
        if str(interaction.get("trigger_type") or "") != trigger_type:
            ignored += 1
            continue
        if interaction.get("action") == "dismiss":
            matched.append(interaction)
            continue
        ignored += 1
    return matched, ignored


def _latest_next_signal(interactions: list[Mapping[str, Any]]) -> str:
    for interaction in reversed(interactions):
        signal = str(interaction.get("next_signal_required") or "").strip()
        if signal:
            return signal
    return ""


def _first_observed_signal(next_signal: str, observed_signals: list[str]) -> str | None:
    observed = {str(signal) for signal in observed_signals}
    return next_signal if next_signal and next_signal in observed else None


def _suppression_reasons(
    *,
    explicit_trigger_opt_out: bool,
    matched: list[Mapping[str, Any]],
    next_signal: str,
    next_signal_observed: str | None,
) -> list[str]:
    if explicit_trigger_opt_out:
        return ["explicit_trigger_opt_out"]
    if matched and next_signal and next_signal_observed is None:
        return ["recent_dismiss_without_next_signal"]
    return []


def _review_decision(
    reasons: list[str],
    *,
    explicit_trigger_opt_out: bool,
) -> dict[str, str]:
    if explicit_trigger_opt_out:
        return {
            "status": "suppressed_feedback",
            "reviewer_next_step": "respect_trigger_opt_out",
        }
    if reasons:
        return {
            "status": "suppressed_feedback",
            "reviewer_next_step": "keep_silent_until_next_signal",
        }
    return {
        "status": "candidate_for_human_review",
        "reviewer_next_step": "review_context_before_live_plan",
    }


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "evaluate_no_send_control_feedback"]
