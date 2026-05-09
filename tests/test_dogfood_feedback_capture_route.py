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
