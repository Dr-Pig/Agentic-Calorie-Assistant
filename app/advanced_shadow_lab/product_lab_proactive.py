from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_proactive_delivery import (
    build_product_lab_proactive_delivery_packet,
)
from app.advanced_shadow_lab.product_lab_proactive_action_state import (
    action_state_source_refs,
    pending_intake_followup_candidate,
    rescue_omission_trace,
)


def run_product_lab_proactive(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
    recommendation_artifact: Mapping[str, Any],
    rescue_artifact: Mapping[str, Any],
    action_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current_action_state = action_state or {}
    rescue_omission = rescue_omission_trace(current_action_state)
    specs = [
        _recommendation_candidate(recommendation_artifact, fixture_inputs),
        pending_intake_followup_candidate(
            action_state=current_action_state,
            control_model=_control_model(fixture_inputs, "pending_intake_followup"),
        ),
    ]
    if rescue_omission is None:
        specs.append(_rescue_candidate(rescue_artifact, fixture_inputs))
    candidates = [
        _candidate(
            trigger_type=str(spec.get("trigger_type") or ""),
            candidate_kind=str(spec.get("candidate_kind") or ""),
            source_output_refs=[str(item) for item in spec.get("source_output_refs") or []],
            source_status=str(spec.get("source_status") or ""),
            control_model=_mapping(spec.get("control_model")),
            next_signal_fallback=str(spec.get("next_signal_fallback") or ""),
        )
        for spec in specs
        if spec is not None
    ]
    blockers = [
        blocker
        for candidate in candidates
        for blocker in _candidate_blockers(candidate)
    ]
    passed = [] if blockers else candidates
    delivery = build_product_lab_proactive_delivery_packet(
        candidates=passed,
        blocked=bool(blockers),
    )
    return {
        "artifact_type": "advanced_product_lab_proactive_runtime_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "session_id": str(turn.get("session_id") or ""),
        "turn_id": str(turn.get("turn_id") or ""),
        "chat_first": True,
        "candidate_count": len(passed),
        "candidates": passed,
        "delivery_packet": delivery,
        "memory_context_refs": [
            str(item) for item in memory_context_pack.get("selected_record_ids") or []
        ],
        "action_state_refs": action_state_source_refs(current_action_state),
        "omission_traces": [] if rescue_omission is None else [rescue_omission],
        "source_outputs_read": [
            str(recommendation_artifact.get("artifact_type") or ""),
            str(rescue_artifact.get("artifact_type") or ""),
            str(current_action_state.get("artifact_type") or ""),
        ],
        "lab_chat_delivery_allowed": not bool(blockers),
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "push_or_line_delivery_connected": False,
        "served_to_mainline_user": False,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
    }


def _recommendation_candidate(
    recommendation: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    primary = _mapping(_mapping(recommendation.get("offer_synthesis")).get("selected_primary"))
    return {
        "trigger_type": "recommendation_prompt",
        "candidate_kind": "next_meal_recommendation",
        "source_output_refs": [
            str(recommendation.get("artifact_type") or ""),
            f"candidate:{primary.get('candidate_id') or ''}",
        ],
        "source_status": str(recommendation.get("status") or ""),
        "control_model": _control_model(fixture_inputs, "recommendation_prompt"),
        "next_signal_fallback": "new_app_open_with_qualified_pool",
    }


def _rescue_candidate(
    rescue: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    card = _mapping(rescue.get("proposal_card"))
    return {
        "trigger_type": "rescue_nudge",
        "candidate_kind": "same_day_rescue_proposal",
        "source_output_refs": [
            str(rescue.get("artifact_type") or ""),
            f"proposal:{card.get('card_kind') or ''}",
        ],
        "source_status": str(rescue.get("status") or ""),
        "control_model": _control_model(fixture_inputs, "rescue_nudge"),
        "next_signal_fallback": "material_budget_change_or_user_reopens_rescue",
    }


def _candidate(
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


def _candidate_blockers(candidate: Mapping[str, Any]) -> list[str]:
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


def _control_model(
    fixture_inputs: Mapping[str, Any],
    trigger_type: str,
) -> Mapping[str, Any]:
    models = _mapping(fixture_inputs.get("user_control_models"))
    return _mapping(models.get(trigger_type))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["run_product_lab_proactive"]
