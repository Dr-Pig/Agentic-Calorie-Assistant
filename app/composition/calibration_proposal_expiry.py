from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.shared.infra.models import ProposalContainerRecord, User

EXPIRABLE_CALIBRATION_PROPOSAL_STATUSES = frozenset({"open"})


@dataclass(frozen=True)
class CalibrationProposalExpiryResult:
    expired_count: int
    expired_proposal_container_ids: list[int]


def _parse_expires_at(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _can_expire_at(*, expires_at: datetime | None, now_at: datetime) -> bool:
    if expires_at is None:
        return False
    expires_is_aware = expires_at.tzinfo is not None and expires_at.utcoffset() is not None
    now_is_aware = now_at.tzinfo is not None and now_at.utcoffset() is not None
    if expires_is_aware != now_is_aware:
        return False
    return expires_at <= now_at


def _load_expiry_candidate_rows(
    db: Session,
    *,
    user: User,
) -> list[tuple[int, dict[str, Any]]]:
    rows = db.execute(
        select(ProposalContainerRecord.id, ProposalContainerRecord.metadata_json).where(
            ProposalContainerRecord.user_id == user.id,
            ProposalContainerRecord.proposal_type == "calibration",
            ProposalContainerRecord.proposal_status.in_(EXPIRABLE_CALIBRATION_PROPOSAL_STATUSES),
        )
    ).all()
    return [(int(proposal_id), dict(metadata or {})) for proposal_id, metadata in rows]


def expire_stale_calibration_proposals(
    db: Session,
    *,
    user: User,
    now_at: datetime | None = None,
) -> CalibrationProposalExpiryResult:
    resolved_now = now_at or datetime.now()
    expired_ids: list[int] = []
    for proposal_id, metadata in _load_expiry_candidate_rows(db, user=user):
        expires_at = _parse_expires_at(metadata.get("expires_at"))
        if not _can_expire_at(expires_at=expires_at, now_at=resolved_now):
            continue
        metadata.update(
            {
                "expired_at": resolved_now.isoformat(),
                "expiry_reason": "expires_at_reached",
            }
        )
        result = db.execute(
            update(ProposalContainerRecord)
            .where(
                ProposalContainerRecord.id == proposal_id,
                ProposalContainerRecord.user_id == user.id,
                ProposalContainerRecord.proposal_type == "calibration",
                ProposalContainerRecord.proposal_status.in_(EXPIRABLE_CALIBRATION_PROPOSAL_STATUSES),
            )
            .values(
                proposal_status="expired",
                metadata_json=metadata,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount == 1:
            expired_ids.append(proposal_id)

    if expired_ids:
        db.commit()
    return CalibrationProposalExpiryResult(
        expired_count=len(expired_ids),
        expired_proposal_container_ids=expired_ids,
    )


__all__ = [
    "CalibrationProposalExpiryResult",
    "EXPIRABLE_CALIBRATION_PROPOSAL_STATUSES",
    "expire_stale_calibration_proposals",
]
