from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.recommendation_context import build_recommendation_context
from app.domain import ActiveBodyPlanView, CurrentBudgetView, ProposalContainer
from app.infrastructure.preference_profile_persistence import load_preference_profile_summary
from app.models import Base, MealItemRecord, MealThreadRecord, MealVersionRecord


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _seed_meal_item(
    db: Session,
    *,
    user_id: int,
    title: str,
    occurred_at: datetime,
    protein_g: int,
    item_kind: str,
    staple_type: str,
    cuisine_family: str,
    store_name: str,
) -> None:
    thread = MealThreadRecord(user_id=user_id, title=title, thread_kind="text_intake")
    db.add(thread)
    db.flush()
    version = MealVersionRecord(
        meal_thread_id=thread.id,
        version_status="active",
        version_reason="new_intake",
        meal_title=title,
        raw_input=title,
        planner_intent="food_estimation",
        resolution_status="completed_meal",
        total_kcal=520,
        protein_g=protein_g,
        occurred_at=occurred_at,
        local_date="2026-04-18",
    )
    db.add(version)
    db.flush()
    thread.active_version_id = version.id
    db.add(thread)
    db.add(
        MealItemRecord(
            meal_version_id=version.id,
            item_index=0,
            name=title,
            quantity_hint="1 serving",
            source="llm",
            evidence_role="main",
            estimate_basis="llm_only",
            confidence_tier="high",
            estimated_kcal=520,
            protein_g=protein_g,
            carb_g=45,
            fat_g=16,
            classification_json={
                "item_kind": item_kind,
                "staple_type": staple_type,
                "cuisine_family": cuisine_family,
                "store_name": store_name,
            },
        )
    )
    db.commit()


def test_recommendation_context_extracts_constraints_and_preferences() -> None:
    db = _session()
    _seed_meal_item(
        db,
        user_id=1,
        title="chicken rice",
        occurred_at=datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc),
        protein_g=28,
        item_kind="main_meal",
        staple_type="rice",
        cuisine_family="taiwanese",
        store_name="Store A",
    )
    _seed_meal_item(
        db,
        user_id=1,
        title="protein shake",
        occurred_at=datetime(2026, 4, 18, 16, 0, tzinfo=timezone.utc),
        protein_g=24,
        item_kind="drink",
        staple_type="drink",
        cuisine_family="beverage",
        store_name="Store B",
    )
    preference_summary = load_preference_profile_summary(db, user_id=1)

    packet = build_recommendation_context(
        user_id=1,
        current_budget_view=CurrentBudgetView(
            user_id=1,
            local_date="2026-04-18",
            budget_kcal=1800,
            consumed_kcal=980,
            remaining_kcal=820,
            active_meal_count=2,
        ),
        active_body_plan_view=ActiveBodyPlanView(
            user_id=1,
            plan_status="active",
            goal_type="lose_weight",
            daily_budget_kcal=1800,
        ),
        preference_profile_summary=preference_summary,
        open_proposals=[ProposalContainer(proposal_type="rescue", proposal_status="open")],
        raw_user_input="附近有什麼可以吃",
    )

    assert packet.recommendation_mode == "reactive_chat"
    assert packet.hard_constraints.remaining_budget_kcal == 820
    assert packet.hard_constraints.rescue_active is True
    assert packet.hard_constraints.location_required is True
    assert "main_meal" in packet.soft_preferences.preferred_item_kinds
    assert "rice" in packet.soft_preferences.preferred_staple_types
    assert packet.soft_preferences.protein_posture_preference == "high_protein_bias"
    assert packet.context_window_summary["source_item_count"] == 2


def test_recommendation_context_supports_cold_start_without_preferences() -> None:
    packet = build_recommendation_context(
        user_id=9,
        current_budget_view=CurrentBudgetView(
            user_id=9,
            local_date="2026-04-18",
            budget_kcal=1650,
            consumed_kcal=300,
            remaining_kcal=1350,
        ),
        active_body_plan_view=ActiveBodyPlanView(
            user_id=9,
            plan_status="active",
            daily_budget_kcal=1650,
        ),
    )

    assert packet.recommendation_mode == "cold_start"
    assert packet.hard_constraints.remaining_budget_kcal == 1350
    assert packet.soft_preferences.preferred_item_kinds == ()
    assert packet.context_window_summary["preference_freshness"] == "empty"
