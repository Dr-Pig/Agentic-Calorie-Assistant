"""Budget domain ORM models: day budget ledger and ledger entries."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infra.models import Base, utcnow

if TYPE_CHECKING:
    from app.shared.infra.models import User


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
