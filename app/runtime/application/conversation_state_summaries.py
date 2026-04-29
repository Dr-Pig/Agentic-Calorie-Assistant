from __future__ import annotations

from typing import Any, Callable

from ...shared.domain import (
    ActiveMealSummary,
    ConversationArchiveRecord,
    ConversationMessage,
    PendingFollowupState,
    RecentTurnSummary,
    SessionSummary,
    SessionTranscriptRecord,
)
from ...shared.time_labels import describe_time_fields


def _message_timestamp(message: Any) -> str:
    created_at = getattr(message, "created_at", None)
    if created_at is None:
        return ""
    if hasattr(created_at, "isoformat"):
        return created_at.isoformat()
    return str(created_at)


def build_archive_records(archive_messages: list[Any]) -> list[ConversationArchiveRecord]:
    records: list[ConversationArchiveRecord] = []
    for message in archive_messages:
        timestamp = _message_timestamp(message)
        time_fields = describe_time_fields(timestamp)
        content = str(getattr(message, "content", "") or "")
        records.append(
            ConversationArchiveRecord(
                record_id=int(getattr(message, "id", 0) or 0),
                user_id=str(getattr(message, "user_id", "") or ""),
                local_date=str(time_fields.get("local_date") or ""),
                summary_text=content,
                transcript_excerpt=[
                    ConversationMessage(
                        role=str(getattr(message, "role", "user") or "user"),
                        content=content,
                        timestamp=timestamp or None,
                    )
                ],
                source_request_ids=[],
            )
        )
    return records


def build_session_transcript_records(*, session_id: str, archive_messages: list[Any]) -> list[SessionTranscriptRecord]:
    records: list[SessionTranscriptRecord] = []
    for message in archive_messages:
        timestamp = _message_timestamp(message)
        time_fields = describe_time_fields(timestamp)
        records.append(
            SessionTranscriptRecord(
                turn_id=str(getattr(message, "id", "") or ""),
                role=str(getattr(message, "role", "user") or "user"),
                content=str(getattr(message, "content", "") or ""),
                timestamp=timestamp,
                linked_meal_id=getattr(message, "linked_meal_log_id", None),
                local_date=time_fields.get("local_date"),
                source_request_id=getattr(message, "request_id", None),
                trace_id=None,
            )
        )
    return records


def build_pending_followup_state(*, latest_log: Any | None) -> PendingFollowupState:
    pending_question = str(getattr(latest_log, "pending_question", "") or "").strip()
    meal_id = getattr(latest_log, "id", None)
    meal_thread_id = getattr(latest_log, "meal_thread_id", None)
    is_open = bool(pending_question)
    return PendingFollowupState(
        is_open=is_open,
        question=pending_question or None,
        pending_question=pending_question or None,
        meal_id=meal_id,
        meal_thread_id=meal_thread_id,
        source_meal_id=meal_id,
        asked_at_utc=_message_timestamp(latest_log) if latest_log is not None else None,
        missing_high_impact_slots=[pending_question] if pending_question else [],
    )


def build_recent_turn_summary(recent_messages: list[Any]) -> RecentTurnSummary:
    user_turn = ""
    assistant_turn = ""
    for message in reversed(recent_messages):
        role = str(getattr(message, "role", "") or "")
        content = str(getattr(message, "content", "") or "")
        if not assistant_turn and role == "assistant":
            assistant_turn = content
        elif not user_turn and role == "user":
            user_turn = content
        if user_turn and assistant_turn:
            break
    return RecentTurnSummary(user_turn=user_turn, assistant_turn=assistant_turn)


def extract_current_session_preferences(messages: list[Any], *, preference_keywords: tuple[str, ...]) -> list[str]:
    preferences: list[str] = []
    for message in messages:
        content = str(getattr(message, "content", "") or "").strip()
        if not content:
            continue
        lowered = content.lower()
        if any(token and token in lowered for token in preference_keywords):
            preferences.append(content)
    return preferences


def build_session_summary(
    *,
    latest_log: Any | None,
    conversation_digest: Any,
    durable_memory_hits: list[Any],
    archive_messages: list[Any],
    extract_current_session_preferences: Callable[[list[Any]], list[str]],
) -> SessionSummary:
    latest_user_turns = [
        str(message.content or "")
        for message in archive_messages
        if str(getattr(message, "role", "") or "") == "user"
    ][-3:]
    latest_assistant_turns = [
        str(message.content or "")
        for message in archive_messages
        if str(getattr(message, "role", "") or "") == "assistant"
    ][-3:]
    open_questions = list(getattr(conversation_digest, "open_questions", []) or [])
    if getattr(conversation_digest, "pending_question", None):
        open_questions.append(str(conversation_digest.pending_question))
    return SessionSummary(
        latest_user_turns=latest_user_turns,
        latest_assistant_turns=latest_assistant_turns,
        open_questions=[item for item in open_questions if str(item).strip()],
        pending_followup=build_pending_followup_state(latest_log=latest_log),
        active_meal=ActiveMealSummary(
            meal_id=getattr(latest_log, "id", None),
            meal_thread_id=getattr(latest_log, "meal_thread_id", None),
            meal_version_id=getattr(latest_log, "meal_version_id", None),
            title=getattr(latest_log, "meal_title", None),
            meal_title=getattr(latest_log, "meal_title", None),
            status=getattr(latest_log, "status", None),
            pending_question=getattr(latest_log, "pending_question", None),
            followup_status="open" if getattr(latest_log, "pending_question", None) else "closed",
            unresolved_slots=[str(getattr(latest_log, "pending_question", "") or "").strip()]
            if getattr(latest_log, "pending_question", None)
            else [],
        ),
        current_session_preferences=extract_current_session_preferences(archive_messages),
    )


__all__ = [
    "build_archive_records",
    "build_pending_followup_state",
    "build_recent_turn_summary",
    "build_session_summary",
    "build_session_transcript_records",
    "extract_current_session_preferences",
]
