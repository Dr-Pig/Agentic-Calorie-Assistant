from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.body.application.body_observation_service import (
    load_body_observation_history,
    record_body_observation_to_canonical,
)
from app.shared.domain import BodyObservation
from app.models import Base, User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return TestingSession()


def _user(db: Session) -> User:
    user = User(user_id="test-user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_body_observation_write_normalizes_local_date_and_reads_typed_history() -> None:
    db = _session()
    user = _user(db)
    observed_at = datetime(2026, 4, 11, 7, 30, 0)

    observation = record_body_observation_to_canonical(
        db,
        user=user,
        value=72.4,
        unit="kg",
        observed_at=observed_at,
        metadata={"note": "morning weigh-in"},
    )

    assert isinstance(observation, BodyObservation)
    assert observation.observation_id is not None
    assert observation.user_id == user.id
    assert observation.value == 72.4
    assert observation.unit == "kg"
    assert observation.observed_at == observed_at
    assert observation.local_date == "2026-04-11"
    assert observation.source == "manual"
    assert observation.metadata == {"note": "morning weigh-in"}

    history = load_body_observation_history(
        db,
        user_id=user.id,
        local_date="2026-04-11",
    )

    assert len(history) == 1
    assert isinstance(history[0], BodyObservation)
    assert history[0].observation_id == observation.observation_id
    assert history[0].local_date == "2026-04-11"
    assert history[0].observed_at == observed_at


def test_body_observation_preserves_explicit_local_date_and_orders_history() -> None:
    db = _session()
    user = _user(db)

    first = record_body_observation_to_canonical(
        db,
        user=user,
        value=71.8,
        unit="kg",
        observed_at=datetime(2026, 4, 12, 6, 15, 0),
        local_date="2026-04-11",
        source="scale",
    )
    second = record_body_observation_to_canonical(
        db,
        user=user,
        value=71.5,
        unit="kg",
        observed_at=datetime(2026, 4, 12, 8, 0, 0),
        source="scale",
    )

    assert first.local_date == "2026-04-11"
    assert second.local_date == "2026-04-12"

    all_history = load_body_observation_history(db, user_id=user.id)
    assert [observation.observation_id for observation in all_history] == [
        first.observation_id,
        second.observation_id,
    ]
    assert [observation.local_date for observation in all_history] == [
        "2026-04-11",
        "2026-04-12",
    ]
    assert all_history[0].source == "scale"
    assert all_history[1].source == "scale"


@pytest.mark.parametrize("value", [0.0, -10.0, float("inf")])
def test_weight_observation_rejects_non_positive_or_non_finite_values(value: float) -> None:
    db = _session()
    user = _user(db)

    with pytest.raises(ValueError, match="positive finite"):
        record_body_observation_to_canonical(
            db,
            user=user,
            value=value,
            unit="kg",
            observation_type="weight",
            local_date="2026-04-13",
        )
