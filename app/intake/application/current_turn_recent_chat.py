from __future__ import annotations

from typing import Any

from .manager_context_recent_chat_window import build_recent_chat_window

_RECENT_CHAT_MAX_MESSAGES = 20
_RECENT_CHAT_MAX_CHARS = 6000
_RECENT_CHAT_MAX_TOKENS = 2000


def recent_chat_turns_state(
    recent_chat_turns: Any,
    *,
    pending_followup: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    if recent_chat_turns is None:
        return [], "unknown", {}
    turns: list[dict[str, Any]] = []
    for raw_turn in list(recent_chat_turns or []):
        if not isinstance(raw_turn, dict):
            continue
        turn = {
            "message_id": raw_turn.get("message_id"),
            "role": str(raw_turn.get("role") or ""),
            "content": str(raw_turn.get("content") or ""),
            "created_at": raw_turn.get("created_at"),
            "trace_id": raw_turn.get("trace_id"),
            "linked_meal_log_id": raw_turn.get("linked_meal_log_id"),
            "local_date": raw_turn.get("local_date"),
            "read_only": True,
            "mutation_authority": False,
            "source": str(raw_turn.get("source") or "sqlite_message_buffer"),
        }
        followup_question = str(raw_turn.get("structured_followup_question") or "").strip()
        if followup_question:
            turn["structured_followup_question"] = followup_question
        turns.append(turn)
    bounded, artifact = build_recent_chat_window(
        turns,
        max_recent_messages=_RECENT_CHAT_MAX_MESSAGES,
        max_recent_chars=_RECENT_CHAT_MAX_CHARS,
        max_recent_tokens=_RECENT_CHAT_MAX_TOKENS,
        pending_followup=pending_followup,
    )
    return bounded, ("present" if bounded else "none"), artifact


__all__ = ["recent_chat_turns_state"]
