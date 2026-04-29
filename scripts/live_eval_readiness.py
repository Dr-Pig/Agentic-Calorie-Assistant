from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_LOCAL_LIVE_BASE_URL = "http://127.0.0.1:8010"
DIAGNOSTIC_LIVE_SCOPE = "diagnostic_live_smoke"
READINESS_CANDIDATE_SCOPE = "live_readiness_candidate"
PHASE_C_SAME_TRUTH_FAILURE = "phase_c_same_truth_contradiction"

PHASE_C_LIVE_BLOCKING_CHECKS = (
    "phase_c_trace_present",
    "phase_c_same_truth_gate_checked",
    "phase_c_same_truth_gate_not_hard_fail",
    "phase_c_no_same_truth_hard_fail_condition",
    "phase_c_mutation_outcome_present",
    "phase_c_same_truth_read_result_present",
)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def live_test_mode_from_base_url(*, base_url_explicit: bool) -> str:
    return "readiness" if base_url_explicit else "diagnostic"


def readiness_claim_scope(*, live_test_mode: str) -> str:
    return READINESS_CANDIDATE_SCOPE if live_test_mode == "readiness" else DIAGNOSTIC_LIVE_SCOPE


def fetch_server_ping(base_url: str, *, timeout_seconds: int = 15) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        req = urllib.request.Request(urllib.parse.urljoin(base_url, "/ping"), method="GET")
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except Exception as exc:  # pragma: no cover - exercised through callers against live servers.
        return None, {"type": type(exc).__name__, "message": str(exc)}


def build_live_preflight_report(
    *,
    base_url: str,
    base_url_explicit: bool,
    ping_payload: dict[str, Any] | None,
    ping_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = live_test_mode_from_base_url(base_url_explicit=base_url_explicit)
    ping = _dict(ping_payload)
    server_ping_status = "pass" if ping and not ping_error else "fail"
    provider_readiness = {
        "provider": ping.get("provider"),
        "manager_provider": ping.get("manager_provider"),
        "search": ping.get("search"),
        "extract": ping.get("extract"),
    }
    return {
        "live_test_mode": mode,
        "base_url": base_url,
        "base_url_explicit": base_url_explicit,
        "server_ping_status": server_ping_status,
        "server_ping_error": ping_error,
        "provider_readiness": provider_readiness,
        "readiness_claim_scope": readiness_claim_scope(live_test_mode=mode),
    }


def _phase_c_surface_present_or_not_available(value: Any) -> bool:
    if value == "not_available":
        return True
    if not isinstance(value, dict):
        return False
    if value.get("status") == "not_available":
        return True
    return bool(value)


def build_phase_c_live_readiness(
    *,
    response: dict[str, Any] | None,
    trace: dict[str, Any] | None,
) -> dict[str, Any]:
    response_data = _dict(response)
    trace_data = _dict(trace)
    phase_c_trace = _dict(trace_data.get("phase_c_trace") or response_data.get("phase_c_trace"))
    same_truth_gate = _dict(phase_c_trace.get("same_truth_closure_gate"))
    hard_fail_conditions = _list(response_data.get("hard_fail_conditions"))
    gate_status = str(same_truth_gate.get("status") or "not_available")
    mutation_outcome = phase_c_trace.get("mutation_outcome")
    same_truth_read_result = phase_c_trace.get("same_truth_read_result")

    checks = {
        "phase_c_trace_present": bool(phase_c_trace),
        "phase_c_same_truth_gate_checked": same_truth_gate.get("checked") is True,
        "phase_c_same_truth_gate_not_hard_fail": gate_status != "hard_fail",
        "phase_c_no_same_truth_hard_fail_condition": PHASE_C_SAME_TRUTH_FAILURE not in hard_fail_conditions,
        "phase_c_mutation_outcome_present": _phase_c_surface_present_or_not_available(mutation_outcome),
        "phase_c_same_truth_read_result_present": _phase_c_surface_present_or_not_available(same_truth_read_result),
    }
    return {
        "checks": checks,
        "summary": {
            "status": gate_status,
            "failure_family": same_truth_gate.get("failure_family"),
            "hard_fail_conditions": hard_fail_conditions,
            "readiness_pass": all(checks.values()),
        },
    }


def summarize_phase_c_gate_status(case_results: list[dict[str, Any]]) -> str:
    statuses: list[str] = []
    readiness_failed = False
    for case_result in case_results:
        readiness = _dict(_dict(case_result.get("extra")).get("phase_c_live_readiness"))
        if not readiness:
            continue
        statuses.append(str(readiness.get("status") or "not_available"))
        readiness_failed = readiness_failed or not bool(readiness.get("readiness_pass"))
    if not statuses:
        return "not_applicable"
    if "hard_fail" in statuses:
        return "hard_fail"
    if readiness_failed:
        return "flagged"
    if any(status == "flagged" for status in statuses):
        return "flagged"
    return "pass"


__all__ = [
    "DEFAULT_LOCAL_LIVE_BASE_URL",
    "DIAGNOSTIC_LIVE_SCOPE",
    "PHASE_C_LIVE_BLOCKING_CHECKS",
    "PHASE_C_SAME_TRUTH_FAILURE",
    "READINESS_CANDIDATE_SCOPE",
    "build_live_preflight_report",
    "build_phase_c_live_readiness",
    "fetch_server_ping",
    "live_test_mode_from_base_url",
    "readiness_claim_scope",
    "summarize_phase_c_gate_status",
]
