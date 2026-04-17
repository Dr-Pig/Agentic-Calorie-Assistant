from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import BodyPlanRecord, BodyProfileRecord, User

ProfileSex = Literal["female", "male"]
ProfileActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
ProfileGoalType = Literal["lose_weight", "maintain", "gain_weight"]


@dataclass(frozen=True)
class BodyProfileUpsertInput:
    sex: ProfileSex
    age_years: int
    height_cm: float
    current_weight_kg: float
    activity_level: ProfileActivityLevel
    goal_type: ProfileGoalType
    weekly_target_rate_kg: float | None = None
    target_weight_kg: float | None = None
    timezone: str | None = None


@dataclass(frozen=True)
class BodyPlanBootstrapWriteInput:
    estimated_tdee_kcal: int
    daily_budget_kcal: int
    safety_floor_kcal: int
    target_pace_kg_per_week: float | None
    goal_type: ProfileGoalType
    plan_source: str = "onboarding_bootstrap"
    recommended_target_kcal: int | None = None


def load_active_body_profile_record(
    db: Session,
    *,
    user_id: int,
) -> BodyProfileRecord | None:
    return db.execute(
        select(BodyProfileRecord)
        .where(
            BodyProfileRecord.user_id == user_id,
            BodyProfileRecord.profile_status == "active",
        )
        .order_by(BodyProfileRecord.id.desc())
    ).scalar_one_or_none()


def upsert_active_body_profile(
    db: Session,
    *,
    user: User,
    profile: BodyProfileUpsertInput,
) -> BodyProfileRecord:
    record = load_active_body_profile_record(db, user_id=user.id)
    now = datetime.now()
    if record is None:
        record = BodyProfileRecord(
            user_id=user.id,
            created_at=now,
        )
        db.add(record)
        db.flush()

    record.profile_status = "active"
    record.sex = profile.sex
    record.age_years = profile.age_years
    record.height_cm = profile.height_cm
    record.current_weight_kg = profile.current_weight_kg
    record.activity_level = profile.activity_level
    record.goal_type = profile.goal_type
    record.weekly_target_rate_kg = profile.weekly_target_rate_kg
    record.target_weight_kg = profile.target_weight_kg
    record.timezone = profile.timezone
    record.updated_at = now
    return record


def load_active_body_plan_record(
    db: Session,
    *,
    user_id: int,
) -> BodyPlanRecord | None:
    return db.execute(
        select(BodyPlanRecord)
        .where(
            BodyPlanRecord.user_id == user_id,
            BodyPlanRecord.plan_status == "active",
        )
        .order_by(BodyPlanRecord.id.desc())
    ).scalar_one_or_none()


def upsert_active_body_plan_from_bootstrap(
    db: Session,
    *,
    user: User,
    plan: BodyPlanBootstrapWriteInput,
) -> BodyPlanRecord:
    record = load_active_body_plan_record(db, user_id=user.id)
    now = datetime.now()
    if record is None:
        record = BodyPlanRecord(
            user_id=user.id,
            plan_status="active",
            started_at=now,
            created_at=now,
        )
        db.add(record)
        db.flush()

    metadata = dict(record.metadata_json or {})
    metadata.update(
        {
            "goal_type": plan.goal_type,
            "plan_source": plan.plan_source,
            "recommended_target_kcal": plan.recommended_target_kcal or plan.daily_budget_kcal,
        }
    )

    record.plan_status = "active"
    record.plan_label = f"{plan.goal_type}_budget_plan"
    record.estimated_tdee = plan.estimated_tdee_kcal
    record.daily_budget_kcal = plan.daily_budget_kcal
    record.safety_floor_kcal = plan.safety_floor_kcal
    record.target_pace_kg_per_week = plan.target_pace_kg_per_week
    record.metadata_json = metadata
    if record.started_at is None:
        record.started_at = now
    return record
