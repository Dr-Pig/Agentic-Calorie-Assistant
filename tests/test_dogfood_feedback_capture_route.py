from __future__ import annotations

import json
import secrets

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.composition import accurate_intake_debug_routes
from app.routes import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_local_feedback_route_writes_trace_linked_record_without_promotion(
    monkeypatch,
    tmp_path,
) -> None:
    token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    monkeypatch.setattr(
        accurate_intake_debug_routes,
        "DOGFOOD_FEEDBACK_DIR",
        tmp_path / "feedback",
        raising=False,
    )
    client = _client()

    response = client.post(
        "/accurate-intake/feedback",
        headers={"X-Local-Debug-Token": token},
        json={
            "category": "latency",
            "feedback_text": "The turn took too long.",
            "page": "chat",
            "selected_date": "2026-05-10",
            "user_external_id": "local-self-use-001",
            "trace_id": "trace-latency-001",
            "message_id": "assistant-1",
            "severity": "high",
            "ui_event": {
                "route": "/static/accurate-intake-chat.html",
                "api_duration_ms": 197000,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "captured"
    assert payload["local_only"] is True
    assert payload["do_not_commit"] is True
    assert payload["manager_context_injection_allowed"] is False
    assert payload["food_kb_truth_update_allowed"] is False
    assert payload["canonical_eval_promotion_allowed"] is False
    assert payload["linked_context"]["trace_id"] == "trace-latency-001"

    jsonl_path = tmp_path / "feedback" / "accurate_intake_dogfood_feedback.jsonl"
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["feedback_id"] == payload["feedback_id"]
    assert rows[0]["ui_event"]["api_duration_ms"] == 197000
