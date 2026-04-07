from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Integer, String, Text, DateTime, JSON, Float, ForeignKey
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
