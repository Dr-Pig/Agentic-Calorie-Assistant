from __future__ import annotations

from typing import Any, Mapping


def pending_intake_followup_candidate(
    *,
    action_state: Mapping[str, Any],
    control_model: Mapping[str, Any],
) -> dict[str, Any] | None:
    draft_ids = [str(item) for item in action_state.get("active_pending_intake_draft_ids") or []]
    meal_intents = _active_pending_meal_intents(action_state)
    intent_ids = [str(item.get("intent_id") or "") for item in meal_intents]
    if not draft_ids and not intent_ids:
        return None
    return {
        "trigger_type": "pending_intake_followup",
        "candidate_kind": "pending_intake_confirmation_followup",
        "source_output_refs": [
            "advanced_product_lab_action_state",
            *[f"pending_intake_draft:{draft_id}" for draft_id in draft_ids],
            *_pending_meal_intent_refs(action_state, meal_intents),
        ],
        "source_status": "pass",
        "source_bridge_trace": _pending_intake_bridge_trace(
            draft_ids=draft_ids,
            meal_intents=meal_intents,
        ),
        "control_model": control_model,
        "next_signal_fallback": "user_confirms_or_cancels_pending_intake",
    }


def rescue_omission_trace(action_state: Mapping[str, Any]) -> dict[str, Any] | None:
    if int(action_state.get("dismissed_rescue_instance_count") or 0) <= 0:
        return None
    return {
        "trigger_type": "rescue_nudge",
        "omission_reason": "dismissed_rescue_instance_active",
        "source_refs": [
            str(item) for item in action_state.get("dismissed_rescue_source_refs") or []
        ],
        "user_facing_behavior_changed": False,
        "scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
    }


def action_state_source_refs(action_state: Mapping[str, Any]) -> list[str]:
    refs = [
        *[str(item) for item in action_state.get("active_pending_intake_source_refs") or []],
        *[str(item) for item in action_state.get("active_pending_meal_intent_source_refs") or []],
        *[str(item) for item in action_state.get("dismissed_rescue_source_refs") or []],
        *[str(item) for item in action_state.get("rescue_commit_source_refs") or []],
    ]
    return [item for item in refs if item]


def _active_pending_meal_intents(
    action_state: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    return [
        item
        for item in action_state.get("active_pending_meal_intents") or []
        if isinstance(item, Mapping)
        and item.get("status") == "created"
        and item.get("canonical_write_authorized") is not True
    ]


def _pending_meal_intent_refs(
    action_state: Mapping[str, Any],
    meal_intents: list[Mapping[str, Any]],
) -> list[str]:
    explicit_refs = [
        str(item) for item in action_state.get("active_pending_meal_intent_source_refs") or []
    ]
    if explicit_refs:
        return explicit_refs
    return [f"pending_meal_intent:{item.get('intent_id') or ''}" for item in meal_intents]


def _pending_intake_bridge_trace(
    *,
    draft_ids: list[str],
    meal_intents: list[Mapping[str, Any]],
) -> dict[str, Any]:
    postures = [_mapping(item.get("meal_window_posture")) for item in meal_intents]
    return {
        "downstream_workflow_family": "pending_meal_intent",
        "active_pending_intake_draft_ids": list(draft_ids),
        "active_pending_meal_intent_ids": [
            str(item.get("intent_id") or "") for item in meal_intents
        ],
        "target_windows": [str(item.get("target_window") or "") for item in postures],
        "followup_timing": [str(item.get("followup_timing") or "") for item in postures],
        "quiet_hours_policy": [
            str(item.get("quiet_hours_policy") or "") for item in postures
        ],
        "canonical_write_authorized": False,
        "meal_thread_mutated": False,
        "ledger_entry_created": False,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "action_state_source_refs",
    "pending_intake_followup_candidate",
    "rescue_omission_trace",
]
