from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.composition.state_resolver import _target_meal_reference, resolve_intake_state
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord
from app.models import Base
from app.schemas import CommitRequestCandidate, MealItemPayload


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _candidate(*, request_id: str, items: list[MealItemPayload] | None = None) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id=request_id,
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="pearl milk tea",
        raw_input="pearl milk tea",
        estimated_kcal=480,
        protein_g=4,
        carb_g=78,
        fat_g=16,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=items or [],
    )


def test_resolved_state_target_reference_includes_single_active_item_authority() -> None:
    db = _session()
    user = get_or_create_user(db, "single-item-target-ref")
    result = commit_meal_payload_to_canonical(db, user=user, candidate=_candidate(request_id="single-item"))
    assert result is not None
    item = db.execute(select(MealItemRecord)).scalar_one()

    state = resolve_intake_state(
        db,
        user_external_id="single-item-target-ref",
        local_date="2026-05-02",
        incoming_user_text="actually make that half sugar",
    )

    target = state.injected_context["TARGET_MEAL_REFERENCE"]
    assert target["meal_thread_id"] == result.meal_thread_id
    assert target["meal_version_id"] == result.meal_version_id
    assert target["meal_item_id"] == item.id
    assert target["canonical_name"] == "pearl milk tea"
    assert target["item_resolution_source"] == "single_active_item"


def test_resolved_state_target_reference_does_not_guess_item_for_multi_item_meal() -> None:
    db = _session()
    user = get_or_create_user(db, "multi-item-target-ref")
    result = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="multi-item",
            items=[
                MealItemPayload(name="rice", estimated_kcal=260),
                MealItemPayload(name="egg", estimated_kcal=90),
            ],
        ),
    )
    assert result is not None

    state = resolve_intake_state(
        db,
        user_external_id="multi-item-target-ref",
        local_date="2026-05-02",
        incoming_user_text="actually make that less rice",
    )

    target = state.injected_context["TARGET_MEAL_REFERENCE"]
    assert target["meal_thread_id"] == result.meal_thread_id
    assert "meal_item_id" not in target
    assert target["item_resolution_source"] == "ambiguous_active_items"


def test_recent_committed_meal_summary_exposes_multi_item_candidates_without_selected_authority() -> None:
    db = _session()
    user = get_or_create_user(db, "multi-item-recent-candidates")
    result = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="multi-item-candidates",
            items=[
                MealItemPayload(name="rice", estimated_kcal=260),
                MealItemPayload(name="egg", estimated_kcal=90),
            ],
        ),
    )
    assert result is not None

    state = resolve_intake_state(
        db,
        user_external_id="multi-item-recent-candidates",
        local_date="2026-05-02",
        incoming_user_text="actually make the rice smaller",
    )

    recent = state.injected_context["RECENT_COMMITTED_MEALS_SUMMARY"][0]
    assert recent["meal_thread_id"] == result.meal_thread_id
    assert recent["item_resolution_source"] == "ambiguous_active_items"
    assert "meal_item_id" not in recent
    assert recent["item_candidates"] == [
        {
            "meal_item_id": 1,
            "canonical_name": "rice",
            "item_index": 0,
            "estimated_kcal": 260,
            "mutation_authority": False,
            "selected_target": False,
        },
        {
            "meal_item_id": 2,
            "canonical_name": "egg",
            "item_index": 1,
            "estimated_kcal": 90,
            "mutation_authority": False,
            "selected_target": False,
        },
    ]


def test_open_target_clarification_without_thread_does_not_promote_active_meal_as_pending_target() -> None:
    target = _target_meal_reference(
        active_meal={
            "meal_thread_id": 20,
            "meal_version_id": 22,
            "meal_title": "lunch chicken rice",
        },
        conversation_state=SimpleNamespace(
            pending_followup_state=SimpleNamespace(
                is_open=True,
                pending_question="Which meal should I remove?",
                meal_thread_id=None,
            ),
            active_meal_state=SimpleNamespace(meal_title=None),
        ),
    )

    assert target["meal_thread_id"] == 20
    assert target["target_resolution_source"] == "active_meal_view"
    assert target["correction_confidence"] == "medium"


def test_resolved_state_no_plan_budget_snapshot_preserves_no_ledger_posture() -> None:
    db = _session()
    user = get_or_create_user(db, "no-plan-context-snapshot")
    commit_meal_payload_to_canonical(db, user=user, candidate=_candidate(request_id="no-plan-context"))

    state = resolve_intake_state(
        db,
        user_external_id="no-plan-context-snapshot",
        local_date="2026-05-02",
        incoming_user_text="how much is left today?",
    )

    budget = state.injected_context["CURRENT_BUDGET"]
    assert budget["has_active_plan"] is False
    assert budget["has_day_budget_ledger"] is False
    assert budget["no_plan_posture"] == "onboarding_required"
    assert budget["freshness_status"] == "current_turn"
    assert budget["remaining_kcal"] == 0


def test_resolved_state_budget_snapshot_reports_active_plan_and_ledger_freshness() -> None:
    db = _session()
    user = get_or_create_user(db, "active-plan-context-snapshot")
    bootstrap = bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=30,
            height_cm=165.0,
            current_weight_kg=58.0,
            activity_level="sedentary",
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            local_date="2026-05-02",
        ),
    )
    commit_meal_payload_to_canonical(db, user=user, candidate=_candidate(request_id="active-plan-context"))
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()

    state = resolve_intake_state(
        db,
        user_external_id="active-plan-context-snapshot",
        local_date="2026-05-02",
        incoming_user_text="how much is left today?",
    )

    budget = state.injected_context["CURRENT_BUDGET"]
    body = state.injected_context["ACTIVE_BODY_PLAN"]
    assert budget["has_active_plan"] is True
    assert budget["has_day_budget_ledger"] is True
    assert budget["budget_kcal"] == bootstrap.target_result.recommended_target_kcal
    assert budget["consumed_kcal"] == 480
    assert budget["remaining_kcal"] == bootstrap.target_result.recommended_target_kcal - 480
    assert budget["ledger_last_recomputed_at"] == ledger.last_recomputed_at.isoformat()
    assert budget["freshness_status"] == "current_turn"
    assert body["body_plan_id"] == bootstrap.active_body_plan_view.body_plan_id
    assert body["freshness_status"] == "current_turn"
