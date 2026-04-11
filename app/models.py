from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Integer, String, Text, DateTime, JSON, Float, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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

    # --- Status & Versioning ---
    status: Mapped[str] = mapped_column(String(20), default="completed_meal", index=True)
    # "candidate_meal"   : 剛提到餐點，但仍待補更多資訊
    # "draft_unresolved" : 已知部分內容，但仍需追問或補充
    # "completed_meal"   : 估算完成
    # "superseded"  : 被後續修正覆蓋 (保留作歷史溯源)
    parent_log_id: Mapped[Optional[int]] = mapped_column(ForeignKey("meal_logs.id"), nullable=True)
    pending_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Core Data ---
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
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    linked_meal_log_id: Mapped[Optional[int]] = mapped_column(ForeignKey("meal_logs.id"), nullable=True, index=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="messages")


class MealThreadRecord(Base):
    __tablename__ = "meal_threads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    thread_kind: Mapped[str] = mapped_column(String(32), default="text_intake", index=True)
    active_version_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="meal_threads")
    versions: Mapped[list["MealVersionRecord"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )


class MealVersionRecord(Base):
    __tablename__ = "meal_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    meal_thread_id: Mapped[int] = mapped_column(ForeignKey("meal_threads.id"), index=True)
    parent_version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("meal_versions.id"), nullable=True, index=True)
    version_status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    version_reason: Mapped[str] = mapped_column(String(64), default="new_intake")
    reason_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    meal_title: Mapped[str] = mapped_column(String(512), default="")
    raw_input: Mapped[str] = mapped_column(Text, default="")
    source_request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    planner_intent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    resolution_status: Mapped[str] = mapped_column(String(32), default="completed_meal", index=True)
    total_kcal: Mapped[int] = mapped_column(Integer, default=0)
    protein_g: Mapped[int] = mapped_column(Integer, default=0)
    carb_g: Mapped[int] = mapped_column(Integer, default=0)
    fat_g: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    local_date: Mapped[str] = mapped_column(String(32), default="", index=True)
    superseded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    thread: Mapped["MealThreadRecord"] = relationship(back_populates="versions", foreign_keys=[meal_thread_id])
    parent_version: Mapped[Optional["MealVersionRecord"]] = relationship(
        remote_side="MealVersionRecord.id", foreign_keys=[parent_version_id]
    )
    items: Mapped[list["MealItemRecord"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class MealItemRecord(Base):
    __tablename__ = "meal_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    meal_version_id: Mapped[int] = mapped_column(ForeignKey("meal_versions.id"), index=True)
    item_index: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(512))
    quantity_hint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="llm")
    evidence_role: Mapped[str] = mapped_column(String(64), default="unknown")
    estimate_basis: Mapped[str] = mapped_column(String(64), default="llm_only")
    confidence_tier: Mapped[str] = mapped_column(String(16), default="low")
    estimated_kcal: Mapped[int] = mapped_column(Integer, default=0)
    protein_g: Mapped[int] = mapped_column(Integer, default=0)
    carb_g: Mapped[int] = mapped_column(Integer, default=0)
    fat_g: Mapped[int] = mapped_column(Integer, default=0)
    evidence_ids_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    classification_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    version: Mapped["MealVersionRecord"] = relationship(back_populates="items")


class LegacyMealLogMapRecord(Base):
    __tablename__ = "legacy_meal_log_map"

    id: Mapped[int] = mapped_column(primary_key=True)
    meal_log_id: Mapped[int] = mapped_column(ForeignKey("meal_logs.id"), unique=True, index=True)
    meal_thread_id: Mapped[int] = mapped_column(ForeignKey("meal_threads.id"), index=True)
    meal_version_id: Mapped[int] = mapped_column(ForeignKey("meal_versions.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class DayBudgetLedgerRecord(Base):
    __tablename__ = "day_budget_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    local_date: Mapped[str] = mapped_column(String(32), index=True)
    budget_kcal: Mapped[int] = mapped_column(Integer, default=0)
    consumed_kcal: Mapped[int] = mapped_column(Integer, default=0)
    adjustment_kcal: Mapped[int] = mapped_column(Integer, default=0)
    remaining_kcal: Mapped[int] = mapped_column(Integer, default=0)
    last_recomputed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="ledgers")


class LedgerEntryRecord(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    local_date: Mapped[str] = mapped_column(String(32), index=True)
    entry_type: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    delta_kcal: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="ledger_entries")


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
    proposal_container_id: Mapped[int] = mapped_column(ForeignKey("proposal_containers.id"), index=True)
    option_type: Mapped[str] = mapped_column(String(64), index=True)
    option_label: Mapped[str] = mapped_column(String(255), default="")
    option_summary: Mapped[str] = mapped_column(Text, default="")
    rank_order: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    effect_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    proposal: Mapped["ProposalContainerRecord"] = relationship(back_populates="options")


class ProactiveTriggerRecord(Base):
    __tablename__ = "proactive_triggers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    trigger_type: Mapped[str] = mapped_column(String(64), index=True)
    trigger_status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="proactive_triggers")
