from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.models import Base
from app.routes import router


ROOT = Path(__file__).resolve().parents[1]


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _client(db: Session) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_calibration_action_router_is_mounted_in_root_routes() -> None:
    root_routes = ROOT / "app" / "routes.py"
    source = root_routes.read_text(encoding="utf-8")

    assert "from app.composition.calibration_routes import public_router as calibration_router" in source
    assert "router.include_router(calibration_router)" in source


def test_root_router_exposes_open_calibration_proposals_read_model() -> None:
    db = _session()
    client = _client(db)

    response = client.get("/calibration/proposals/open", params={"user_id": "route-activation"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "route-activation",
        "open_count": 0,
        "proposals": [],
    }


def test_root_router_does_not_expose_direct_calibration_payload_action() -> None:
    db = _session()
    client = _client(db)

    response = client.post("/calibration/proposal/action", json={})

    assert response.status_code == 404


def test_root_router_does_not_expose_manual_model_input_preview() -> None:
    db = _session()
    client = _client(db)

    response = client.post("/calibration/proposal/preview", json={})

    assert response.status_code == 404


def test_root_router_does_not_expose_calibration_expiry_bookkeeping() -> None:
    db = _session()
    client = _client(db)

    response = client.post("/calibration/proposals/expire-stale", json={})

    assert response.status_code == 404
