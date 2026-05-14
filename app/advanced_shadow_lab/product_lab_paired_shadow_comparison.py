from __future__ import annotations

from typing import Any, Mapping


COMPARISON_PATHS = [
    "baseline_product_outputs",
    "candidate_only_pre_delivery",
    "lab_chat_delivery",
]


def build_product_lab_paired_shadow_comparison(
    turn_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_ids = _candidate_ids(turn_artifact)
    delivery_ids = _delivery_ids(turn_artifact)
    omitted = _omitted_trigger_types(turn_artifact)
    blockers = [
        *_turn_blockers(turn_artifact),
        *_alignment_blockers(candidate_ids, delivery_ids),
    ]
    return {
        "artifact_type": "advanced_product_lab_paired_shadow_comparison",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "comparison_paths": list(COMPARISON_PATHS),
        "baseline_product_outputs": _baseline_product_outputs(turn_artifact),
        "candidate_only_ids": candidate_ids,
        "lab_chat_delivery_ids": delivery_ids,
        "omitted_trigger_types": omitted,
        "shadow_comparison_passed": not blockers,
        "mainline_activation_enabled": False,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "blockers": blockers,
    }


def _baseline_product_outputs(turn_artifact: Mapping[str, Any]) -> dict[str, Any]:
    recommendation = _mapping(turn_artifact.get("product_lab_recommendation_artifact"))
    rescue = _mapping(turn_artifact.get("product_lab_rescue_artifact"))
    return {
        "recommendation_present": recommendation.get("status") == "pass",
        "rescue_present": rescue.get("proposal_presented_to_lab") is True,
        "canonical_product_mutation_allowed": (
            recommendation.get("canonical_product_mutation_allowed") is True
            or rescue.get("canonical_product_mutation_allowed") is True
        ),
    }


def _candidate_ids(turn_artifact: Mapping[str, Any]) -> list[str]:
    proactive = _mapping(turn_artifact.get("product_lab_proactive_artifact"))
    return [
        str(candidate.get("candidate_id") or "")
        for candidate in proactive.get("candidates") or []
        if isinstance(candidate, Mapping)
    ]


def _delivery_ids(turn_artifact: Mapping[str, Any]) -> list[str]:
    surface = _mapping(turn_artifact.get("lab_chat_surface"))
    return [
        str(message.get("candidate_id") or "")
        for message in surface.get("messages") or []
        if isinstance(message, Mapping)
    ]


def _omitted_trigger_types(turn_artifact: Mapping[str, Any]) -> list[str]:
    proactive = _mapping(turn_artifact.get("product_lab_proactive_artifact"))
    return [
        str(trace.get("trigger_type") or "")
        for trace in proactive.get("omission_traces") or []
        if isinstance(trace, Mapping)
    ]


def _turn_blockers(turn_artifact: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if turn_artifact.get("status") != "pass":
        blockers.append(f"turn.status_{turn_artifact.get('status') or 'missing'}")
    for key in (
        "mainline_activation_enabled",
        "scheduler_delivery_allowed",
        "notification_delivery_allowed",
        "canonical_product_mutation_allowed",
    ):
        if turn_artifact.get(key) is True:
            blockers.append(f"turn.{key}")
    return blockers


def _alignment_blockers(candidate_ids: list[str], delivery_ids: list[str]) -> list[str]:
    if candidate_ids == delivery_ids:
        return []
    return [f"candidate_delivery_mismatch:{candidate_ids}!={delivery_ids}"]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_product_lab_paired_shadow_comparison"]
