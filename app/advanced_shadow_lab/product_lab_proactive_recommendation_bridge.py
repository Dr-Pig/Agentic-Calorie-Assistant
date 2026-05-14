from __future__ import annotations

from typing import Any, Mapping


def build_recommendation_proactive_candidate_bridge(
    *,
    recommendation_artifact: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        recommendation_artifact.get("recommendation_served_to_lab") is not True
        or recommendation_artifact.get("proactive_recommendation_candidate_allowed")
        is not True
    ):
        return _artifact(status="omitted", reason="recommendation_not_eligible_for_proactive")
    primary = _mapping(
        _mapping(recommendation_artifact.get("offer_synthesis")).get("selected_primary")
    )
    candidate_id = str(primary.get("candidate_id") or "")
    blockers = [] if candidate_id else ["recommendation.selected_primary_missing"]
    blockers.extend(_quality_blockers(primary))
    source_trace = _source_bridge_trace(primary, recommendation_artifact)
    return _artifact(
        status="blocked" if blockers else "pass",
        blockers=blockers,
        source_selected_candidate_id=candidate_id,
        candidate_spec={
            "trigger_type": "recommendation_prompt",
            "candidate_kind": "next_meal_recommendation",
            "source_output_refs": [
                str(recommendation_artifact.get("artifact_type") or ""),
                f"candidate:{candidate_id}",
            ],
            "source_status": str(recommendation_artifact.get("status") or ""),
            "downstream_workflow_family": "recommendation",
            "candidate_quality_tier": source_trace["candidate_quality_tier"],
            "proactive_intensity": source_trace["proactive_intensity"],
            "source_bridge_trace": source_trace,
            "control_model": dict(_control_model(fixture_inputs)),
            "next_signal_fallback": "new_app_open_with_qualified_pool",
        }
        if not blockers
        else None,
    )


def _artifact(
    *,
    status: str,
    reason: str = "",
    blockers: list[str] | None = None,
    source_selected_candidate_id: str = "",
    candidate_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_proactive_candidate_bridge",
        "status": status,
        "reason": reason,
        "reads_recommendation_outputs": status in {"pass", "blocked"},
        "candidate_created": status == "pass",
        "source_selected_candidate_id": source_selected_candidate_id,
        "candidate_spec": candidate_spec,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "served_to_mainline_user": False,
        "canonical_product_mutation_allowed": False,
        "blockers": blockers or [],
    }


def _quality_blockers(primary: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    quality_tier = str(primary.get("quality_tier") or "")
    source_type = str(primary.get("source_type") or "")
    proactive_intensity = str(primary.get("proactive_intensity") or "")
    if quality_tier in {"low", "rejected"} or proactive_intensity in {"none", "skip"}:
        blockers.append("recommendation.low_quality_context")
    if source_type in {"generic_category", "generic_only"}:
        blockers.append("recommendation.generic_category_only")
    return blockers


def _source_bridge_trace(
    primary: Mapping[str, Any],
    recommendation_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = str(primary.get("candidate_id") or "")
    return {
        "downstream_workflow_family": "recommendation",
        "source_selected_candidate_id": candidate_id,
        "candidate_quality_tier": str(primary.get("quality_tier") or ""),
        "proactive_intensity": str(primary.get("proactive_intensity") or ""),
        "source_type": str(primary.get("source_type") or ""),
        "quality_score": primary.get("quality_score"),
        "quality_signals": _quality_signals(
            primary=primary,
            recommendation_artifact=recommendation_artifact,
            candidate_id=candidate_id,
        ),
        "source_refs": [str(item) for item in primary.get("source_refs") or []],
        "recommendation_handoff_mode": "chat_first_invitation",
    }


def _quality_signals(
    *,
    primary: Mapping[str, Any],
    recommendation_artifact: Mapping[str, Any],
    candidate_id: str,
) -> list[str]:
    primary_signals = [str(item) for item in primary.get("quality_signals") or []]
    if primary_signals:
        return primary_signals
    retrieval = _mapping(recommendation_artifact.get("retrieval_guard_scoring"))
    for candidate in retrieval.get("allowed_candidates") or []:
        item = _mapping(candidate)
        if str(item.get("candidate_id") or "") == candidate_id:
            return [str(signal) for signal in item.get("quality_signals") or []]
    return []


def _control_model(fixture_inputs: Mapping[str, Any]) -> Mapping[str, Any]:
    models = _mapping(fixture_inputs.get("user_control_models"))
    model = _mapping(models.get("recommendation_prompt"))
    return {
        "dismiss_reason_choices": [
            str(item) for item in model.get("dismiss_reason_choices") or []
        ],
        "snooze_window": dict(_mapping(model.get("snooze_window"))),
        "next_signal_required": str(model.get("next_signal_required") or ""),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_recommendation_proactive_candidate_bridge"]
