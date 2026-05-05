"""Body domain ORM models: observations, profiles, plans."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infra.models import Base, utcnow

if TYPE_CHECKING:
    from app.shared.infra.models import User


class BodyObservationRecord(Base):
    __tablename__ = "body_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    observation_type: Mapped[str] = mapped_column(String(64), default="weight", index=True)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(32), default="kg")
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    local_date: Mapped[str] = mapped_column(String(32), default="", index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="body_observations")


class BodyProfileRecord(Base):
    __tablename__ = "body_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    profile_status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    sex: Mapped[str] = mapped_column(String(32), default="female")
    age_years: Mapped[int] = mapped_column(Integer, default=0)
    height_cm: Mapped[float] = mapped_column(Float, default=0.0)
    current_weight_kg: Mapped[float] = mapped_column(Float, default=0.0)
    activity_level: Mapped[str] = mapped_column(String(32), default="sedentary")
    goal_type: Mapped[str] = mapped_column(String(32), default="lose_weight")
    target_weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weekly_target_rate_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="body_profiles")


class BodyPlanRecord(Base):
    __tablename__ = "body_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    plan_label: Mapped[str] = mapped_column(String(128), default="")
    estimated_tdee: Mapped[int] = mapped_column(Integer, default=0)
    daily_budget_kcal: Mapped[int] = mapped_column(Integer, default=0)
    safety_floor_kcal: Mapped[int] = mapped_column(Integer, default=0)
    target_pace_kg_per_week: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="body_plans")
