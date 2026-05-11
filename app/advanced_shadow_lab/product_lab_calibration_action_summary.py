from __future__ import annotations

from typing import Any, Mapping


def turn_calibration_action_summary(
    action_outcomes: list[Mapping[str, Any]],
) -> dict[str, Any]:
    decisions = _decision_packets(action_outcomes)
    latest = _latest_daily_budget(decisions)
    return {
        "lab_calibration_action_decision_count": len(decisions),
        "lab_calibration_action_decision_kinds": [
            str(item.get("decision_kind") or "") for item in decisions
        ],
        "lab_calibration_effect_applied_count": sum(
            1 for item in decisions if item.get("lab_calibration_effect_applied") is True
        ),
        "lab_calibration_dismissed_count": sum(
            1 for item in decisions if item.get("proposal_instance_dismissed") is True
        ),
        "lab_calibration_action_source_refs": [
            str(ref) for item in decisions for ref in item.get("source_refs") or []
        ],
        "lab_calibration_latest_daily_budget_kcal": latest,
        "lab_calibration_action_canonical_mutation_allowed": any(
            item.get("canonical_product_mutation_allowed") is True
            for item in decisions
        ),
    }


def session_calibration_action_summary(
    turn_summaries: list[Mapping[str, Any]],
) -> dict[str, Any]:
    latest_values = [
        int(item.get("lab_calibration_latest_daily_budget_kcal") or 0)
        for item in turn_summaries
        if int(item.get("lab_calibration_latest_daily_budget_kcal") or 0) > 0
    ]
    return {
        "lab_calibration_action_decision_count": sum(
            int(item.get("lab_calibration_action_decision_count") or 0)
            for item in turn_summaries
        ),
        "lab_calibration_action_decision_kinds": [
            str(kind)
            for item in turn_summaries
            for kind in item.get("lab_calibration_action_decision_kinds") or []
        ],
        "lab_calibration_effect_applied_count": sum(
            int(item.get("lab_calibration_effect_applied_count") or 0)
            for item in turn_summaries
        ),
        "lab_calibration_dismissed_count": sum(
            int(item.get("lab_calibration_dismissed_count") or 0)
            for item in turn_summaries
        ),
        "lab_calibration_latest_daily_budget_kcal": latest_values[-1]
        if latest_values
        else 0,
        "lab_calibration_action_canonical_mutation_allowed": any(
            item.get("lab_calibration_action_canonical_mutation_allowed") is True
            for item in turn_summaries
        ),
    }


def _decision_packets(items: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    packets: list[Mapping[str, Any]] = []
    for item in items:
        packet = _mapping(item.get("calibration_action_decision_packet"))
        if packet.get("status") == "pass":
            packets.append(packet)
    return packets


def _latest_daily_budget(decisions: list[Mapping[str, Any]]) -> int:
    if not decisions:
        return 0
    plan = _mapping(decisions[-1].get("lab_body_plan_after"))
    return int(plan.get("daily_budget_kcal") or 0)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "session_calibration_action_summary",
    "turn_calibration_action_summary",
]
