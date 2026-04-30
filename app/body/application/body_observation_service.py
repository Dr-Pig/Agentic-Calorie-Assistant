from __future__ import annotations

from datetime import datetime
from math import isfinite

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.body.infrastructure.models import BodyObservationRecord, BodyProfileRecord
from app.shared.infra.models import User
from app.shared.domain import BodyObservation


def _resolved_body_observation_time(
    *,
    observed_at: datetime | None = None,
    local_date: str | None = None,
) -> tuple[datetime, str]:
    normalized_observed_at = observed_at or datetime.now()
    normalized_local_date = (
        local_date.strip() if isinstance(local_date, str) and local_date.strip() else normalized_observed_at.date().isoformat()
    )
    return normalized_observed_at, normalized_local_date


def _body_observation_from_record(record: BodyObservationRecord) -> BodyObservation:
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


def _upsert_observation_skeleton(
    db: Session,
    *,
    user: User,
    value: float,
    unit: str,
    observation_type: str,
    source: str,
    observed_at: datetime | None,
    local_date: str | None,
    metadata: dict[str, object] | None,
) -> BodyObservationRecord:
    normalized_observed_at, normalized_local_date = _resolved_body_observation_time(
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


def record_body_observation_skeleton(
    db: Session,
    *,
    user: User,
    value: float,
    unit: str = "kg",
    observation_type: str = "weight",
    source: str = "manual",
    observed_at: datetime | None = None,
    local_date: str | None = None,
    metadata: dict[str, object] | None = None,
) -> int:
    _validate_body_observation_value(value=value, observation_type=observation_type)
    observation = _upsert_observation_skeleton(
        db,
        user=user,
        value=value,
        unit=unit,
        observation_type=observation_type,
        source=source,
        observed_at=observed_at,
        local_date=local_date,
        metadata=metadata,
    )
    return observation.id


def record_body_observation_to_canonical(
    db: Session,
    *,
    user: User,
    value: float,
    unit: str = "kg",
    observation_type: str = "weight",
    source: str = "manual",
    observed_at: datetime | None = None,
    local_date: str | None = None,
    metadata: dict[str, object] | None = None,
) -> BodyObservation:
    _validate_body_observation_value(value=value, observation_type=observation_type)
    observation = _upsert_observation_skeleton(
        db,
        user=user,
        value=value,
        unit=unit,
        observation_type=observation_type,
        source=source,
        observed_at=observed_at,
        local_date=local_date,
        metadata=metadata,
    )
    return BodyObservation(
        observation_id=observation.id,
        user_id=observation.user_id,
        observation_type=observation.observation_type,
        value=observation.value,
        unit=observation.unit,
        observed_at=observation.observed_at,
        local_date=observation.local_date,
        source=observation.source,
        metadata=dict(observation.metadata_json or {}),
    )


def load_body_observation_history(
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
    return [_body_observation_from_record(record) for record in rows]


def get_active_body_profile_record(
    db: Session,
    *,
    user_id: int,
) -> BodyProfileRecord | None:
    return db.execute(
        select(BodyProfileRecord)
        .where(BodyProfileRecord.user_id == user_id, BodyProfileRecord.profile_status == "active")
        .order_by(BodyProfileRecord.id.desc())
    ).scalars().first()


def _validate_body_observation_value(*, value: float, observation_type: str) -> None:
    normalized = float(value)
    if observation_type == "weight" and (not isfinite(normalized) or normalized <= 0):
        raise ValueError("weight observation value must be positive finite")
