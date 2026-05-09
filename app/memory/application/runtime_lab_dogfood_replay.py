from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from app.memory.application.runtime_lab_candidate_extraction import (
    extract_candidate_from_ingress_event,
)
from app.memory.application.runtime_lab_memory_edd import EXPECTED_RUNTIME_EFFECTS
from app.memory.application.runtime_lab_trace_ingress import (
    MemoryIngressScopeError,
    build_memory_ingress_event_from_manager_trace,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract

SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_dogfood_replay"
)

ALLOWED_SPLITS = {"fixture", "holdout", "negative"}
ALLOWED_OUTCOMES = {"candidate", "rejected"}
NON_CLAIMS = [
    "not_product_activation_evidence",
    "not_private_self_use_approval",
    "not_mainline_manager_memory_context_injection",
    "not_durable_product_memory",
]

def build_memory_dogfood_replay_review_artifact(
    reviewed_records: list[Mapping[str, Any]],
) -> dict[str, Any]:
    reviewed_case_proposals: list[dict[str, Any]] = []
    rejected_records: list[dict[str, Any]] = []
    blockers: list[str] = []

    for index, record in enumerate(reviewed_records):
        case, rejected = _build_reviewed_case(record, index)
        if rejected:
            rejected_records.append(rejected)
            blockers.extend(rejected["blockers"])
            continue
        reviewed_case_proposals.append(case)

    proposed_split_counts = Counter(str(case["split"]) for case in reviewed_case_proposals)
    if not reviewed_case_proposals and not blockers:
        blockers.append("no_reviewed_dogfood_case_proposals")

    return {
        "artifact_type": "runtime_lab_memory_dogfood_replay_review",
        "status": "pass" if reviewed_case_proposals and not blockers else "blocked",
        "owner": "app/memory",
        "consumer": "runtime_lab_memory_quality_report",
        "retirement_trigger": "approved_memory_runtime_activation_plan",
        "reviewed_case_count": len(reviewed_case_proposals),
        "rejected_record_count": len(rejected_records),
        "proposed_split_counts": dict(sorted(proposed_split_counts.items())),
        "reviewed_case_proposals": reviewed_case_proposals,
        "rejected_records": rejected_records,
        "blockers": blockers,
        "runtime_connected": True,
        "lab_isolated": True,
        "live_evidence_required_for_merge": False,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "shadow_memory_context_pack_used": False,
        "manager_context_injected": False,
        "memory_store_written": False,
        "non_claims": list(NON_CLAIMS),
    }

def write_memory_dogfood_replay_review_artifact(
    path: Path,
    reviewed_records: list[Mapping[str, Any]],
) -> dict[str, Any]:
    from app.shared.infra.json_artifacts import write_json_artifact

    artifact = build_memory_dogfood_replay_review_artifact(reviewed_records)
    write_json_artifact(path, artifact)
    return artifact

def _build_reviewed_case(
    record: Mapping[str, Any],
    index: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    trace = _mapping(record.get("trace"))
    review = _mapping(record.get("review"))
    trace_request_id = _request_id(trace, index)

    review_blockers = _review_blockers(trace_request_id, review)
    if review_blockers:
        return {}, _rejected(trace_request_id, review_blockers)

    try:
        event = build_memory_ingress_event_from_manager_trace(trace)
    except MemoryIngressScopeError as exc:
        return {}, _rejected(trace_request_id, [f"{trace_request_id}.{exc}"])

    extraction = extract_candidate_from_ingress_event(event)
    mismatch_blockers = _extraction_mismatch_blockers(
        trace_request_id,
        review,
        extraction,
    )
    if mismatch_blockers:
        return {}, _rejected(trace_request_id, mismatch_blockers)

    return _reviewed_edd_case(event, review, extraction), None

def _review_blockers(case_id: str, review: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not review.get("reviewer_id"):
        blockers.append(f"{case_id}.missing_review_reviewer_id")
    if (
        review.get("semantic_oracle_source") != "product_rule_and_trace_fields"
        or review.get("raw_keyword_route_allowed") is not False
    ):
        blockers.append(f"{case_id}.raw_keyword_semantic_oracle_blocked")
    if str(review.get("split") or "") not in ALLOWED_SPLITS:
        blockers.append(f"{case_id}.invalid_split")
    if not review.get("case_type"):
        blockers.append(f"{case_id}.missing_case_type")
    if str(review.get("expected_outcome") or "") not in ALLOWED_OUTCOMES:
        blockers.append(f"{case_id}.invalid_expected_outcome")
    if review.get("expected_outcome") == "candidate" and not review.get(
        "expected_candidate_type"
    ):
        blockers.append(f"{case_id}.missing_expected_candidate_type")
    if review.get("source_ref_confirmation") is not True:
        blockers.append(f"{case_id}.source_ref_not_review_confirmed")
    return blockers

def _extraction_mismatch_blockers(
    case_id: str,
    review: Mapping[str, Any],
    extraction: Mapping[str, Any],
) -> list[str]:
    expected_outcome = str(review["expected_outcome"])
    if extraction.get("outcome") != expected_outcome:
        return [f"{case_id}.expected_{expected_outcome}_got_{extraction.get('outcome')}"]
    if expected_outcome == "candidate" and extraction.get("candidate_type") != review.get(
        "expected_candidate_type"
    ):
        return [f"{case_id}.candidate_type_mismatch"]
    if expected_outcome == "candidate":
        candidate = _mapping(extraction.get("candidate"))
        if not candidate.get("source_object_refs"):
            return [f"{case_id}.missing_candidate_source_refs"]
    return []


def _reviewed_edd_case(
    event: Mapping[str, Any],
    review: Mapping[str, Any],
    extraction: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = _mapping(extraction.get("candidate"))
    source_refs = [str(ref) for ref in candidate.get("source_object_refs", []) if ref]
    payload = _mapping(candidate.get("payload"))
    manager_decision_field = str(payload.get("manager_decision_field"))

    return {
        "case_id": f"dogfood_{event['request_id']}",
        "case_type": str(review["case_type"]),
        "split": str(review["split"]),
        "source": "dogfood_replay",
        "review": {
            "reviewer_id": str(review["reviewer_id"]),
            "source_ref_confirmation": True,
            "expected_outcome": str(review["expected_outcome"]),
        },
        "trace_fields": {
            "manager_decision_field": manager_decision_field,
            "source_refs": source_refs,
        },
        "expected_candidate": {
            "candidate_type": str(extraction["candidate_type"]),
            "review_status": "pending",
            "promotion_allowed_now": False,
            "human_review_required": True,
        },
        "oracle": {
            "semantic_oracle_source": "product_rule_and_trace_fields",
            "raw_keyword_route_allowed": False,
        },
        "canonical_source_refs": event["canonical_source_refs"],
        "expected_runtime_effects": dict(EXPECTED_RUNTIME_EFFECTS),
    }


def _rejected(case_id: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "outcome": "rejected",
        "blockers": blockers,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def _request_id(trace: Mapping[str, Any], index: int) -> str:
    return str(trace.get("request_id") or f"dogfood_record_{index}")


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_memory_dogfood_replay_review_artifact",
    "write_memory_dogfood_replay_review_artifact",
]
