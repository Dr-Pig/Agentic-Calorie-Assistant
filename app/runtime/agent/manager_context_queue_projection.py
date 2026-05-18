from __future__ import annotations

from typing import Any


def compact_queue_state_for_prompt(value: Any) -> dict[str, Any]:
    """Expose turn ordering without letting future queued text steer this turn."""

    state = _state(value)
    queued_inputs = _queued_inputs(state)
    return {
        "processing_turn_id": state.get("processing_turn_id"),
        "sequence_number": _int_or_zero(state.get("sequence_number")),
        "priority": _priority(state.get("priority")),
        "queued_input_count": len(queued_inputs),
        "queued_inputs_omitted_from_prompt": True,
        "context_role": state.get("context_role") or "turn_ordering_only",
        "semantic_owner": state.get("semantic_owner") or "manager_llm",
        "read_only": True,
        "mutation_authority": False,
    }


def compact_queue_state_for_trace(value: Any) -> dict[str, Any]:
    state = _state(value)
    queued_inputs = _queued_inputs(state)
    return {
        "processing_turn_id": state.get("processing_turn_id"),
        "sequence_number": _int_or_zero(state.get("sequence_number")),
        "priority": _priority(state.get("priority")),
        "queued_input_count": len(queued_inputs),
        "queued_inputs": [
            {
                "sequence_number": item.get("sequence_number"),
                "priority": _priority(item.get("priority")),
                "text_present": bool(str(item.get("text") or "").strip()),
            }
            for item in queued_inputs
        ],
        "context_role": state.get("context_role") or "turn_ordering_only",
        "semantic_owner": state.get("semantic_owner") or "manager_llm",
        "read_only": True,
        "mutation_authority": False,
    }


def _state(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _queued_inputs(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in state.get("queued_inputs") or [] if isinstance(item, dict)]


def _priority(value: Any) -> str:
    priority = str(value or "next").strip()
    return priority if priority in {"now", "next", "later"} else "next"


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


__all__ = [
    "compact_queue_state_for_prompt",
    "compact_queue_state_for_trace",
]
