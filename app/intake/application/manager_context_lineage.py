from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

CONTEXT_LINEAGE_VERSION = "manager_context_lineage_v1"
CONTEXT_GENERATION_ID = "manager_context_packet_v1"


def attach_context_lineage(packet: dict[str, Any]) -> dict[str, Any]:
    """Attach traceable context state metadata without making semantic decisions."""

    packet["context_layers"] = context_layers_for_packet(packet)
    packet["context_lineage"] = context_lineage_for_packet(packet)
    return packet


def context_lineage_for_packet(packet: dict[str, Any]) -> dict[str, Any]:
    artifact = dict(packet.get("context_loading_artifact") or {})
    history_trimmed = bool(
        artifact.get("history_trimmed")
        or artifact.get("omitted_count")
        or artifact.get("char_truncated")
    )
    context_reinjected = bool(
        artifact.get("context_reinjected_after_compaction_or_history_trim")
        or (
            history_trimmed
            and artifact.get("canonical_state_reinjected_after_history_trim")
        )
    )
    reinject_reason = "history_trimmed_with_hard_pins" if context_reinjected else "none"
    return {
        "lineage_version": CONTEXT_LINEAGE_VERSION,
        "context_generation": CONTEXT_GENERATION_ID,
        "context_packet_hash": context_packet_hash(packet),
        "active_workflow_id": active_workflow_id_for_packet(packet),
        "history_trimmed": history_trimmed,
        "context_reinjected_after_compaction_or_history_trim": context_reinjected,
        "prior_context_generation": packet.get("context_lineage", {}).get("context_generation"),
        "reinject_reason": reinject_reason,
        "compacted_summary_ref": None,
        "source_role": "runtime_context_state_packet",
        "semantic_owner": "manager_llm",
        "read_only": True,
        "mutation_authority": False,
    }


def context_layers_for_packet(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    current_turn = dict(packet.get("current_turn") or {})
    hard_pins = dict(packet.get("hard_pins") or {})
    active_day_state = dict(packet.get("active_day_state") or {})
    target_candidates = dict(packet.get("target_candidates") or {})
    artifact = dict(packet.get("context_loading_artifact") or {})
    recent_chat_window = dict(packet.get("recent_chat_window") or {})
    metadata = dict(packet.get("metadata") or {})
    candidates = list(target_candidates.get("for_correction_or_removal") or [])
    return {
        "current_turn": _readonly_layer(
            {
                "user_id_present": bool(metadata.get("user_id")),
                "local_date": metadata.get("local_date"),
                "session_id_present": bool(metadata.get("session_id")),
                "channel": current_turn.get("channel"),
                "manager_mode": current_turn.get("manager_mode"),
                "raw_user_input_present": bool(current_turn.get("raw_user_input")),
                "interaction_event_present": current_turn.get("interaction_event") is not None,
            }
        ),
        "active_workflow": _readonly_layer(
            {
                "active_workflow_id": active_workflow_id_for_packet(packet),
                "pending_followup_present": _object_present(hard_pins.get("pending_followup")),
                "pending_draft_present": _object_present(hard_pins.get("pending_draft")),
                "last_assistant_question_present": bool(hard_pins.get("last_assistant_question")),
                "active_meal_thread_present": _object_present(
                    active_day_state.get("active_meal_thread_ref")
                )
                or _object_present(active_day_state.get("active_meal_estimate_basis")),
            }
        ),
        "evidence_state": _readonly_layer(
            {
                "recent_chat_message_count": len(list(recent_chat_window.get("messages") or [])),
                "recent_chat_messages_omitted": artifact.get("omitted_count"),
                "target_candidate_count": len(candidates),
                "budget_summary_present": _object_present(active_day_state.get("budget_summary")),
                "body_plan_summary_present": _object_present(active_day_state.get("body_plan_summary")),
                "active_meal_estimate_basis_present": _object_present(
                    active_day_state.get("active_meal_estimate_basis")
                ),
            }
        ),
    }


def context_packet_hash(packet: dict[str, Any]) -> str:
    payload = deepcopy(packet)
    payload.pop("context_lineage", None)
    payload.pop("context_layers", None)
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def active_workflow_id_for_packet(packet: dict[str, Any]) -> str | None:
    hard_pins = dict(packet.get("hard_pins") or {})
    pending_followup_id = _pending_followup_workflow_id(hard_pins.get("pending_followup"))
    if pending_followup_id:
        return pending_followup_id
    pending_draft_id = _pending_draft_workflow_id(hard_pins.get("pending_draft"))
    if pending_draft_id:
        return pending_draft_id
    active_day_state = dict(packet.get("active_day_state") or {})
    active_meal_id = _meal_thread_workflow_id(active_day_state.get("active_meal_thread_ref"))
    if active_meal_id:
        return active_meal_id
    active_meal_id = _meal_thread_workflow_id(active_day_state.get("active_meal_estimate_basis"))
    if active_meal_id:
        return active_meal_id
    return None


def _pending_followup_workflow_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("runtime_turn_id", "pending_followup_id", "followup_id"):
        item = _scalar_text(value.get(key))
        if item:
            return f"pending_followup:{item}"
    for key in ("meal_thread_id", "source_meal_id", "meal_id"):
        item = _scalar_text(value.get(key))
        if item:
            return f"pending_followup:meal_thread:{item}"
    return "pending_followup:open"


def _pending_draft_workflow_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("draft_id", "source_request_id"):
        item = _scalar_text(value.get(key))
        if item:
            return f"pending_draft:{item}"
    meal_thread_id = _scalar_text(value.get("meal_thread_id"))
    if meal_thread_id:
        return f"pending_draft:meal_thread:{meal_thread_id}"
    return "pending_draft:open"


def _meal_thread_workflow_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    meal_thread_id = _scalar_text(value.get("meal_thread_id"))
    if meal_thread_id:
        return f"meal_thread:{meal_thread_id}"
    target_id = _scalar_text(value.get("target_object_id"))
    if target_id:
        return f"meal_thread:{target_id}"
    return None


def _readonly_layer(values: dict[str, Any]) -> dict[str, Any]:
    return {
        **values,
        "semantic_owner": "manager_llm",
        "context_role": "candidate_state_only",
        "read_only": True,
        "mutation_authority": False,
    }


def _object_present(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def _scalar_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        default=str,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


__all__ = [
    "CONTEXT_GENERATION_ID",
    "CONTEXT_LINEAGE_VERSION",
    "active_workflow_id_for_packet",
    "attach_context_lineage",
    "context_layers_for_packet",
    "context_lineage_for_packet",
    "context_packet_hash",
]
