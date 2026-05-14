from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_proactive_action_state import (
    pending_intake_followup_candidate,
)
from app.advanced_shadow_lab.product_lab_proactive_recommendation_bridge import (
    build_recommendation_proactive_candidate_bridge,
)

TRIGGER_METADATA = {
    "recommendation_prompt": ("recommendation", "app_open", "qualified_recommendation_offer_available"),
    "pending_intake_followup": ("pending_meal", "state_threshold", "pending_intake_needs_confirmation"),
    "rescue_nudge": ("rescue", "event_driven", "same_day_rescue_proposal_available"),
    "weekly_insight": ("memory", "scheduled_check", "weekly_behavior_summary_available"),
}


def build_product_lab_proactive_wake_sources(
    *,
    fixture_inputs: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
    recommendation_artifact: Mapping[str, Any],
    rescue_artifact: Mapping[str, Any],
    weekly_insight_artifact: Mapping[str, Any] | None = None,
    action_state: Mapping[str, Any] | None = None,
    rescue_omission_active: bool = False,
) -> dict[str, Any]:
    current_action_state = action_state or {}
    recommendation_bridge = build_recommendation_proactive_candidate_bridge(
        recommendation_artifact=recommendation_artifact,
        fixture_inputs=fixture_inputs,
    )
    specs = [
        recommendation_bridge.get("candidate_spec"),
        pending_intake_followup_candidate(
            action_state=current_action_state,
            control_model=_control_model(fixture_inputs, "pending_intake_followup"),
        ),
    ]
    if not rescue_omission_active:
        specs.append(_rescue_candidate(rescue_artifact, fixture_inputs))
    specs.append(_weekly_insight_candidate(weekly_insight_artifact or {}, fixture_inputs))
    raw_candidate_specs = [dict(spec) for spec in specs if isinstance(spec, Mapping)]
    candidate_specs = [_spec_with_wake_trace(spec) for spec in raw_candidate_specs]
    wake_sources = [
        *_memory_context_sources(memory_context_pack),
        *[_candidate_wake_source(spec) for spec in candidate_specs],
    ]
    blockers = [
        f"recommendation_bridge.{blocker}"
        for blocker in recommendation_bridge.get("blockers") or []
        if recommendation_bridge.get("status") == "blocked"
    ]
    return {
        "artifact_type": "advanced_product_lab_proactive_wake_source_adapter_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "wake_source_count": len(wake_sources),
        "wake_sources": wake_sources,
        "candidate_specs": candidate_specs,
        "candidate_spec_trigger_types": [
            str(spec.get("trigger_type") or "") for spec in candidate_specs
        ],
        "context_only_source_families": [
            str(source.get("source_family") or "")
            for source in wake_sources
            if source.get("candidate_spec") is None
        ],
        "recommendation_proactive_candidate_bridge": recommendation_bridge,
        "wake_source_is_not_user_benefit": True,
        "raw_user_text_semantic_inference_performed": False,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "served_to_mainline_user": False,
        "canonical_product_mutation_allowed": False,
        "blockers": blockers,
    }


def _candidate_wake_source(spec: Mapping[str, Any]) -> dict[str, Any]:
    trigger = str(spec.get("trigger_type") or "")
    source_family, wake_source, reason = TRIGGER_METADATA.get(
        trigger, ("unknown", "unknown", "")
    )
    return {
        "source_family": source_family,
        "trigger_type": trigger,
        "wake_source": wake_source,
        "user_relevant_reason": reason,
        "source_output_refs": [str(item) for item in spec.get("source_output_refs") or []],
        "source_status": str(spec.get("source_status") or ""),
        "candidate_spec": dict(spec),
        "wake_source_is_user_benefit": False,
    }


def _spec_with_wake_trace(spec: Mapping[str, Any]) -> dict[str, Any]:
    trace = _candidate_wake_source(spec)
    return {
        **dict(spec),
        "wake_source_trace": {
            key: value
            for key, value in trace.items()
            if key != "candidate_spec"
        },
    }


def _memory_context_sources(memory_context_pack: Mapping[str, Any]) -> list[dict[str, Any]]:
    selected_ids = [str(item) for item in memory_context_pack.get("selected_record_ids") or []]
    if not selected_ids:
        return []
    return [
        {
            "source_family": "memory",
            "trigger_type": "memory_context_signal",
            "wake_source": "context_available",
            "user_relevant_reason": "",
            "source_output_refs": [
                str(memory_context_pack.get("artifact_type") or ""),
                *[f"memory_record:{record_id}" for record_id in selected_ids],
            ],
            "source_status": str(memory_context_pack.get("status") or ""),
            "candidate_spec": None,
            "wake_source_is_user_benefit": False,
        }
    ]


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


def _weekly_insight_candidate(
    weekly_insight: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any] | None:
    if (
        weekly_insight.get("status") != "pass"
        or weekly_insight.get("weekly_insight_chat_candidate_allowed") is not True
    ):
        return None
    report = _mapping(weekly_insight.get("weekly_insight_report"))
    return {
        "trigger_type": "weekly_insight",
        "candidate_kind": "weekly_behavior_insight_report",
        "source_output_refs": [
            str(weekly_insight.get("artifact_type") or ""),
            f"weekly_report:{report.get('report_id') or ''}",
        ],
        "source_status": str(weekly_insight.get("status") or ""),
        "control_model": _control_model(fixture_inputs, "weekly_insight"),
        "next_signal_fallback": "new_weekly_insight_window",
    }


def _control_model(
    fixture_inputs: Mapping[str, Any],
    trigger_type: str,
) -> Mapping[str, Any]:
    models = _mapping(fixture_inputs.get("user_control_models"))
    model = _mapping(models.get(trigger_type))
    return {
        "dismiss_reason_choices": [
            str(item) for item in model.get("dismiss_reason_choices") or []
        ],
        "snooze_window": dict(_mapping(model.get("snooze_window"))),
        "next_signal_required": str(model.get("next_signal_required") or ""),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_product_lab_proactive_wake_sources"]
