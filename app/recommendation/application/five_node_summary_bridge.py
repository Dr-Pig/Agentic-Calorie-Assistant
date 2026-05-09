from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.summary_consumer_quality import (
    build_recommendation_shadow_summary_consumer_quality_report,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.five_node_summary_bridge"
)

FIVE_NODE_ARTIFACT = "recommendation_five_node_lab_runner_artifact"
SUMMARY_REPORT = "recommendation_shadow_summary_consumer_quality_report"
FALSE_FLAGS = {
    "runtime_connected": False,
    "recommendation_served": False,
    "proactive_sent": False,
    "live_search_used": False,
    "ranking_llm_invoked": False,
    "intake_handoff_created": False,
    "mutation_changed": False,
    "meal_thread_mutated": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "durable_memory_written": False,
    "manager_context_packet_changed": False,
    "manager_context_injected": False,
}


def build_summary_quality_report_from_five_node_lab_artifact(
    *,
    memory_summary_projection: Mapping[str, Any],
    five_node_artifact: Mapping[str, Any],
    source_payload: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = _artifact_blockers(five_node_artifact)
    selected_candidate_id = _selected_candidate_id(five_node_artifact)

    source_candidate: Mapping[str, Any] = {}
    if not blockers:
        source_candidate = _source_candidate(source_payload, selected_candidate_id)
        blockers.extend(
            _source_candidate_blockers(source_candidate, selected_candidate_id)
        )
    if blockers:
        return _blocked_report(memory_summary_projection, five_node_artifact, blockers)

    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=memory_summary_projection,
        prepared_candidates=[_prepared_candidate(source_payload, source_candidate)],
    )
    report["source_recommendation_artifact_type"] = five_node_artifact.get(
        "artifact_type"
    )
    report["five_node_lab_bridge_used"] = True
    report["bridge_blockers"] = []
    return report


def _artifact_blockers(artifact: Mapping[str, Any]) -> list[str]:
    if artifact.get("artifact_type") != FIVE_NODE_ARTIFACT:
        return ["recommendation_five_node_artifact.unsupported_artifact_type"]
    if artifact.get("status") != "pass":
        return ["recommendation_five_node_artifact.status_not_pass"]

    selected_id = _selected_candidate_id(artifact)
    allowed_ids = set(_allowed_candidate_ids(artifact))
    response_id = _response_candidate_id(artifact)
    blockers: list[str] = []
    if selected_id not in allowed_ids:
        blockers.append(
            f"recommendation_five_node_artifact.selected_candidate_not_allowed:{selected_id}"
        )
    if response_id != selected_id:
        blockers.append(
            f"recommendation_five_node_artifact.response_candidate_mismatch:{response_id}"
        )
    for flag, value in _mapping(artifact.get("activation_flags")).items():
        if value is True:
            blockers.append(f"recommendation_five_node_artifact.activation_flag_true:{flag}")
    return blockers


def _source_candidate_blockers(
    candidate: Mapping[str, Any],
    selected_candidate_id: str,
) -> list[str]:
    if not candidate:
        return [f"source_candidate.not_found:{selected_candidate_id}"]
    refs = [str(ref) for ref in candidate.get("source_refs", [])]
    unsafe_refs = [ref for ref in refs if not ref.startswith("memory_candidate:")]
    if unsafe_refs:
        return [f"source_candidate.unsafe_source_ref:{unsafe_refs[0]}"]
    if not refs:
        return [f"source_candidate.safe_source_refs_missing:{selected_candidate_id}"]
    return []


def _prepared_candidate(
    source_payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    budget = _mapping(source_payload.get("current_budget_view"))
    return {
        "candidate_id": str(candidate.get("candidate_id", "")),
        "title": str(candidate.get("title", "")),
        "store_name": str(candidate.get("store_name", "")),
        "store_metadata": _safe_store_metadata(candidate),
        "estimated_kcal": _int_or_none(candidate.get("estimated_kcal")),
        "remaining_budget_kcal": _int_or_none(budget.get("remaining_kcal")),
        "evidence_posture": str(candidate.get("evidence_posture", "unknown")),
        "availability_posture": str(candidate.get("availability_posture", "unknown")),
        "realistic_executable": bool(candidate.get("realistic_executable")),
        "user_accessible": bool(candidate.get("user_accessible")),
        "source_refs": [str(ref) for ref in candidate.get("source_refs", [])],
    }


def _blocked_report(
    memory_summary_projection: Mapping[str, Any],
    five_node_artifact: Mapping[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "artifact_type": SUMMARY_REPORT,
        "status": "blocked",
        "blockers": blockers,
        "owner": "app/recommendation",
        "consumer": "future recommendation/proactive activation slices",
        "retirement_trigger": "approved recommendation_runtime_activation_plan",
        "source_memory_artifact_type": memory_summary_projection.get("artifact_type"),
        "source_recommendation_artifact_type": five_node_artifact.get("artifact_type"),
        "memory_summary_projection_used": False,
        "five_node_lab_bridge_used": False,
        "candidate_count": 0,
        "candidate_evaluations": [],
        "pool_decision": "blocked",
        "primary_candidate_id": None,
        "backup_candidate_ids": [],
        "offer_candidate_ids": [],
        "rejected_candidate_ids": [],
        "local_only": True,
        "diagnostic_only": True,
        "shadow_only": True,
        "non_claims": ["not_recommendation_serving", "not_runtime_activation_evidence"],
        **dict(FALSE_FLAGS),
    }


def _source_candidate(
    source_payload: Mapping[str, Any],
    selected_candidate_id: str,
) -> Mapping[str, Any]:
    values = source_payload.get("candidate_source_fixture")
    if not isinstance(values, list):
        return {}
    for item in values:
        if isinstance(item, Mapping) and item.get("candidate_id") == selected_candidate_id:
            return item
    return {}


def _allowed_candidate_ids(artifact: Mapping[str, Any]) -> list[str]:
    retrieval = _mapping(artifact.get("candidate_retrieval"))
    values = retrieval.get("allowed_candidate_ids")
    return [str(value) for value in values] if isinstance(values, list) else []


def _selected_candidate_id(artifact: Mapping[str, Any]) -> str:
    return str(_mapping(artifact.get("ranking_synthesis")).get("selected_candidate_id", ""))


def _response_candidate_id(artifact: Mapping[str, Any]) -> str:
    return str(_mapping(artifact.get("response_offer_packet")).get("candidate_id", ""))


def _safe_store_metadata(candidate: Mapping[str, Any]) -> dict[str, str]:
    metadata = candidate.get("store_metadata")
    if not isinstance(metadata, Mapping):
        return {}
    return {
        key: str(metadata[key])
        for key in ("chain", "location_label")
        if metadata.get(key)
    }


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_summary_quality_report_from_five_node_lab_artifact",
]
