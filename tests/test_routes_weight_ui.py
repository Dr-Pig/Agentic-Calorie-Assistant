from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.canonical_commit_bridge import record_body_observation_to_canonical
from app.database import get_or_create_user
from app.main import app
from app.models import Base
from app.routes import get_db as routes_get_db


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    db = testing_session()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[routes_get_db] = override_get_db
    try:
        yield db
    finally:
        app.dependency_overrides.pop(routes_get_db, None)
        db.close()


@pytest.fixture()
def client(db_session):
    with TestClient(app) as test_client:
        yield test_client


def test_weight_observations_route_returns_typed_history_with_local_date_filter(client, db_session) -> None:
    user = get_or_create_user(db_session, "weight-ui-user")
    record_body_observation_to_canonical(
        db_session,
        user=user,
        value=72.4,
        observed_at=datetime(2026, 4, 11, 7, 30),
        local_date="2026-04-11",
        source="manual",
    )
    record_body_observation_to_canonical(
        db_session,
        user=user,
        value=72.1,
        observed_at=datetime(2026, 4, 12, 7, 45),
        local_date="2026-04-12",
        source="manual",
    )

    response = client.get("/weight/observations", params={"user_id": "weight-ui-user", "local_date": "2026-04-11"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == user.id
    assert payload["local_date"] == "2026-04-11"
    assert len(payload["observations"]) == 1
    observation = payload["observations"][0]
    assert observation["value"] == 72.4
    assert observation["unit"] == "kg"
    assert observation["local_date"] == "2026-04-11"
    assert observation["source"] == "manual"


def test_weight_surface_renders_canonical_body_observation_history(client, db_session) -> None:
    user = get_or_create_user(db_session, "weight-ui-surface")
    record_body_observation_to_canonical(
        db_session,
        user=user,
        value=71.9,
        observed_at=datetime(2026, 4, 13, 6, 10),
        source="scale",
    )

    response = client.get("/weight", params={"user_id": "weight-ui-surface"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Weight Surface" in response.text
    assert "source: body_observation_history" in response.text
    assert "71.9 kg" in response.text
    assert "scale" in response.text
