from __future__ import annotations

import secrets
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.composition import intake_routes, v2_routes
from app.database import get_db
from app.models import Base
from app.routes import router
from app.runtime.application.request_trace_artifacts import (
    build_internal_trace_refs,
    build_trace_refs,
)
from app.runtime.interface import local_debug_auth


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


def _request_with_host(host: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/logs",
            "headers": [],
            "query_string": b"",
            "client": (host, 50000),
            "server": ("testserver", 80),
            "scheme": "http",
            "root_path": "",
        }
    )


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
        ("POST", "/accurate-intake/feedback"),
        ("GET", "/accurate-intake/local-data-hygiene"),
        ("POST", "/accurate-intake/local-data-hygiene/backup"),
        ("POST", "/accurate-intake/local-data-hygiene/export"),
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


def test_sensitive_routes_accept_server_set_local_debug_session_cookie(monkeypatch) -> None:
    token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    client = _client()

    establish = client.post("/accurate-intake/local-debug-session", json={"token": token})
    missing_header = client.get("/logs")

    assert establish.status_code == 204
    assert "local_debug_session" in client.cookies
    assert missing_header.status_code == 200
    assert "items" in missing_header.json()


def test_local_debug_session_cookie_is_http_only_and_strict(monkeypatch) -> None:
    token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    client = _client()

    response = client.post("/accurate-intake/local-debug-session", json={"token": token})

    assert response.status_code == 204
    set_cookie = response.headers["set-cookie"]
    assert "local_debug_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "samesite=strict" in set_cookie.lower()
    assert "Path=/" in set_cookie
    assert "Domain=" not in set_cookie


def test_local_debug_session_rejects_wrong_token_without_setting_cookie(monkeypatch) -> None:
    token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    client = _client()

    response = client.post(
        "/accurate-intake/local-debug-session",
        json={"token": secrets.token_urlsafe(24)},
    )

    assert response.status_code == 403
    assert "set-cookie" not in response.headers
    assert "local_debug_session" not in client.cookies


def test_sensitive_routes_stay_closed_for_non_loopback_clients(monkeypatch) -> None:
    token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)

    with pytest.raises(HTTPException) as excinfo:
        local_debug_auth.require_local_debug_access(
            _request_with_host("203.0.113.10"),
            x_local_debug_token=token,
        )

    assert excinfo.value.status_code == 404


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


def test_estimate_error_response_does_not_expose_internal_exception_text(monkeypatch) -> None:
    async def fail_execute_intake_turn(**_: Any) -> dict[str, Any]:
        raise RuntimeError("internal estimate marker should not leak")

    monkeypatch.setattr(intake_routes, "execute_intake_turn", fail_execute_intake_turn)
    client = _client()

    response = client.post(
        "/estimate",
        json={"user_id": "public-hardening", "text": "tea egg", "local_date": "2026-05-06"},
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload == {
        "request_id": payload["request_id"],
        "error": "internal_server_error",
        "coach_message": "處理這則訊息時發生錯誤，請稍後再試。",
        "payload": None,
    }
    assert "internal estimate marker" not in response.text
    assert str(Path("app/intake/interface/intake_error_response.py")) not in response.text


def test_public_trace_refs_redact_internal_debug_locations() -> None:
    public_refs = build_trace_refs(request_id="req-public")
    internal_refs = build_internal_trace_refs(request_id="req-public")

    assert public_refs == {"request_id": "req-public"}
    assert internal_refs["request_id"] == "req-public"
    assert internal_refs["admin_trace_url"] == "/admin/trace/req-public"
    assert "request_trace_path" in internal_refs
    assert "stage_trace_path" in internal_refs


def test_ping_redacts_provider_topology() -> None:
    client = _client()

    payload = client.get("/ping").json()

    assert payload["provider"] == {"status": "ok"}
    assert payload["manager_provider"] == {"status": "ok"}
    assert payload["search"] == {"status": "ok"}
    assert payload["extract"] == {"status": "ok"}
    assert "base_url" not in str(payload)
    assert "timeout_seconds" not in str(payload)


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
