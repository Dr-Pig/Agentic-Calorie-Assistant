from __future__ import annotations

from datetime import datetime
from math import isfinite

from sqlalchemy.orm import Session

from app.models import BodyProfileRecord, User
from app.shared.domain import BodyObservation
from app.shared.infra.canonical_persistence import (
    load_active_body_profile_record,
    load_body_observations,
    upsert_observation_skeleton,
)


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
    observation = upsert_observation_skeleton(
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
    observation = upsert_observation_skeleton(
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
    return load_body_observations(
        db,
        user_id=user_id,
        local_date=local_date,
        observation_type=observation_type,
    )


def get_active_body_profile_record(
    db: Session,
    *,
    user_id: int,
) -> BodyProfileRecord | None:
    return load_active_body_profile_record(db, user_id=user_id)


def _validate_body_observation_value(*, value: float, observation_type: str) -> None:
    normalized = float(value)
    if observation_type == "weight" and (not isfinite(normalized) or normalized <= 0):
        raise ValueError("weight observation value must be positive finite")
