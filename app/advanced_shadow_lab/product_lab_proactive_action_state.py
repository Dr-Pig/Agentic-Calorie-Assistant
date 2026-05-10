from __future__ import annotations

from typing import Any, Mapping


def pending_intake_followup_candidate(
    *,
    action_state: Mapping[str, Any],
    control_model: Mapping[str, Any],
) -> dict[str, Any] | None:
    draft_ids = [str(item) for item in action_state.get("active_pending_intake_draft_ids") or []]
    if not draft_ids:
        return None
    return {
        "trigger_type": "pending_intake_followup",
        "candidate_kind": "pending_intake_confirmation_followup",
        "source_output_refs": [
            "advanced_product_lab_action_state",
            *[f"pending_intake_draft:{draft_id}" for draft_id in draft_ids],
        ],
        "source_status": "pass",
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
        *[str(item) for item in action_state.get("dismissed_rescue_source_refs") or []],
        *[str(item) for item in action_state.get("rescue_commit_source_refs") or []],
    ]
    return [item for item in refs if item]


__all__ = [
    "action_state_source_refs",
    "pending_intake_followup_candidate",
    "rescue_omission_trace",
]
