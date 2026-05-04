from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.body.infrastructure.models import BodyObservationRecord, BodyPlanRecord, BodyProfileRecord
from app.budget.application.effective_budget_math import summarize_budget_adjustment_layers
from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord
from app.shared.infra.models import User
from app.shared.domain import BodyObservation


def resolved_body_observation_time(
    *,
    observed_at: datetime | None = None,
    local_date: str | None = None,
) -> tuple[datetime, str]:
    normalized_observed_at = observed_at or datetime.now()
    normalized_local_date = (
        local_date.strip() if isinstance(local_date, str) and local_date.strip() else normalized_observed_at.date().isoformat()
    )
    return normalized_observed_at, normalized_local_date


def body_observation_from_record(record: BodyObservationRecord) -> BodyObservation:
    return BodyObservation(
        observation_id=record.id,
        user_id=record.user_id,
        observation_type=record.observation_type,
        value=record.value,
        unit=record.unit,
        observed_at=record.observed_at,
        local_date=record.local_date,
        source=record.source,
        metadata=dict(record.metadata_json or {}),
    )


def upsert_observation_skeleton(
    db: Session,
    *,
    user: User,
    value: float,
    unit: str = "kg",
    observation_type: str = "weight",
    source: str = "manual",
    observed_at: datetime | None = None,
    local_date: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> BodyObservationRecord:
    normalized_observed_at, normalized_local_date = resolved_body_observation_time(
        observed_at=observed_at,
        local_date=local_date,
    )
    record = BodyObservationRecord(
        user_id=user.id,
        observation_type=observation_type,
        value=value,
        unit=unit,
        observed_at=normalized_observed_at,
        local_date=normalized_local_date,
        source=source,
        metadata_json=dict(metadata or {}),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def load_body_observations(
    db: Session,
    *,
    user_id: int,
    local_date: str | None = None,
    observation_type: str | None = "weight",
) -> list[BodyObservation]:
    stmt = select(BodyObservationRecord).where(BodyObservationRecord.user_id == user_id)
    if isinstance(observation_type, str) and observation_type.strip():
        stmt = stmt.where(BodyObservationRecord.observation_type == observation_type.strip())
    if isinstance(local_date, str) and local_date.strip():
        stmt = stmt.where(BodyObservationRecord.local_date == local_date.strip())
    rows = db.execute(
        stmt.order_by(BodyObservationRecord.observed_at.asc(), BodyObservationRecord.id.asc())
    ).scalars().all()
    return [body_observation_from_record(record) for record in rows]


def load_active_body_plan_record(db: Session, *, user_id: int) -> BodyPlanRecord | None:
    return db.execute(
        select(BodyPlanRecord)
        .where(BodyPlanRecord.user_id == user_id, BodyPlanRecord.plan_status == "active")
        .order_by(BodyPlanRecord.id.desc())
    ).scalars().first()


def load_active_body_profile_record(db: Session, *, user_id: int) -> BodyProfileRecord | None:
    return db.execute(
        select(BodyProfileRecord)
        .where(BodyProfileRecord.user_id == user_id, BodyProfileRecord.profile_status == "active")
        .order_by(BodyProfileRecord.id.desc())
    ).scalars().first()


def resolve_active_budget_kcal(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    explicit_budget_kcal: int | None = None,
) -> int:
    if explicit_budget_kcal is not None:
        return explicit_budget_kcal

    active_plan = load_active_body_plan_record(db, user_id=user_id)
    if active_plan is not None and active_plan.daily_budget_kcal > 0:
        return active_plan.daily_budget_kcal

    existing_ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user_id,
            DayBudgetLedgerRecord.local_date == local_date,
        )
    ).scalar_one_or_none()
    if existing_ledger is not None:
        return existing_ledger.budget_kcal

    return 0


def should_refresh_day_budget_ledger(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    explicit_budget_kcal: int | None = None,
) -> bool:
    if explicit_budget_kcal is not None:
        return True
    if load_active_body_plan_record(db, user_id=user_id) is not None:
        return True
    existing_ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user_id,
            DayBudgetLedgerRecord.local_date == local_date,
        )
    ).scalar_one_or_none()
    return existing_ledger is not None


def ensure_body_plan_skeleton(
    db: Session,
    *,
    user: User,
    estimated_tdee: int = 0,
    daily_budget_kcal: int = 0,
    safety_floor_kcal: int = 0,
) -> BodyPlanRecord:
    active = db.execute(
        select(BodyPlanRecord)
        .where(BodyPlanRecord.user_id == user.id, BodyPlanRecord.plan_status == "active")
        .order_by(BodyPlanRecord.id.desc())
    ).scalars().first()
    if active is not None:
        return active
    record = BodyPlanRecord(
        user_id=user.id,
        estimated_tdee=estimated_tdee,
        daily_budget_kcal=daily_budget_kcal,
        safety_floor_kcal=safety_floor_kcal,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def recompute_day_budget_ledger(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    budget_kcal: int | None = None,
    commit: bool = True,
) -> DayBudgetLedgerRecord:
    resolved_budget_kcal = resolve_active_budget_kcal(
        db,
        user_id=user_id,
        local_date=local_date,
        explicit_budget_kcal=budget_kcal,
    )
    ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user_id,
            DayBudgetLedgerRecord.local_date == local_date,
        )
    ).scalar_one_or_none()
    if ledger is None:
        ledger = DayBudgetLedgerRecord(
            user_id=user_id,
            local_date=local_date,
            budget_kcal=resolved_budget_kcal,
        )
        db.add(ledger)
        db.flush()
    active_meal_kcal = db.execute(
        select(MealVersionRecord.total_kcal)
        .join(MealThreadRecord, MealThreadRecord.active_version_id == MealVersionRecord.id)
        .where(
            MealThreadRecord.user_id == user_id,
            MealVersionRecord.local_date == local_date,
            MealVersionRecord.version_status == "active",
            MealVersionRecord.resolution_status == "completed_meal",
        )
    ).scalars().all()
    adjustment_entries = db.execute(
        select(LedgerEntryRecord).where(
            LedgerEntryRecord.user_id == user_id,
            LedgerEntryRecord.local_date == local_date,
            LedgerEntryRecord.entry_type != "meal_consumption",
        )
    ).scalars().all()
    consumed = sum(delta for delta in active_meal_kcal if delta > 0)
    adjustment_summary = summarize_budget_adjustment_layers(adjustment_entries)
    adjustments = adjustment_summary.runtime_adjustment_total_kcal
    ledger.budget_kcal = resolved_budget_kcal
    ledger.consumed_kcal = consumed
    ledger.adjustment_kcal = adjustments
    ledger.remaining_kcal = resolved_budget_kcal - consumed - adjustments
    ledger.last_recomputed_at = datetime.now()
    db.flush()
    if commit:
        db.commit()
        db.refresh(ledger)
    return ledger
