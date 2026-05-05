"""Cross-cutting ORM models: Base, User, and legacy tables."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Integer, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.body.infrastructure.models import (
        BodyObservationRecord,
        BodyPlanRecord,
        BodyProfileRecord,
    )
    from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
    from app.intake.infrastructure.models import MealThreadRecord


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    logs: Mapped[list["MealLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    messages: Mapped[list["MessageBuffer"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    meal_threads: Mapped[list["MealThreadRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ledgers: Mapped[list["DayBudgetLedgerRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ledger_entries: Mapped[list["LedgerEntryRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    body_observations: Mapped[list["BodyObservationRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    body_profiles: Mapped[list["BodyProfileRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    body_plans: Mapped[list["BodyPlanRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    proposals: Mapped[list["ProposalContainerRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    proactive_triggers: Mapped[list["ProactiveTriggerRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class MealLog(Base):
    __tablename__ = "meal_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    status: Mapped[str] = mapped_column(String(20), default="completed_meal", index=True)
    parent_log_id: Mapped[Optional[int]] = mapped_column(ForeignKey("meal_logs.id"), nullable=True)
    pending_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    meal_title: Mapped[str] = mapped_column(String(512))
    raw_input: Mapped[str] = mapped_column(Text)

    kcal: Mapped[int] = mapped_column(Integer, default=0)
    protein_g: Mapped[int] = mapped_column(Integer, default=0)
    carb_g: Mapped[int] = mapped_column(Integer, default=0)
    fat_g: Mapped[int] = mapped_column(Integer, default=0)

    components_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    debug_steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship(back_populates="logs")


class MessageBuffer(Base):
    __tablename__ = "message_buffer"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    linked_meal_log_id: Mapped[Optional[int]] = mapped_column(ForeignKey("meal_logs.id"), nullable=True, index=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trace_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped["User"] = relationship(back_populates="messages")


class ProactiveTriggerRecord(Base):
    __tablename__ = "proactive_triggers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    trigger_type: Mapped[str] = mapped_column(String(64), index=True)
    trigger_status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="proactive_triggers")


class ProposalContainerRecord(Base):
    __tablename__ = "proposal_containers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    proposal_type: Mapped[str] = mapped_column(String(64), index=True)
    proposal_status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    top_option_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="proposals")
    options: Mapped[list["ProposalOptionRecord"]] = relationship(
        back_populates="proposal", cascade="all, delete-orphan"
    )


class ProposalOptionRecord(Base):
    __tablename__ = "proposal_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_container_id: Mapped[int] = mapped_column(
        ForeignKey("proposal_containers.id"), index=True
    )
    option_type: Mapped[str] = mapped_column(String(64), index=True)
    option_label: Mapped[str] = mapped_column(String(255))
    option_summary: Mapped[str] = mapped_column(Text, default="")
    rank_order: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    effect_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    proposal: Mapped["ProposalContainerRecord"] = relationship(back_populates="options")
