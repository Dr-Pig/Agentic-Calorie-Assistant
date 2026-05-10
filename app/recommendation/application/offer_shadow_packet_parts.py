from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.offer_shadow_packet_policy import (
    FALSE_FLAGS,
    MEMORY_MATCH_SIGNALS,
    QUALITY_REPORT,
    REPORT_FORBIDDEN_TRUE_FLAGS,
    THREE_NODE_ARTIFACT,
    decision_ownership,
)
from app.recommendation.application.three_node_summary_bridge import (
    REQUIRED_LOGICAL_STAGES,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.offer_shadow_packet_parts"
)


def build_offer_packet_artifact(
    *,
    status: str,
    blockers: list[str],
    report: Mapping[str, Any],
    three_node_artifact: Mapping[str, Any],
    selected_primary: dict[str, Any] | None,
    backup_candidates: list[dict[str, Any]],
    offer_synthesis_trace: dict[str, Any],
    ux_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_type": "recommendation_offer_shadow_packet",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/recommendation",
        "consumer": "future_chat_first_recommendation_shadow_review",
        "retirement_trigger": "approved_recommendation_runtime_activation_plan",
        "source_recommendation_artifact_type": three_node_artifact.get("artifact_type"),
        "source_quality_report_artifact_type": report.get("artifact_type"),
        "canonical_recommendation_graph": report.get("canonical_recommendation_graph"),
        "physical_node_order": string_list(three_node_artifact.get("physical_node_order")),
        "logical_stage_trace": logical_stage_trace(report, three_node_artifact),
        "selected_primary": selected_primary,
        "backup_candidates": backup_candidates,
        "offer_synthesis_trace": offer_synthesis_trace,
        "ux_packet": ux_packet,
        "decision_ownership": decision_ownership(),
        "blockers": blockers,
        "local_only": True,
        "diagnostic_only": True,
        "shadow_only": True,
        "non_claims": [
            "not_recommendation_serving",
            "not_user_facing_response",
            "not_intake_handoff",
            "not_recommendation_intent_state",
            "not_runtime_activation_evidence",
        ],
        **dict(FALSE_FLAGS),
    }


def input_blockers(
    report: Mapping[str, Any],
    artifact: Mapping[str, Any],
) -> list[str]:
    return [*quality_report_blockers(report), *three_node_artifact_blockers(artifact)]


def quality_report_blockers(report: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if report.get("artifact_type") != QUALITY_REPORT:
        blockers.append("recommendation_quality_report.unsupported_artifact_type")
    if report.get("status") != "pass":
        blockers.append("recommendation_quality_report.status_not_pass")
    if report.get("canonical_recommendation_graph") != "three_node":
        blockers.append("recommendation_quality_report.not_three_node_graph")
    if report.get("three_node_lab_bridge_used") is not True:
        blockers.append("recommendation_quality_report.three_node_bridge_not_used")
    if tuple(logical_stage_names(report)) != REQUIRED_LOGICAL_STAGES:
        blockers.append("recommendation_quality_report.logical_stage_trace_mismatch")
    if report.get("pool_decision") not in {"offer", "primary_plus_backup"}:
        blockers.append("recommendation_quality_report.pool_not_offer_eligible")
    for flag in REPORT_FORBIDDEN_TRUE_FLAGS:
        if report.get(flag) is True:
            blockers.append(f"recommendation_quality_report.{flag}")
    return blockers


def three_node_artifact_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != THREE_NODE_ARTIFACT:
        blockers.append("recommendation_three_node_artifact.unsupported_artifact_type")
    if artifact.get("status") != "pass":
        blockers.append("recommendation_three_node_artifact.status_not_pass")
    if len(string_list(artifact.get("physical_node_order"))) != 3:
        blockers.append("recommendation_three_node_artifact.physical_node_count_mismatch")
    for flag, value in mapping(artifact.get("activation_flags")).items():
        if value is True:
            blockers.append(
                f"recommendation_three_node_artifact.activation_flag_true:{flag}"
            )
    return blockers


def primary_blockers(primary: Mapping[str, Any], offer: Mapping[str, Any]) -> list[str]:
    if not primary:
        return ["selected_primary.not_found"]
    blockers: list[str] = []
    if primary.get("candidate_id") != str(offer.get("candidate_id") or ""):
        blockers.append("selected_primary.offer_candidate_mismatch")
    if primary.get("quality_gate_passed") is not True:
        blockers.append("selected_primary.quality_gate_not_passed")
    if primary.get("presentation_posture") == "silent":
        blockers.append("selected_primary.presentation_posture_silent")
    if not has_reviewed_memory_ref(primary, offer):
        blockers.append("selected_primary.reviewed_memory_source_ref_missing")
    return blockers


def backup_blockers(
    report: Mapping[str, Any],
    *,
    backup_candidate_ids: list[str],
) -> list[str]:
    blockers: list[str] = []
    for backup_id in backup_candidate_ids:
        candidate = candidate_evaluation(report, backup_id)
        if not candidate:
            blockers.append(f"backup_candidate.not_found:{backup_id}")
        elif candidate.get("quality_gate_passed") is not True:
            blockers.append(f"backup_candidate.quality_gate_not_passed:{backup_id}")
    return blockers


def has_reviewed_memory_ref(primary: Mapping[str, Any], offer: Mapping[str, Any]) -> bool:
    signals = {str(signal) for signal in primary.get("quality_signals") or []}
    if not signals.intersection(MEMORY_MATCH_SIGNALS):
        return False
    return bool(set(source_refs(primary)).intersection(source_refs(offer)))


def candidate_summary(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "title": str(candidate.get("title") or ""),
        "store_name": str(candidate.get("store_name") or ""),
        "estimated_kcal": int_or_none(candidate.get("estimated_kcal")),
        "source_refs": source_refs(candidate),
    }


def candidate_evaluation(report: Mapping[str, Any], candidate_id: str) -> Mapping[str, Any]:
    for item in report.get("candidate_evaluations") or []:
        if isinstance(item, Mapping) and item.get("candidate_id") == candidate_id:
            return item
    return {}


def logical_stage_trace(
    report: Mapping[str, Any],
    artifact: Mapping[str, Any],
) -> list[dict[str, str]]:
    source = report.get("logical_stage_trace") or artifact.get("logical_stage_trace")
    return [
        {
            "logical_stage": str(item.get("logical_stage") or ""),
            "physical_node": str(item.get("physical_node") or ""),
            "owner": str(item.get("owner") or ""),
        }
        for item in list_field(source)
        if isinstance(item, Mapping)
    ]


def logical_stage_names(report: Mapping[str, Any]) -> list[str]:
    return [
        str(item.get("logical_stage") or "")
        for item in list_field(report.get("logical_stage_trace"))
        if isinstance(item, Mapping)
    ]


def backup_candidate_ids(offer: Mapping[str, Any]) -> list[str]:
    return string_list(offer.get("backup_candidate_ids"))


def source_refs(candidate: Mapping[str, Any]) -> list[str]:
    return [
        str(ref)
        for ref in candidate.get("source_refs") or []
        if str(ref).startswith("memory_candidate:")
    ]


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def list_field(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None
