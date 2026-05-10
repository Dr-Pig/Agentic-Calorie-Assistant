from __future__ import annotations

import json
from pathlib import Path
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
    monkeypatch.setattr(
        accurate_intake_debug_routes,
        "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH",
        tmp_path / "review_queue.json",
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
                "source_page": "chat",
                "api_duration_ms": 197000,
            },
            "operation_context": {
                "submitted_endpoint": "/accurate-intake/feedback",
                "http_status": 200,
                "duration_ms": 516,
                "page_url": "http://127.0.0.1:8787/static/accurate-intake-chat.html",
                "page_path": "/static/accurate-intake-chat.html",
                "referrer": "/static/accurate-intake-today.html",
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
    assert payload["linked_context"]["page"] == "chat"
    assert payload["linked_context"]["trace_id"] == "trace-latency-001"
    assert payload["linked_context"]["message_id"] == "assistant-1"
    assert payload["ui_event"]["source_page"] == "chat"
    assert payload["operation_context"]["submitted_endpoint"] == "/accurate-intake/feedback"
    assert payload["operation_context"]["http_status"] == 200
    assert payload["operation_context"]["duration_ms"] == 516
    assert payload["operation_context"]["page_path"] == "/static/accurate-intake-chat.html"

    jsonl_path = tmp_path / "feedback" / "accurate_intake_dogfood_feedback.jsonl"
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["feedback_id"] == payload["feedback_id"]
    assert rows[0]["ui_event"]["api_duration_ms"] == 197000
    assert rows[0]["ui_event"]["source_page"] == "chat"
    assert rows[0]["operation_context"]["submitted_endpoint"] == "/accurate-intake/feedback"


def test_local_review_queue_route_reads_feedback_without_promotion(
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
    monkeypatch.setattr(
        accurate_intake_debug_routes,
        "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH",
        tmp_path / "review_queue.json",
        raising=False,
    )
    client = _client()

    feedback_response = client.post(
        "/accurate-intake/feedback",
        headers={"X-Local-Debug-Token": token},
        json={
            "category": "ui_ux",
            "feedback_text": "The review path was hard to find.",
            "page": "feedback",
            "selected_date": "2026-05-10",
            "user_external_id": "local-self-use-001",
            "trace_id": "trace-ui-001",
            "severity": "medium",
        },
    )
    assert feedback_response.status_code == 200

    response = client.get(
        "/accurate-intake/review-queue",
        headers={"X-Local-Debug-Token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_type"] == "accurate_intake_dogfood_review_queue"
    assert payload["claim_scope"] == "local_dogfood_review_queue_artifact"
    assert payload["feedback_triage_record_count"] == 1
    assert payload["desktop_feedback_records"][0]["category"] == "ui_ux"
    assert payload["desktop_feedback_records"][0]["linked_context"]["trace_id"] == "trace-ui-001"
    assert payload["source_feedback_store_exists"] is True
    assert payload["manager_context_injection_allowed"] is False
    assert payload["food_kb_truth_update_allowed"] is False
    assert payload["canonical_eval_promotion_allowed"] is False
    assert payload["product_truth_update_allowed"] is False
    assert payload["promotion_policy"]["feedback_can_create_product_truth"] is False


def test_local_feedback_review_and_data_routes_accept_local_debug_session_cookie(
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
    monkeypatch.setattr(
        accurate_intake_debug_routes,
        "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH",
        tmp_path / "review_queue.json",
        raising=False,
    )
    client = _client()

    establish = client.post("/accurate-intake/local-debug-session", json={"token": token})
    feedback = client.post(
        "/accurate-intake/feedback",
        json={
            "category": "bug",
            "feedback_text": "Cookie-only protected route check.",
            "page": "review",
            "selected_date": "2026-05-10",
            "user_external_id": "local-self-use-001",
        },
    )
    review = client.get("/accurate-intake/review-queue")
    data = client.get("/accurate-intake/local-data-hygiene")

    assert establish.status_code == 204
    assert feedback.status_code == 200
    assert review.status_code == 200
    assert data.status_code == 200
    assert review.json()["feedback_triage_record_count"] == 1
    assert data.json()["artifact_type"] == "accurate_intake_local_operator_data_hygiene_bundle"


def test_local_feedback_route_preserves_minimal_payload_with_empty_operation_context(
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
            "category": "bug",
            "feedback_text": "Minimal payload should still work.",
            "page": "chat",
            "selected_date": "2026-05-10",
            "user_external_id": "local-self-use-001",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "captured"
    assert payload["operation_context"]["submitted_endpoint"] == "/accurate-intake/feedback"
    assert payload["operation_context"]["http_status"] == 200
    assert isinstance(payload["operation_context"]["duration_ms"], int)


def test_feedback_page_collects_operation_context_for_submit_request() -> None:
    page = (
        Path("static/accurate-intake-feedback.html").read_text(encoding="utf-8")
    )

    assert "performance.now()" in page
    assert "submitted_endpoint: endpoints.feedback" in page
    assert "http_status: null" in page
    assert "duration_ms: null" in page
    assert "client_request_started_at_ms: Math.round(performance.now())" in page
    assert "page_url: window.location.href" in page
    assert "page_path: window.location.pathname" in page
    assert "referrer: document.referrer" in page


def test_review_page_displays_feedback_operation_context_fields() -> None:
    page = Path("static/accurate-intake-review.html").read_text(encoding="utf-8")

    assert "record.operation_context" in page
    assert "submitted_endpoint" in page
    assert "http_status" in page
    assert "duration_ms" in page
    assert "page_path" in page
    assert "referrer" in page


def test_local_review_queue_route_preserves_existing_review_candidates(
    monkeypatch,
    tmp_path,
) -> None:
    token = secrets.token_urlsafe(24)
    review_path = tmp_path / "review_queue.json"
    feedback_dir = tmp_path / "feedback"
    feedback_dir.mkdir()
    feedback_dir.joinpath("accurate_intake_dogfood_feedback.jsonl").write_text(
        json.dumps(
            {
                "artifact_type": "accurate_intake_dogfood_feedback_record",
                "feedback_id": "feedback-live",
                "category": "latency",
                "feedback_text": "Slow turn.",
                "linked_context": {"trace_id": "trace-live"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    review_path.write_text(
        json.dumps(
            {
                "artifact_type": "accurate_intake_dogfood_review_queue",
                "review_candidates": [
                    {
                        "status": "review_candidate",
                        "trace_id": "trace-existing",
                        "auto_flags": ["evidence_gap"],
                    }
                ],
                "correction_feedback_events": [
                    {"event_type": "user_correction_feedback", "trace_id": "trace-correction"}
                ],
                "desktop_feedback_records": [
                    {
                        "feedback_id": "feedback-existing",
                        "category": "ui_ux",
                        "feedback_text": "Needs review.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    monkeypatch.setattr(
        accurate_intake_debug_routes,
        "DOGFOOD_FEEDBACK_DIR",
        feedback_dir,
        raising=False,
    )
    monkeypatch.setattr(
        accurate_intake_debug_routes,
        "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH",
        review_path,
        raising=False,
    )
    client = _client()

    response = client.get(
        "/accurate-intake/review-queue",
        headers={"X-Local-Debug-Token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_review_queue_artifact_exists"] is True
    assert payload["review_candidate_count"] == 1
    assert payload["review_candidates"][0]["trace_id"] == "trace-existing"
    assert payload["correction_feedback_event_count"] == 1
    assert {
        record["feedback_id"]
        for record in payload["desktop_feedback_records"]
    } == {"feedback-existing", "feedback-live"}
