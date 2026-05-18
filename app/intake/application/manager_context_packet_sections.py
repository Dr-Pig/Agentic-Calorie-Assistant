from __future__ import annotations

from typing import Any

from app.runtime.contracts.phase_a import CurrentTurnContextV1


def candidate_context(
    current_turn_context: CurrentTurnContextV1,
    explicit_candidates: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if explicit_candidates is not None:
        return list(explicit_candidates)
    return [
        *list(current_turn_context.candidate_attachment_targets or []),
        *list(current_turn_context.recent_item_targets or []),
    ]


def queue_state(value: dict[str, Any] | None) -> dict[str, Any]:
    state = dict(value or {})
    queued_inputs = state.get("queued_inputs")
    if not isinstance(queued_inputs, list):
        queued_inputs = []
    normalized_inputs: list[dict[str, Any]] = []
    for item in queued_inputs:
        if not isinstance(item, dict):
            continue
        normalized_inputs.append(
            {
                "sequence_number": item.get("sequence_number"),
                "text": str(item.get("text") or item.get("raw_text") or ""),
                "priority": _queue_priority(item.get("priority")),
                "read_only": True,
                "mutation_authority": False,
            }
        )
    return {
        "processing_turn_id": state.get("processing_turn_id"),
        "queued_inputs": normalized_inputs,
        "sequence_number": int(state.get("sequence_number") or 0),
        "priority": _queue_priority(state.get("priority")),
        "read_only": True,
        "mutation_authority": False,
        "semantic_owner": "manager_llm",
        "context_role": "turn_ordering_only",
    }


def active_workflow_state(
    *,
    current_turn_context: CurrentTurnContextV1,
    pending_draft: dict[str, Any] | None,
) -> dict[str, Any]:
    pending_followup = _dict_or_none(current_turn_context.pending_followup)
    active_ref = _dict_or_empty(current_turn_context.active_meal_thread_ref)
    target_ref = _dict_or_empty(current_turn_context.target_resolution_posture)
    required_slots = _slot_list(pending_followup, "required_slots")
    optional_slots = _slot_list(pending_followup, "optional_slots")
    return {
        "active_workflow_id": _workflow_id(
            pending_followup=pending_followup,
            pending_draft=pending_draft,
            active_ref=active_ref,
            target_ref=target_ref,
        ),
        "workflow_type": current_turn_context.open_workflow_type,
        "meal_thread_id": _first_scalar(
            pending_followup,
            pending_draft,
            active_ref,
            target_ref,
            keys=("meal_thread_id", "meal_id", "target_object_id"),
        ),
        "active_version_id": _first_scalar(
            pending_followup,
            pending_draft,
            active_ref,
            target_ref,
            keys=("meal_version_id", "version_id"),
        ),
        "commit_status": _first_scalar(
            pending_followup,
            pending_draft,
            active_ref,
            keys=("commit_status", "resolution_status", "version_status"),
        )
        or "unknown",
        "pending_type": _pending_type(pending_followup),
        "required_slots": required_slots,
        "optional_slots": optional_slots,
        "known_facts": _known_facts(pending_followup, pending_draft, active_ref),
        "unresolved_facts": _unresolved_facts(required_slots=required_slots, optional_slots=optional_slots),
        "last_assistant_question": current_turn_context.last_system_question,
        "manager_must_decide": [
            "determine_current_turn_relation_to_active_workflow",
            "determine_whether_current_turn_answers_required_slots",
            "determine_whether_current_turn_answers_optional_slots",
            "determine_basis_inquiry_vs_correction_vs_new_log",
            "select_attach_target_or_ask_clarification",
        ],
        "selection_owner": "manager",
        "read_only": True,
        "mutation_authority": False,
    }


def _queue_priority(value: Any) -> str:
    priority = str(value or "next").strip()
    return priority if priority in {"now", "next", "later"} else "next"


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, dict) else None


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _workflow_id(
    *,
    pending_followup: dict[str, Any] | None,
    pending_draft: dict[str, Any] | None,
    active_ref: dict[str, Any],
    target_ref: dict[str, Any],
) -> str | None:
    for prefix, value in (
        ("pending_followup", pending_followup),
        ("pending_draft", pending_draft),
        ("meal_thread", active_ref),
        ("target", target_ref),
    ):
        if not isinstance(value, dict):
            continue
        for key in ("runtime_turn_id", "pending_followup_id", "draft_id", "meal_thread_id", "target_object_id"):
            item = value.get(key)
            if item not in (None, ""):
                return f"{prefix}:{item}"
    return None


def _pending_type(pending_followup: dict[str, Any] | None) -> str:
    if not isinstance(pending_followup, dict):
        return "none"
    pending_type = str(pending_followup.get("pending_type") or "").strip()
    return pending_type if pending_type in {"blocking_composition", "optional_refinement", "none"} else "manager_must_decide"


def _slot_list(source: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    if not isinstance(source, dict) or not isinstance(source.get(key), list):
        return []
    slots: list[dict[str, Any]] = []
    for value in source[key]:
        if not isinstance(value, dict):
            continue
        slots.append(
            {
                "slot_id": str(value.get("slot_id") or ""),
                "slot_kind": str(value.get("slot_kind") or ""),
                "required_for_commit": bool(value.get("required_for_commit")),
                "current_value": value.get("current_value"),
                "source": str(value.get("source") or ""),
                "resolution_condition": str(value.get("resolution_condition") or ""),
                "asked_question": str(value.get("asked_question") or ""),
                "read_only": True,
                "mutation_authority": False,
            }
        )
    return slots


def _known_facts(*values: dict[str, Any] | None) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for value in values:
        if not isinstance(value, dict):
            continue
        for key in ("meal_title", "canonical_name", "pending_question", "expected_answer_type", "resolution_status"):
            if value.get(key) not in (None, ""):
                facts[key] = value[key]
    facts["read_only"] = True
    facts["mutation_authority"] = False
    return facts


def _unresolved_facts(*, required_slots: list[dict[str, Any]], optional_slots: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "required_slot_ids": [
            str(slot.get("slot_id") or "") for slot in required_slots if slot.get("current_value") in (None, "")
        ],
        "optional_slot_ids": [
            str(slot.get("slot_id") or "") for slot in optional_slots if slot.get("current_value") in (None, "")
        ],
        "read_only": True,
        "mutation_authority": False,
    }


def _first_scalar(*values: dict[str, Any] | None, keys: tuple[str, ...]) -> Any:
    for value in values:
        if not isinstance(value, dict):
            continue
        for key in keys:
            item = value.get(key)
            if item not in (None, ""):
                return item
    return None


__all__ = [
    "active_workflow_state",
    "candidate_context",
    "queue_state",
]
