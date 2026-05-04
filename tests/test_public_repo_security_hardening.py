from __future__ import annotations

import secrets
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.composition import v2_routes
from app.database import get_db
from app.models import Base
from app.routes import router


def _client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_sensitive_routes_are_closed_when_local_debug_token_is_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("LOCAL_DEBUG_API_TOKEN", raising=False)
    client = _client()

    for method, path in (
        ("GET", "/logs"),
        ("GET", "/admin/traces"),
        ("GET", "/admin/trace/example-trace"),
        ("GET", "/accurate-intake/debug"),
        ("GET", "/accurate-intake/chat-history"),
        ("GET", "/accurate-intake/debug/surface"),
        ("GET", "/user/public-hardening/logs"),
        ("POST", "/user/public-hardening/context/reset"),
    ):
        response = client.request(method, path)

        assert response.status_code == 404, f"{method} {path} should be default-closed"


def test_sensitive_routes_require_matching_local_debug_token(monkeypatch) -> None:
    token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    client = _client()

    missing = client.get("/logs")
    wrong = client.get("/logs", headers={"X-Local-Debug-Token": secrets.token_urlsafe(24)})
    allowed = client.get("/logs", headers={"X-Local-Debug-Token": token})

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert allowed.status_code == 200
    assert "items" in allowed.json()


def test_v2_estimate_error_response_does_not_expose_traceback(monkeypatch) -> None:
    async def fail_execute_intake_turn(**_: Any) -> dict[str, Any]:
        raise RuntimeError("internal stack marker should not leak")

    monkeypatch.setattr(v2_routes, "execute_intake_turn", fail_execute_intake_turn)
    client = _client()

    response = client.post("/v2/estimate", json={"user_id": "public-hardening", "text": "tea egg"})

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "error": "internal_server_error",
        "request_id": payload["request_id"],
        "status": "error",
    }
    assert "traceback" not in payload
    assert "internal stack marker" not in response.text
    assert str(Path("app/composition/v2_routes.py")) not in response.text


def test_evomap_activation_secret_script_is_not_tracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "scripts/evomap_activate.py"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    assert result.stdout.strip() == ""


def test_tracked_source_has_no_evomap_secret_key_literal_reference() -> None:
    pattern = "node" + "_secret"
    result = subprocess.run(
        ["git", "grep", "-n", pattern, "--", "app", "scripts", "static", "tests"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 1
    assert result.stdout.strip() == ""
