from __future__ import annotations

from typing import Any, Mapping

def product_lab_proactive_candidate(
    *,
    trigger_type: str,
    candidate_kind: str,
    source_output_refs: list[str],
    source_status: str,
    control_model: Mapping[str, Any],
    next_signal_fallback: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_proactive_candidate",
        "status": "pass" if source_status == "pass" else "blocked",
        "candidate_id": product_lab_proactive_candidate_id(trigger_type),
        "trigger_type": trigger_type,
        "candidate_kind": candidate_kind,
        "surface": "chat",
        "source_output_refs": source_output_refs,
        "dismiss_reason_choices": [
            str(item) for item in control_model.get("dismiss_reason_choices") or []
        ],
        "snooze_window": dict(_mapping(control_model.get("snooze_window"))),
        "undo_scope": "candidate_instance",
        "next_signal_required": str(
            control_model.get("next_signal_required") or next_signal_fallback
        ),
        "served_to_lab_chat": source_status == "pass",
        "served_to_mainline_user": False,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
    }


def product_lab_proactive_candidate_blockers(
    candidate: Mapping[str, Any],
) -> list[str]:
    trigger = str(candidate.get("trigger_type") or "unknown")
    blockers: list[str] = []
    if candidate.get("status") != "pass":
        blockers.append(f"{trigger}.source_status_not_pass")
    if not candidate.get("dismiss_reason_choices"):
        blockers.append(f"{trigger}.dismiss_reason_choices_missing")
    snooze = _mapping(candidate.get("snooze_window"))
    if not isinstance(snooze.get("minutes"), int) or snooze.get("minutes", 0) <= 0:
        blockers.append(f"{trigger}.snooze_window_missing")
    if not str(candidate.get("next_signal_required") or ""):
        blockers.append(f"{trigger}.next_signal_required_missing")
    return blockers


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def product_lab_proactive_candidate_id(trigger_type: str) -> str:
    return {
        "recommendation_prompt": "recommendation_prompt:0",
        "rescue_nudge": "rescue_nudge:1",
        "weekly_insight": "weekly_insight:2",
        "pending_intake_followup": "pending_intake_followup:3",
    }.get(trigger_type, f"{trigger_type}:0")


__all__ = [
    "product_lab_proactive_candidate",
    "product_lab_proactive_candidate_blockers",
]
