from __future__ import annotations

from dataclasses import dataclass

from app.budget.application.current_budget_answer import RemainingBudgetAnswerContract
from app.intake.application.phase_a_boundary_projection import (
    build_budget_boundary_projection,
    build_intake_boundary_projection,
)
from app.shared.contracts.intake_results import EstimatePayload


@dataclass(frozen=True)
class _PersistenceResult:
    action: str | None = None
    canonical_commit: dict | None = None


def _payload(
    *,
    meal_title: str,
    estimated_kcal: int,
    action_taken: str,
    follow_up_needed: bool = False,
    followup_question: str | None = None,
    response_mode_hint: str = "rough_estimate_ok",
    missing_slots: list[str] | None = None,
    unresolved_info: list[str] | None = None,
    canonical_write_allowed: bool = True,
) -> EstimatePayload:
    return EstimatePayload(
        request_id="req-1",
        meal_title=meal_title,
        estimated_kcal=estimated_kcal,
        action_taken=action_taken,
        follow_up_needed=follow_up_needed,
        followup_question=followup_question,
        route_target="clarify_user_private" if action_taken == "clarify_before_estimate" else "direct_answer",
        trace_contract={
            "response_mode_hint": response_mode_hint,
            "missing_slots": list(missing_slots or []),
            "unresolved_info": list(unresolved_info or []),
            "followup_question": followup_question,
            "canonical_write_decision": {
                "can_write_canonical": canonical_write_allowed,
            },
        },
        reasoning_state={
            "missing_high_impact_slots": list(missing_slots or []),
        },
    )


def test_pearl_milk_tea_turn_one_projects_estimate_with_followup_draft() -> None:
    payload = _payload(
        meal_title="pearl milk tea",
        estimated_kcal=450,
        action_taken="answer_with_uncertainty",
        follow_up_needed=True,
        followup_question="What size and sugar level was it?",
        response_mode_hint="rough_estimate_ok",
        missing_slots=["size", "sugar_level"],
        canonical_write_allowed=False,
    )

    projection = build_intake_boundary_projection(
        payload=payload,
        persistence_result=_PersistenceResult(action="save_draft_log", canonical_commit=None),
        active_body_plan_present=True,
    )

    assert projection.clarification_decision.mode == "estimate_with_followup"
    assert projection.clarification_decision.followup_required is True
    assert projection.clarification_decision.provisional_range_allowed is True
    assert projection.commit_boundary_decision.intent == "draft"
    assert projection.commit_boundary_decision.predicted_meal_status == "draft_unresolved"
    assert projection.commit_boundary_decision.canonical_write_allowed is False
    assert projection.commit_boundary_decision.ledger_mutation_allowed is False
    assert projection.owner_alignment == "aligned"
    assert projection.legacy_projection["clarify_mode"] == "estimate_with_followup"


def test_homemade_dish_projects_clarify_before_estimate() -> None:
    payload = _payload(
        meal_title="home cooked dish",
        estimated_kcal=0,
        action_taken="clarify_before_estimate",
        follow_up_needed=True,
        followup_question="What dishes or ingredients and how much?",
        response_mode_hint="clarify_first",
        unresolved_info=["dishes_or_ingredients", "portion"],
        canonical_write_allowed=False,
    )

    projection = build_intake_boundary_projection(
        payload=payload,
        persistence_result=_PersistenceResult(action="save_draft_log", canonical_commit=None),
        active_body_plan_present=True,
    )

    assert projection.clarification_decision.mode == "clarify_before_estimate"
    assert projection.clarification_decision.followup_required is True
    assert projection.clarification_decision.provisional_range_allowed is False
    assert projection.commit_boundary_decision.intent == "draft"
    assert projection.commit_boundary_decision.predicted_meal_status == "draft_unresolved"


def test_simple_meal_projects_direct_commit() -> None:
    payload = _payload(
        meal_title="rice and vegetables",
        estimated_kcal=320,
        action_taken="direct_answer",
        follow_up_needed=False,
        response_mode_hint="exact_answer",
        canonical_write_allowed=True,
    )

    projection = build_intake_boundary_projection(
        payload=payload,
        persistence_result=_PersistenceResult(
            action="save_completed_log",
            canonical_commit={"meal_thread_id": 10},
        ),
        active_body_plan_present=True,
    )

    assert projection.clarification_decision.mode == "direct_commit"
    assert projection.commit_boundary_decision.intent == "commit"
    assert projection.commit_boundary_decision.predicted_meal_status == "completed_meal"
    assert projection.commit_boundary_decision.canonical_write_allowed is True
    assert projection.commit_boundary_decision.ledger_mutation_allowed is True
    assert projection.owner_alignment == "aligned"
    assert projection.legacy_projection["canonical_commit"] is True


def test_commit_projection_reports_persistence_contradiction_without_fixing_it() -> None:
    payload = _payload(
        meal_title="pearl milk tea",
        estimated_kcal=520,
        action_taken="direct_answer",
        canonical_write_allowed=True,
    )

    projection = build_intake_boundary_projection(
        payload=payload,
        persistence_result=_PersistenceResult(action="save_draft_log", canonical_commit=None),
        active_body_plan_present=True,
    )

    assert projection.commit_boundary_decision.intent == "commit"
    assert projection.owner_alignment == "contradictory"
    assert "commit_boundary_persistence_mismatch" in projection.consistency_flags


def test_no_plan_intake_is_allowed_but_budget_mode_is_not_applicable() -> None:
    payload = _payload(
        meal_title="tea egg",
        estimated_kcal=70,
        action_taken="direct_answer",
        canonical_write_allowed=True,
    )

    projection = build_intake_boundary_projection(
        payload=payload,
        persistence_result=_PersistenceResult(action="save_completed_log", canonical_commit={"meal_thread_id": 1}),
        active_body_plan_present=False,
    )

    assert projection.fallback_honesty_decision.intake_allowed_without_plan is True
    assert projection.fallback_honesty_decision.budget_answer_mode == "not_applicable"


def test_no_plan_budget_query_projects_degraded_budget_mode() -> None:
    answer = RemainingBudgetAnswerContract(
        status="onboarding_required",
        user_id=1,
        local_date="2026-04-29",
        daily_target_kcal=0,
        consumed_kcal=600,
        remaining_kcal=0,
        meal_count=2,
    )

    projection = build_budget_boundary_projection(
        remaining_budget=answer,
        active_body_plan_present=False,
    )

    assert projection.fallback_honesty_decision.budget_answer_mode == "degraded"
    assert projection.fallback_honesty_decision.concrete_remaining_kcal_allowed is False
    assert projection.fallback_honesty_decision.onboarding_guidance_allowed is True
    assert projection.fallback_honesty_decision.intake_allowed_without_plan is True
    assert projection.owner_alignment == "aligned"
    assert projection.legacy_projection["budget_answer_mode"] == "degraded"
