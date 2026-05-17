from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.intake.interface import intake_error_response
from app.providers.builderspace_adapter import BuilderSpaceResponseError
from app.schemas import EstimateRequest


def test_estimate_error_response_records_provider_timeout_without_user_debug_leak(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    trace_payloads: list[dict[str, Any]] = []
    audit_events: list[Any] = []

    def fake_write_request_trace_artifact(request_id: str, payload: dict[str, Any]) -> Path:
        trace_payloads.append(payload)
        return tmp_path / f"{request_id}.json"

    monkeypatch.setattr(intake_error_response, "write_request_trace_artifact", fake_write_request_trace_artifact)
    monkeypatch.setattr(intake_error_response, "append_audit_event", audit_events.append)

    exc = BuilderSpaceResponseError(
        "BuilderSpace manager error at stage=intake_manager_round: ReadTimeout: ",
        trace={
            "stage": "intake_manager_round",
            "provider": "builderspace",
            "model": "grokfast",
            "failure_family": "provider_timeout",
            "failing_component": "builderspace_adapter.complete_with_trace",
            "timeout_seconds": 30,
            "transport_attempts": [{"attempt_index": 0, "error_type": "ReadTimeout"}],
            "parse_attempts": [],
            "schema_name": "manager_loop_decision",
            "schema_version": "v1",
            "decision_transport_mode": "json_schema",
            "structured_output_transport_mode": "json_schema",
            "cache_metrics": {"cached_tokens": None},
            "request_payload": {"messages": ["should stay out of public response"]},
        },
    )

    response = intake_error_response.build_estimate_error_response(
        request_id="timeout-req",
        request=EstimateRequest(text="早餐吃鐵板麵套餐", allow_search=True, user_id="self-use"),
        source_page_version="test-page",
        exc=exc,
    )

    public_payload = json.loads(response.body)
    public_text = response.body.decode("utf-8")
    assert response.status_code == 500
    assert public_payload["error"] == "internal_server_error"
    assert public_payload["payload"] is None
    assert "系統剛剛等模型回覆太久" in public_payload["coach_message"]
    assert "ReadTimeout" not in public_text
    assert "builderspace_adapter" not in public_text
    assert "should stay out" not in public_text

    assert trace_payloads[0]["exception_family"] == "provider_timeout"
    assert trace_payloads[0]["error_type"] == "BuilderSpaceResponseError"
    assert trace_payloads[0]["provider_runtime"]["stage"] == "intake_manager_round"
    assert trace_payloads[0]["provider_runtime"]["timeout_seconds"] == 30
    assert "request_payload" not in trace_payloads[0]["provider_runtime"]
    assert audit_events[0].trace_artifact_path.endswith("timeout-req.json")


def test_estimate_error_response_generic_runtime_error_stays_user_safe(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    trace_payloads: list[dict[str, Any]] = []

    monkeypatch.setattr(
        intake_error_response,
        "write_request_trace_artifact",
        lambda _request_id, payload: trace_payloads.append(payload) or tmp_path / "trace.json",
    )
    monkeypatch.setattr(intake_error_response, "append_audit_event", lambda _event: None)

    response = intake_error_response.build_estimate_error_response(
        request_id="runtime-req",
        request=EstimateRequest(text="tea egg", allow_search=False, user_id="self-use"),
        source_page_version=None,
        exc=RuntimeError("internal estimate marker should not leak"),
    )

    public_text = response.body.decode("utf-8")
    public_payload = json.loads(response.body)
    assert response.status_code == 500
    assert trace_payloads[0]["exception_family"] == "runtime_error"
    assert "系統剛剛處理失敗" in public_payload["coach_message"]
    assert "internal estimate marker" not in public_text
