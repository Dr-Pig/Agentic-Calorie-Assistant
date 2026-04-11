from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..application.conversation_state_assembler import (
    assemble_conversation_state,
    build_archive_records,
    build_session_meal_records,
    build_session_transcript_records,
)
from ..database import append_message, get_conversation_archive, get_latest_log, get_meal_log_history, get_or_create_user, get_recent_messages
from ..domain import ConversationState
from ..models import MealLog, MessageBuffer, User
from .conversation_context_retriever import ConversationContextRetriever
from .session_record_store import retrieve_planner_context, sync_session_records


@dataclass
class LoadedConversationContext:
    user: User
    latest_log: MealLog | None
    recent_messages: list[MessageBuffer]
    archive_messages: list[MessageBuffer]
    state: ConversationState


def load_conversation_state(db: Session, *, user_id: str, incoming_user_text: str | None = None) -> LoadedConversationContext:
    user = get_or_create_user(db, user_id)
    if incoming_user_text:
        append_message(db, user, "user", incoming_user_text)

    latest_log = get_latest_log(db, user)
    meal_history = get_meal_log_history(db, user, limit=30, include_superseded=True)
    recent_messages = get_recent_messages(db, user, limit=5)
    archive_messages = get_conversation_archive(db, user)

    sync_session_records(
        session_id=user_id,
        transcript_records=build_session_transcript_records(session_id=user_id, archive_messages=archive_messages),
        meal_records=build_session_meal_records(session_id=user_id, meal_history=meal_history),
    )

    archive_records = build_archive_records(archive_messages)
    retriever = ConversationContextRetriever()
    file_transcript_hits, file_meal_hits, active_meal_time_gap_seconds, retrieval_diagnostics = retrieve_planner_context(
        session_id=user_id,
        query=incoming_user_text or (latest_log.meal_title if latest_log else ""),
        active_meal_id=latest_log.id if latest_log else None,
        pending_question=latest_log.pending_question if latest_log else None,
    )
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
