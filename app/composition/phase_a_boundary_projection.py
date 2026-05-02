from __future__ import annotations

from typing import Any

from app.composition.current_budget_answer import RemainingBudgetAnswerContract
from app.intake.application.state_transition import determine_meal_status
from app.nutrition.application.followup_policy import annotate_followup_policy
from app.runtime.application.execution_guard import evaluate_macro_display
from app.runtime.contracts.phase_a import (
    ClarificationDecision,
    CommitBoundaryDecision,
    FallbackHonestyDecision,
    PhaseABoundaryProjection,
)
from app.shared.contracts.intake_results import EstimatePayload


def _result_field(result: Any | None, field_name: str) -> Any:
    if result is None:
        return None
    if isinstance(result, dict):
        return result.get(field_name)
    return getattr(result, field_name, None)


def _build_followup_projection(payload: EstimatePayload) -> ClarificationDecision:
    parsed = annotate_followup_policy(
        {
            "action_taken": payload.action_taken,
            "estimated_kcal": payload.estimated_kcal,
            "follow_up_needed": payload.follow_up_needed,
            "followup_question": payload.followup_question,
            "missing_slots": list(payload.trace_contract.get("missing_slots") or []),
            "blocking_slots": list(payload.trace_contract.get("blocking_slots") or []),
            "unresolved_info": list(payload.trace_contract.get("unresolved_info") or []),
            "reasoning_state": dict(payload.reasoning_state or {}),
            "follow_up_reasoning": payload.follow_up_reasoning,
            "reason_not_direct_answer": str(payload.trace_contract.get("reason_not_direct_answer") or ""),
        }
    )
    response_mode_hint = str(payload.trace_contract.get("response_mode_hint") or "")
    action_taken = str(payload.action_taken or "")

    if action_taken == "clarify_before_estimate" or response_mode_hint == "clarify_first":
        mode = "clarify_before_estimate"
    elif str(parsed.get("followup_decision_type") or "") == "estimate_with_followup":
        mode = "estimate_with_followup"
    elif action_taken == "direct_answer" and not bool(parsed.get("follow_up_needed")):
        mode = "direct_commit"
    else:
        mode = "none"

    return ClarificationDecision(
        mode=mode,
        followup_required=bool(parsed.get("follow_up_needed")),
        followup_targets=[str(item) for item in parsed.get("followup_targets", []) if str(item).strip()],
        provisional_range_allowed=mode in {"direct_commit", "estimate_with_followup"},
    )


def _build_commit_projection(
    payload: EstimatePayload,
    *,
    persistence_result: Any | None,
) -> tuple[CommitBoundaryDecision, str, list[str], dict[str, Any]]:
    trace_contract = dict(payload.trace_contract or {})
    response_mode_hint = str(trace_contract.get("response_mode_hint") or "")
    blocking_slots = [str(item) for item in trace_contract.get("blocking_slots", []) if str(item).strip()]
    canonical_write_decision = dict(trace_contract.get("canonical_write_decision") or {})
    if "can_write_canonical" not in canonical_write_decision:
        canonical_write_decision["can_write_canonical"] = (
            int(payload.estimated_kcal or 0) > 0
            and not blocking_slots
            and response_mode_hint != "clarify_first"
        )
        canonical_write_decision["source"] = "phase_a_legality_projection"
    elif blocking_slots or response_mode_hint == "clarify_first":
        canonical_write_decision["can_write_canonical"] = False
        canonical_write_decision["source"] = "phase_a_legality_blocker"
    trace_contract["canonical_write_decision"] = canonical_write_decision

    predicted_status = determine_meal_status(
        payload_action_taken=payload.action_taken,
        payload_route_target=payload.route_target,
        estimated_kcal=payload.estimated_kcal,
        trace_contract=trace_contract,
        quality_signals=payload.quality_signals,
    )
    predicted_status_value = str(predicted_status or "none")
    canonical_write_allowed = canonical_write_decision.get("can_write_canonical", predicted_status_value == "completed_meal") is not False

    if predicted_status_value == "completed_meal" and canonical_write_allowed:
        intent = "commit"
    elif predicted_status_value in {"candidate_meal", "draft_unresolved"}:
        intent = "draft"
    else:
        intent = "no_mutation"

    macro_guard = evaluate_macro_display(
        estimated_kcal=int(payload.estimated_kcal or 0),
        protein_g=int(payload.protein_g or 0),
        carb_g=int(payload.carb_g or 0),
        fat_g=int(payload.fat_g or 0),
    )
    decision = CommitBoundaryDecision(
        intent=intent,
        predicted_meal_status=predicted_status_value,  # type: ignore[arg-type]
        canonical_write_allowed=bool(canonical_write_allowed),
        ledger_mutation_allowed=intent == "commit" and bool(canonical_write_allowed),
        macro_visible_allowed=predicted_status_value == "completed_meal" and macro_guard.display_status == "show",
    )

    observed_commit = bool(_result_field(persistence_result, "canonical_commit"))
    observed_action = str(_result_field(persistence_result, "action") or "")
    consistency_flags: list[str] = []
    if persistence_result is None:
        alignment = "not_applicable"
    elif decision.ledger_mutation_allowed and not observed_commit:
        alignment = "contradictory"
        consistency_flags.append("commit_boundary_persistence_mismatch")
    elif not decision.ledger_mutation_allowed and observed_commit:
        alignment = "contradictory"
        consistency_flags.append("commit_boundary_persistence_mismatch")
    elif decision.intent == "draft" and observed_action == "save_completed_log":
        alignment = "contradictory"
        consistency_flags.append("commit_boundary_persistence_mismatch")
    else:
        alignment = "aligned"

    legacy_projection = {
        "canonical_commit_allowed": decision.canonical_write_allowed,
        "canonical_commit": observed_commit if persistence_result is not None else None,
    }
    return decision, alignment, consistency_flags, legacy_projection


def _build_intake_fallback_projection(*, active_body_plan_present: bool) -> FallbackHonestyDecision:
    return FallbackHonestyDecision(
        budget_answer_mode="not_applicable",
        concrete_remaining_kcal_allowed=False,
        onboarding_guidance_allowed=not active_body_plan_present,
        intake_allowed_without_plan=True,
    )


def build_intake_boundary_projection(
    *,
    payload: EstimatePayload,
    persistence_result: Any | None,
    active_body_plan_present: bool,
) -> PhaseABoundaryProjection:
    clarification_decision = _build_followup_projection(payload)
    commit_boundary_decision, owner_alignment, consistency_flags, legacy_projection = _build_commit_projection(
        payload,
        persistence_result=persistence_result,
    )
    fallback_honesty_decision = _build_intake_fallback_projection(active_body_plan_present=active_body_plan_present)
    legacy_projection.update(
        {
            "clarify_mode": clarification_decision.mode,
            "budget_answer_mode": fallback_honesty_decision.budget_answer_mode,
        }
    )
    return PhaseABoundaryProjection(
        clarification_decision=clarification_decision,
        commit_boundary_decision=commit_boundary_decision,
        fallback_honesty_decision=fallback_honesty_decision,
        owner_alignment=owner_alignment,  # type: ignore[arg-type]
        consistency_flags=consistency_flags,
        legacy_projection=legacy_projection,
    )


def build_budget_boundary_projection(
    *,
    remaining_budget: RemainingBudgetAnswerContract,
    active_body_plan_present: bool,
    observed_reply_text: str | None = None,
) -> PhaseABoundaryProjection:
    degraded = remaining_budget.status == "onboarding_required" or not active_body_plan_present
    fallback_honesty_decision = FallbackHonestyDecision(
        budget_answer_mode="degraded" if degraded else "ready",
        concrete_remaining_kcal_allowed=not degraded,
        onboarding_guidance_allowed=degraded,
        intake_allowed_without_plan=True,
    )
    consistency_flags: list[str] = []
    owner_alignment = "aligned"
    remaining_kcal = remaining_budget.remaining_kcal
    if (
        degraded
        and remaining_kcal is not None
        and observed_reply_text
        and str(remaining_kcal)
        and str(remaining_kcal) in observed_reply_text
    ):
        owner_alignment = "contradictory"
        consistency_flags.append("degraded_budget_specific_remaining_exposed")
    return PhaseABoundaryProjection(
        clarification_decision=ClarificationDecision(mode="none"),
        commit_boundary_decision=CommitBoundaryDecision(intent="no_mutation", predicted_meal_status="none"),
        fallback_honesty_decision=fallback_honesty_decision,
        owner_alignment=owner_alignment,  # type: ignore[arg-type]
        consistency_flags=consistency_flags,
        legacy_projection={
            "clarify_mode": "none",
            "canonical_commit_allowed": False,
            "canonical_commit": None,
            "budget_answer_mode": fallback_honesty_decision.budget_answer_mode,
        },
    )


def attach_boundary_projection(
    phase_a_trace: dict[str, Any] | None,
    projection: PhaseABoundaryProjection,
) -> dict[str, Any]:
    updated = dict(phase_a_trace or {})
    updated["boundary_projection"] = projection.model_dump(mode="json")
    return updated


__all__ = [
    "attach_boundary_projection",
    "build_budget_boundary_projection",
    "build_intake_boundary_projection",
]
