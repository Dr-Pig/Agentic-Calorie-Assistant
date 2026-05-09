from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.memory.application.runtime_lab_candidate_records import (
    candidate_extraction_artifact,
    candidate_record,
    rejection_record,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_candidate_extraction"
)

REJECTED_CANDIDATE_TYPES = {"none"}


def build_candidate_extraction_artifact_from_edd_suite(
    suite: Mapping[str, Any],
) -> dict[str, Any]:
    results = [extract_candidate_from_edd_case(case) for case in suite.get("cases", [])]
    candidates = [result["candidate"] for result in results if result["outcome"] == "candidate"]
    rejections = [result for result in results if result["outcome"] == "rejected"]
    return candidate_extraction_artifact(
        case_results=results,
        candidates=candidates,
        rejections=rejections,
        runtime_connected=False,
        live_dogfood_replay=False,
    )


def extract_candidate_from_edd_case(case: Mapping[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("case_id") or "unknown_case")
    trace_fields = _mapping(case.get("trace_fields"))
    expected_candidate = _mapping(case.get("expected_candidate"))
    oracle = _mapping(case.get("oracle"))

    if _uses_raw_keyword_oracle(oracle):
        return rejection_record(case_id, "raw_keyword_semantic_oracle_blocked")
    if not trace_fields.get("manager_decision_field"):
        return rejection_record(case_id, "missing_manager_decision_field")

    candidate_type = str(expected_candidate.get("candidate_type") or "none")
    if candidate_type in REJECTED_CANDIDATE_TYPES:
        return rejection_record(
            case_id,
            str(expected_candidate.get("rejection_reason") or "not_memory_candidate"),
        )

    candidate = candidate_record(
        case_id=case_id,
        candidate_type=candidate_type,
        scope_keys={
            "user_id": "synthetic-user",
            "workspace_id": "synthetic-workspace",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "edd_fixture",
            "run_id": case_id,
        },
        source_refs=_source_refs(trace_fields),
        payload=dict(expected_candidate),
        reason_codes=[str(trace_fields["manager_decision_field"])],
        runtime_connected=False,
    )
    return {
        "case_id": case_id,
        "outcome": "candidate",
        "candidate_type": candidate_type,
        "candidate": candidate,
    }


def build_candidate_extraction_artifact_from_ingress_events(
    events: list[Mapping[str, Any]],
    *,
    live_dogfood_replay: bool = False,
) -> dict[str, Any]:
    results = [extract_candidate_from_ingress_event(event) for event in events]
    candidates = [result["candidate"] for result in results if result["outcome"] == "candidate"]
    rejections = [result for result in results if result["outcome"] == "rejected"]
    return candidate_extraction_artifact(
        case_results=results,
        candidates=candidates,
        rejections=rejections,
        runtime_connected=True,
        live_dogfood_replay=live_dogfood_replay,
    )


def extract_candidate_from_ingress_event(event: Mapping[str, Any]) -> dict[str, Any]:
    request_id = str(event.get("request_id") or "unknown_request")
    source_trace = _mapping(event.get("sanitized_source_trace"))
    signal = _mapping(source_trace.get("memory_lab_candidate_signal"))
    if not signal:
        return rejection_record(request_id, "no_memory_candidate_signal")
    if not signal.get("manager_decision_field"):
        return rejection_record(request_id, "missing_manager_decision_field")

    candidate_type = str(signal.get("candidate_type") or "none")
    if candidate_type in REJECTED_CANDIDATE_TYPES:
        return rejection_record(
            request_id,
            str(signal.get("rejection_reason") or "not_memory_candidate"),
        )

    candidate = candidate_record(
        case_id=request_id,
        candidate_type=candidate_type,
        scope_keys=dict(_mapping(event.get("scope_keys"))),
        source_refs=[str(ref) for ref in signal.get("source_refs", []) if ref],
        payload=dict(signal),
        reason_codes=[str(code) for code in signal.get("reason_codes", []) if code],
        runtime_connected=True,
    )
    return {
        "case_id": request_id,
        "outcome": "candidate",
        "candidate_type": candidate_type,
        "candidate": candidate,
    }


def write_candidate_extraction_artifact_from_trace(
    path: Path,
    trace: Mapping[str, Any],
    *,
    live_dogfood_replay: bool = False,
) -> dict[str, Any]:
    from app.memory.application.runtime_lab_trace_ingress import (
        build_memory_ingress_event_from_manager_trace,
    )
    from app.shared.infra.json_artifacts import write_json_artifact

    event = build_memory_ingress_event_from_manager_trace(trace)
    artifact = build_candidate_extraction_artifact_from_ingress_events(
        [event],
        live_dogfood_replay=live_dogfood_replay,
    )
    write_json_artifact(path, artifact)
    return artifact


def _source_refs(trace_fields: Mapping[str, Any]) -> list[str]:
    return [str(ref) for ref in trace_fields.get("source_refs", []) if ref]


def _uses_raw_keyword_oracle(oracle: Mapping[str, Any]) -> bool:
    return (
        oracle.get("semantic_oracle_source") != "product_rule_and_trace_fields"
        or oracle.get("raw_keyword_route_allowed") is not False
        or "raw_input_keyword" in oracle
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_candidate_extraction_artifact_from_edd_suite",
    "build_candidate_extraction_artifact_from_ingress_events",
    "extract_candidate_from_edd_case",
    "extract_candidate_from_ingress_event",
    "write_candidate_extraction_artifact_from_trace",
]
