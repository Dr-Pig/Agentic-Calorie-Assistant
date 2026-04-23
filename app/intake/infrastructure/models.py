"""Intake domain ORM models: meal threads, versions, items, legacy map."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Integer, String, Text, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infra.models import Base, utcnow


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
