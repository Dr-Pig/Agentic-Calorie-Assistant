from __future__ import annotations

import re
from typing import Any


FAILURE_FAMILY_OWNERS: dict[str, list[str]] = {
    "encoding_corruption": [
        "app/intake/application/manager_tools.py",
        "app/runtime/application/reply_renderer.py",
    ],
    "schema_drift": [
        "app/runtime/agent/manager.py",
        "app/runtime/agent/manager_support.py",
        "app/providers/builderspace_adapter.py",
    ],
    "tool_routing_gap": [
        "app/intake/application/manager_tools.py",
        "app/runtime/agent/manager.py",
    ],
    "response_fallback_pollution": [
        "app/runtime/application/reply_renderer.py",
        "app/runtime/application/sidecar_service.py",
    ],
    "persistence_pollution": [
        "app/intake/application/commit_service.py",
        "app/intake/application/manager_tools.py",
    ],
    "unknown": [],
}


def _payload(trace: dict[str, Any]) -> dict[str, Any]:
    return dict(trace.get("payload") or {})


def _trace_contract(trace: dict[str, Any]) -> dict[str, Any]:
    payload_contract = _payload(trace).get("trace_contract")
    if isinstance(payload_contract, dict):
        return dict(payload_contract)
    contract = trace.get("trace_contract")
    if isinstance(contract, dict):
        return dict(contract)
    return {}


def _request_text(trace: dict[str, Any]) -> str:
    request = trace.get("request")
    if isinstance(request, dict):
        return str(request.get("text") or "")
    return ""


def _reply_text(trace: dict[str, Any]) -> str:
    payload = _payload(trace)
    return str(payload.get("reply_text") or trace.get("reply_text") or "")


def _llm_traces(trace: dict[str, Any]) -> list[dict[str, Any]]:
    traces = trace.get("llm_traces")
    if isinstance(traces, list):
        return [dict(item) for item in traces if isinstance(item, dict)]
    return []


def _looks_mojibake(text: str) -> bool:
    if not text:
        return False
    if "\ufffd" in text:
        return True
    punct_noise = len(re.findall(r"\?[^\s]", text)) + len(re.findall(r"[^\s]\?", text))
    return punct_noise >= 6


def _has_encoding_corruption(trace: dict[str, Any]) -> bool:
    texts = [_request_text(trace), _reply_text(trace)]
    for item in _llm_traces(trace):
        texts.append(str(item.get("raw_content") or ""))
        texts.append(str(item.get("error") or ""))
    return any(_looks_mojibake(text) for text in texts if text)


def classify_failure_family(trace: dict[str, Any]) -> str:
    if _has_encoding_corruption(trace):
        return "encoding_corruption"

    for item in _llm_traces(trace):
        error = str(item.get("error") or "")
        if "missing_fields" in error or "json" in error.lower() or "schema" in error.lower():
            return "schema_drift"

    tool_trace = (_trace_contract(trace).get("tool_decision_trace") or {})
    if isinstance(tool_trace, dict):
        candidate = tool_trace.get("candidate_tool_calls") or []
        executed = tool_trace.get("executed_tool_calls") or []
        if candidate and not [entry for entry in executed if str(entry.get("status") or "") == "executed"]:
            return "tool_routing_gap"

    reply_text = _reply_text(trace)
    if any(token in reply_text for token in ("0 kcal", "0g")):
        return "response_fallback_pollution"

    persistence = (_trace_contract(trace).get("persistence_decision") or {})
    unresolved = _trace_contract(trace).get("unresolved_info") or []
    if isinstance(persistence, dict) and str(persistence.get("status") or "") == "completed_meal" and unresolved:
        return "persistence_pollution"

    return "unknown"


def build_live_trace_triage(trace: dict[str, Any], *, expected_behavior: str = "") -> dict[str, Any]:
    failure_family = classify_failure_family(trace)
    return {
        "user_input": _request_text(trace),
        "expected_behavior": expected_behavior,
        "actual_reply": _reply_text(trace),
        "request_failure_family": failure_family,
        "suspected_root_cause_bucket": failure_family,
        "owner_file": FAILURE_FAMILY_OWNERS.get(failure_family, []),
    }
