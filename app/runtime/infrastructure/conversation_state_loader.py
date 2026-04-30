from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.runtime.application.conversation_state_assembler import (
    assemble_conversation_state,
    build_archive_records,
    build_session_meal_records,
    build_session_transcript_records,
)
from app.database import append_message, get_conversation_archive, get_latest_log, get_meal_log_history, get_or_create_user, get_recent_messages
from app.shared.domain import ConversationState
from app.models import MealLog, MessageBuffer, User
from .conversation_archive_retriever import ConversationArchiveRetriever
from .session_state_store import retrieve_manager_context_from_records, sync_session_records

DEFAULT_CONVERSATION_ARCHIVE_LIMIT = 120


@dataclass
class LoadedConversationContext:
    user: User
    latest_log: MealLog | None
    recent_messages: list[MessageBuffer]
    archive_messages: list[MessageBuffer]
    state: ConversationState


def _conversation_archive_limit() -> int:
    raw_value = os.getenv("CONVERSATION_ARCHIVE_REQUEST_LIMIT")
    if raw_value is None:
        return DEFAULT_CONVERSATION_ARCHIVE_LIMIT
    try:
        return max(int(raw_value), 1)
    except ValueError:
        return DEFAULT_CONVERSATION_ARCHIVE_LIMIT


def _request_sidecar_sync_enabled() -> bool:
    return os.getenv("SESSION_RECORD_SYNC_ON_REQUEST", "").strip().lower() in {"1", "true", "yes", "on"}


def load_conversation_state(
    db: Session,
    *,
    user_id: str,
    incoming_user_text: str | None = None,
    persist_incoming_user_text: bool = True,
) -> LoadedConversationContext:
    user = get_or_create_user(db, user_id)
    if incoming_user_text and persist_incoming_user_text:
        append_message(db, user, "user", incoming_user_text)

    latest_log = get_latest_log(db, user)
    meal_history = get_meal_log_history(db, user, limit=30, include_superseded=True)
    recent_messages = get_recent_messages(db, user, limit=5)
    archive_messages = get_conversation_archive(db, user, limit=_conversation_archive_limit())
    transcript_records = build_session_transcript_records(session_id=user_id, archive_messages=archive_messages)
    meal_records = build_session_meal_records(session_id=user_id, meal_history=meal_history)

    file_transcript_hits, file_meal_hits, active_meal_time_gap_seconds, retrieval_diagnostics = (
        retrieve_manager_context_from_records(
            transcript_records=transcript_records,
            meal_records=meal_records,
            query=incoming_user_text or (latest_log.meal_title if latest_log else ""),
            active_meal_id=latest_log.id if latest_log else None,
            pending_question=latest_log.pending_question if latest_log else None,
        )
    )

    if _request_sidecar_sync_enabled():
        sync_session_records(
            session_id=user_id,
            transcript_records=transcript_records,
            meal_records=meal_records,
        )

    archive_records = build_archive_records(archive_messages)
    retriever = ConversationArchiveRetriever()
    archive_hits = retriever.retrieve(
        archive=archive_records,
        query=incoming_user_text or (latest_log.meal_title if latest_log else ""),
        latest_meal_title=latest_log.meal_title if latest_log else None,
        pending_question=latest_log.pending_question if latest_log else None,
    )

    state = assemble_conversation_state(
        user_id=user_id,
        latest_log=latest_log,
        recent_messages=recent_messages,
        archive_messages=archive_messages,
        archive_hits=archive_hits,
        file_transcript_hits=file_transcript_hits,
        file_meal_hits=file_meal_hits,
        retrieval_diagnostics=retrieval_diagnostics,
        active_meal_time_gap_seconds=active_meal_time_gap_seconds,
    )
    return LoadedConversationContext(
        user=user,
        latest_log=latest_log,
        recent_messages=recent_messages,
        archive_messages=archive_messages,
        state=state,
    )
