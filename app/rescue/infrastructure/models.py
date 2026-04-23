"""Rescue domain ORM models: proposal containers and options."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infra.models import Base, utcnow


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
