from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.summary_consumer_quality import (
    FALSE_FLAGS as SUMMARY_FALSE_FLAGS,
    build_recommendation_shadow_summary_consumer_quality_report,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.three_node_summary_bridge"
)

THREE_NODE_ARTIFACT = "recommendation_three_node_shadow_artifact"
SUMMARY_REPORT = "recommendation_shadow_summary_consumer_quality_report"
REQUIRED_LOGICAL_STAGES = (
    "recommendation_context_result",
    "candidate_spec",
    "candidate_retrieval_guard_scoring",
    "ranking_result",
    "recommendation_response_result",
)


def build_summary_quality_report_from_three_node_shadow_artifact(
    *,
    memory_summary_projection: Mapping[str, Any],
    three_node_artifact: Mapping[str, Any],
    source_payload: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = _artifact_blockers(three_node_artifact)
    selected_candidate_id = str(three_node_artifact.get("selected_candidate_id") or "")

    source_candidates: list[Mapping[str, Any]] = []
    if not blockers:
        source_candidates = _source_candidates(
            source_payload,
            candidate_ids=_ordered_allowed_candidate_ids(
                three_node_artifact,
                selected_candidate_id,
            ),
        )
        for source_candidate in source_candidates:
            blockers.extend(
                _source_candidate_blockers(
                    source_candidate,
                    str(source_candidate.get("candidate_id") or ""),
                )
            )
        missing_ids = set(_allowed_candidate_ids(three_node_artifact)) - {
            str(candidate.get("candidate_id") or "") for candidate in source_candidates
        }
        blockers.extend(f"source_candidate.not_found:{candidate_id}" for candidate_id in sorted(missing_ids))
    if blockers:
        return _blocked_report(memory_summary_projection, three_node_artifact, blockers)

    report = build_recommendation_shadow_summary_consumer_quality_report(
        memory_summary_projection=memory_summary_projection,
        prepared_candidates=[
            _prepared_candidate(source_payload, source_candidate)
            for source_candidate in source_candidates
        ],
    )
    report["source_recommendation_artifact_type"] = three_node_artifact.get(
        "artifact_type"
    )
    report["canonical_recommendation_graph"] = "three_node"
    report["three_node_lab_bridge_used"] = True
    report["five_node_lab_bridge_used"] = False
    report["logical_stage_trace"] = _logical_stage_trace(three_node_artifact)
    report["bridge_blockers"] = []
    return report


def _artifact_blockers(artifact: Mapping[str, Any]) -> list[str]:
    if artifact.get("artifact_type") != THREE_NODE_ARTIFACT:
        return ["recommendation_three_node_artifact.unsupported_artifact_type"]
    if artifact.get("status") != "pass":
        return ["recommendation_three_node_artifact.status_not_pass"]

    selected_id = str(artifact.get("selected_candidate_id") or "")
    allowed_ids = set(_allowed_candidate_ids(artifact))
    response_id = _response_candidate_id(artifact)
    blockers: list[str] = []
    if selected_id not in allowed_ids:
        blockers.append(
            f"recommendation_three_node_artifact.selected_candidate_not_allowed:{selected_id}"
        )
    if response_id != selected_id:
        blockers.append(
            f"recommendation_three_node_artifact.response_candidate_mismatch:{response_id}"
        )
    if tuple(_logical_stage_names(artifact)) != REQUIRED_LOGICAL_STAGES:
        blockers.append("recommendation_three_node_artifact.logical_stage_trace_mismatch")
    if len(_list_field(artifact.get("physical_node_order"))) != 3:
        blockers.append("recommendation_three_node_artifact.physical_node_count_mismatch")
    for flag, value in _mapping(artifact.get("activation_flags")).items():
        if value is True:
            blockers.append(
                f"recommendation_three_node_artifact.activation_flag_true:{flag}"
            )
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
    three_node_artifact: Mapping[str, Any],
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
        "source_recommendation_artifact_type": three_node_artifact.get("artifact_type"),
        "canonical_recommendation_graph": "three_node",
        "memory_summary_projection_used": False,
        "three_node_lab_bridge_used": False,
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
        **dict(SUMMARY_FALSE_FLAGS),
    }


def _source_candidates(
    source_payload: Mapping[str, Any],
    *,
    candidate_ids: list[str],
) -> list[Mapping[str, Any]]:
    wanted = set(candidate_ids)
    candidates_by_id: dict[str, Mapping[str, Any]] = {}
    for item in _list_field(source_payload.get("candidate_source_fixture")):
        if isinstance(item, Mapping):
            candidate_id = str(item.get("candidate_id") or "")
            if candidate_id in wanted:
                candidates_by_id[candidate_id] = item
    return [
        candidates_by_id[candidate_id]
        for candidate_id in candidate_ids
        if candidate_id in candidates_by_id
    ]


def _ordered_allowed_candidate_ids(
    artifact: Mapping[str, Any],
    selected_candidate_id: str,
) -> list[str]:
    ordered: list[str] = []
    if selected_candidate_id:
        ordered.append(selected_candidate_id)
    for candidate_id in _allowed_candidate_ids(artifact):
        if candidate_id not in ordered:
            ordered.append(candidate_id)
    return ordered


def _allowed_candidate_ids(artifact: Mapping[str, Any]) -> list[str]:
    guard = _mapping(artifact.get("candidate_guard"))
    values = guard.get("allowed_candidate_ids")
    return [str(value) for value in values] if isinstance(values, list) else []


def _response_candidate_id(artifact: Mapping[str, Any]) -> str:
    return str(_mapping(artifact.get("shadow_offer_packet")).get("candidate_id", ""))


def _logical_stage_trace(artifact: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "logical_stage": str(item.get("logical_stage") or ""),
            "physical_node": str(item.get("physical_node") or ""),
            "owner": str(item.get("owner") or ""),
        }
        for item in _list_field(artifact.get("logical_stage_trace"))
        if isinstance(item, Mapping)
    ]


def _logical_stage_names(artifact: Mapping[str, Any]) -> list[str]:
    return [item["logical_stage"] for item in _logical_stage_trace(artifact)]


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


def _list_field(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_summary_quality_report_from_three_node_shadow_artifact"]
