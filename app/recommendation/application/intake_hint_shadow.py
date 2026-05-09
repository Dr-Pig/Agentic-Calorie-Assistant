from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.intake_hint_shadow"
)
REPORT_ARTIFACT = "recommendation_shadow_summary_consumer_quality_report"
HANDOFF_POOL_DECISIONS = {"offer", "primary_plus_backup"}
FALSE_REPORT_FLAGS = (
    "recommendation_served",
    "proactive_sent",
    "live_search_used",
    "ranking_llm_invoked",
    "intake_handoff_created",
    "mutation_changed",
    "meal_thread_mutated",
    "day_budget_mutated",
    "body_plan_mutated",
    "durable_memory_written",
    "manager_context_packet_changed",
    "manager_context_injected",
)
FALSE_PACKET_FLAGS = {
    "runtime_effect_allowed": False,
    "intake_handoff_created": False,
    "recommendation_served": False,
    "meal_thread_mutated": False,
    "ledger_entry_created": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "durable_memory_written": False,
    "manager_context_packet_changed": False,
    "manager_context_injected": False,
    "proactive_sent": False,
    "mutation_changed": False,
}


def build_recommendation_intake_hint_shadow_packet(
    *,
    recommendation_quality_report: Mapping[str, Any],
    selected_candidate_id: str,
    current_surface_channel: str = "shadow_review",
) -> dict[str, Any]:
    blockers = _report_blockers(recommendation_quality_report)
    evaluation = _candidate_evaluation(recommendation_quality_report, selected_candidate_id)
    blockers.extend(_selected_candidate_blockers(recommendation_quality_report, evaluation))
    hint_packet = (
        None
        if blockers
        else _hint_packet(
            candidate=evaluation,
            current_surface_channel=current_surface_channel,
        )
    )
    return {
        "artifact_type": "recommendation_intake_hint_shadow_packet",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/recommendation",
        "consumer": "future_intake_flow_shadow_review",
        "retirement_trigger": "approved_recommendation_intake_handoff_runtime_contract",
        "selected_candidate_id": selected_candidate_id,
        "hint_packet": hint_packet,
        "blockers": blockers,
        "non_claims": [
            "not_intake_commit_request",
            "not_meal_thread_mutation",
            "not_recommendation_serving",
            "not_runtime_activation",
        ],
        **dict(FALSE_PACKET_FLAGS),
    }


def _report_blockers(report: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if report.get("artifact_type") != REPORT_ARTIFACT:
        blockers.append("recommendation_quality_report.unsupported_artifact_type")
    if report.get("status") != "pass":
        blockers.append("recommendation_quality_report.status_not_pass")
    if report.get("pool_decision") not in HANDOFF_POOL_DECISIONS:
        blockers.append("recommendation_quality_report.pool_not_handoff_eligible")
    for flag in FALSE_REPORT_FLAGS:
        if report.get(flag) is True:
            blockers.append(f"recommendation_quality_report.{flag}")
    return blockers


def _selected_candidate_blockers(
    report: Mapping[str, Any],
    evaluation: Mapping[str, Any] | None,
) -> list[str]:
    if evaluation is None:
        return ["selected_candidate.not_found"]
    blockers: list[str] = []
    if evaluation.get("quality_gate_passed") is not True:
        blockers.append("selected_candidate.quality_gate_not_passed")
    if evaluation.get("presentation_posture") == "silent":
        blockers.append("selected_candidate.not_handoff_eligible")
    if "negative_preference_blocker" in list(evaluation.get("memory_rejection_reasons") or []):
        blockers.append("selected_candidate.negative_preference_blocker")
    if not _selected_by_pool(report, str(evaluation.get("candidate_id") or "")):
        blockers.append("selected_candidate.not_selected_by_pool")
    return blockers


def _candidate_evaluation(
    report: Mapping[str, Any],
    selected_candidate_id: str,
) -> Mapping[str, Any] | None:
    for item in report.get("candidate_evaluations") or []:
        if isinstance(item, Mapping) and item.get("candidate_id") == selected_candidate_id:
            return item
    return None


def _selected_by_pool(report: Mapping[str, Any], candidate_id: str) -> bool:
    if not candidate_id:
        return False
    if report.get("primary_candidate_id") == candidate_id:
        return True
    return candidate_id in set(report.get("offer_candidate_ids") or [])


def _hint_packet(
    *,
    candidate: Mapping[str, Any],
    current_surface_channel: str,
) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "title": str(candidate.get("title") or ""),
        "store_metadata": _store_metadata(candidate),
        "estimated_kcal_hint": _int_or_none(candidate.get("estimated_kcal")),
        "current_surface_channel": current_surface_channel,
        "source_refs": _safe_source_refs(candidate),
    }


def _store_metadata(candidate: Mapping[str, Any]) -> dict[str, str]:
    metadata = {}
    if candidate.get("store_name"):
        metadata["store_name"] = str(candidate["store_name"])
    source = candidate.get("store_metadata")
    if isinstance(source, Mapping):
        for key in ("chain", "location_label"):
            if source.get(key):
                metadata[key] = str(source[key])
    return metadata


def _safe_source_refs(candidate: Mapping[str, Any]) -> list[str]:
    return [
        str(ref)
        for ref in candidate.get("source_refs") or []
        if str(ref).startswith("memory_candidate:")
    ]


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_recommendation_intake_hint_shadow_packet",
]
