from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.canonical_commit_bridge import (
    apply_proposal_acceptance_skeleton,
    commit_request_candidate_to_canonical,
)
from app.application.rescue_overlay import (
    RescueOverlayTargetDay,
    apply_short_horizon_rescue_plan,
    assess_rescue_overlay_day,
    build_short_horizon_rescue_plan,
)
from app.models import Base, DayBudgetLedgerRecord, LedgerEntryRecord, User
from app.schemas import CommitRequestCandidate, MealItemPayload


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _user(db: Session) -> User:
    user = User(user_id="rescue-user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _candidate(*, request_id: str, title: str, kcal: int, local_date: str) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id=request_id,
        planner_intent="food_estimation",
        version_reason="new_intake",
        meal_title=title,
        raw_input=title,
        estimated_kcal=kcal,
        protein_g=20,
        carb_g=50,
        fat_g=10,
        resolution_status="completed_meal",
        local_date=local_date,
        items=[
            MealItemPayload(
                name=title,
                quantity_hint="1 serving",
                source="llm",
                evidence_role="unknown",
                estimate_basis="llm_only",
                confidence_tier="medium",
                estimated_kcal=kcal,
                protein_g=20,
                carb_g=50,
                fat_g=10,
                evidence_ids=[],
                classification={},
            )
        ],
        trace_ref={"request_id": request_id},
    )


def test_assess_rescue_overlay_day_marks_strained_vs_non_viable() -> None:
    strained = assess_rescue_overlay_day(
        local_date="2026-04-12",
        base_budget_kcal=2000,
        calibration_adjustment_kcal=0,
        proposed_rescue_overlay_kcal=-250,
        safety_floor_kcal=1500,
    )
    assert strained.viability == "strained"
    assert strained.within_compression_cap is True
    assert strained.meets_safety_floor is True

    non_viable = assess_rescue_overlay_day(
        local_date="2026-04-12",
        base_budget_kcal=2000,
        calibration_adjustment_kcal=0,
        proposed_rescue_overlay_kcal=-350,
        safety_floor_kcal=1500,
    )
    assert non_viable.viability == "non_viable"
    assert non_viable.within_compression_cap is False


def test_build_short_horizon_rescue_plan_handles_viable_and_non_viable_cases() -> None:
    viable = build_short_horizon_rescue_plan(
        overshoot_kcal=450,
        target_days=[
            RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-13", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-14", base_budget_kcal=1800),
        ],
        safety_floor_kcal=1500,
    )
    assert viable.viability == "viable"
    assert viable.scheduled_recovery_kcal == 450
    assert viable.unallocated_recovery_kcal == 0
    assert [day.proposed_rescue_overlay_kcal for day in viable.overlay_days] == [-150, -150, -150]

    blocked = build_short_horizon_rescue_plan(
        overshoot_kcal=100,
        target_days=[
            RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1500),
            RescueOverlayTargetDay(local_date="2026-04-13", base_budget_kcal=1500),
        ],
        safety_floor_kcal=1500,
    )
    assert blocked.viability == "non_viable"
    assert blocked.requires_escalation is True
    assert blocked.scheduled_recovery_kcal == 0
    assert blocked.unallocated_recovery_kcal == 100


def test_build_short_horizon_rescue_plan_resolves_safety_floor_from_active_body_plan() -> None:
    db = _session()
    user = _user(db)
    apply_proposal_acceptance_skeleton(
        db,
        user=user,
        proposal_type="budget_adjustment",
        option_type="budget_adjustment",
        option_label="Set floor",
        estimated_tdee=2200,
        daily_budget_kcal=1800,
        safety_floor_kcal=1450,
    )

    plan = build_short_horizon_rescue_plan(
        overshoot_kcal=300,
        target_days=[
            RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-13", base_budget_kcal=1800),
        ],
        db=db,
        user=user,
    )

    assert plan.safety_floor_kcal == 1450
    assert [day.safety_floor_kcal for day in plan.overlay_days] == [1450, 1450]


def test_build_short_horizon_rescue_plan_prefers_explicit_override_over_body_plan_floor() -> None:
    db = _session()
    user = _user(db)
    apply_proposal_acceptance_skeleton(
        db,
        user=user,
        proposal_type="budget_adjustment",
        option_type="budget_adjustment",
        option_label="Set floor",
        estimated_tdee=2200,
        daily_budget_kcal=1800,
        safety_floor_kcal=1450,
    )

    plan = build_short_horizon_rescue_plan(
        overshoot_kcal=150,
        target_days=[RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1800)],
        safety_floor_kcal=1600,
        db=db,
        user=user,
    )

    assert plan.safety_floor_kcal == 1600
    assert plan.overlay_days[0].safety_floor_kcal == 1600


def test_build_short_horizon_rescue_plan_requires_resolved_safety_floor() -> None:
    db = _session()
    user = _user(db)

    try:
        build_short_horizon_rescue_plan(
            overshoot_kcal=100,
            target_days=[RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1800)],
            db=db,
            user=user,
        )
    except ValueError as exc:
        assert "resolved safety_floor_kcal" in str(exc)
    else:
        raise AssertionError("expected unresolved safety floor to block rescue plan construction")


def test_apply_short_horizon_rescue_plan_writes_overlay_entries_and_recomputes_ledger() -> None:
    db = _session()
    user = _user(db)

    commit_request_candidate_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="rescue-meal",
            title="overshoot meal",
            kcal=900,
            local_date="2026-04-12",
        ),
        budget_kcal=1800,
    )

    plan = build_short_horizon_rescue_plan(
        overshoot_kcal=240,
        target_days=[
            RescueOverlayTargetDay(local_date="2026-04-12", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-13", base_budget_kcal=1800),
        ],
        safety_floor_kcal=1500,
    )
    entries = apply_short_horizon_rescue_plan(db, user=user, plan=plan, source_id=42)

    assert len(entries) == 2
    assert all(entry.entry_type == "rescue_overlay" for entry in entries)
    assert all(entry.source_type == "rescue_plan" for entry in entries)

    first_ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user.id,
            DayBudgetLedgerRecord.local_date == "2026-04-12",
        )
    ).scalar_one()
    second_ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user.id,
            DayBudgetLedgerRecord.local_date == "2026-04-13",
        )
    ).scalar_one()

    assert first_ledger.adjustment_kcal == -120
    assert first_ledger.remaining_kcal == 1020
    assert second_ledger.adjustment_kcal == -120
    assert second_ledger.remaining_kcal == 1920

    stored_entry = db.execute(
        select(LedgerEntryRecord).where(
            LedgerEntryRecord.user_id == user.id,
            LedgerEntryRecord.local_date == "2026-04-12",
            LedgerEntryRecord.entry_type == "rescue_overlay",
        )
    ).scalar_one()
    assert stored_entry.metadata_json["rescue_family"] == "short_horizon_spread"
    assert stored_entry.metadata_json["safety_floor_kcal"] == 1500
