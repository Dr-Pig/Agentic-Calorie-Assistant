from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..database import append_message, get_conversation_archive, get_latest_log, get_meal_log_history, get_or_create_user, get_recent_messages
from ..domain import (
    ActiveMealSummary,
    ConversationArchiveRecord,
    ConversationDigest,
    ConversationMessage,
    ConversationRetrievalHit,
    ConversationState,
    DurableMemoryHit,
    MealRecord,
    PlannerStateDigest,
    RecentTurnSummary,
    RetrievedContextChunk,
    SessionTranscriptRecord,
    SessionSummary,
)
from .conversation_context_retriever import ConversationContextRetriever
from .session_record_store import retrieve_planner_context, sync_session_records
from ..models import MealLog, MessageBuffer, User

BOUNDARY_CLARIFICATION_QUESTION = "這是在補充剛剛那餐，還是你另外又吃了一份新的？"


@dataclass
class LoadedConversationContext:
    user: User
    latest_log: MealLog | None
    recent_messages: list[MessageBuffer]
    archive_messages: list[MessageBuffer]
    state: ConversationState


def _build_conversation_digest(
    *,
    latest_log: MealLog | None,
    recent_messages: list[MessageBuffer],
) -> ConversationDigest:
    recent_user_messages = [msg.content for msg in recent_messages if msg.role == "user"]
    last_explicit_correction = next(
        (
            content
            for content in reversed(recent_user_messages)
            if any(keyword in content for keyword in ["不是", "改成", "更正", "其實", "不要"])
        ),
        None,
    )
    answered_driver_signals = [
        content
        for content in recent_user_messages[-3:]
        if any(keyword in content for keyword in ["大", "小", "半", "一碗", "幾口", "幾顆", "無糖", "微糖", "少冰", "去冰"])
    ]
    unresolved = [latest_log.pending_question] if latest_log and latest_log.pending_question else []
    return ConversationDigest(
        active_meal_title=latest_log.meal_title if latest_log else None,
        active_parent_log_id=latest_log.id if latest_log and latest_log.status != "superseded" else None,
        pending_question=latest_log.pending_question if latest_log else None,
        answered_driver_signals=answered_driver_signals,
        unresolved_driver_signals=unresolved,
        last_explicit_correction=last_explicit_correction,
    )


def _build_durable_memory_hits(
    *,
    latest_log: MealLog | None,
    archive_messages: list[MessageBuffer],
) -> list[DurableMemoryHit]:
    hits: list[DurableMemoryHit] = []
    lowered_messages = [msg.content.strip() for msg in archive_messages if msg.content and msg.role == "user"]
    if latest_log and latest_log.meal_title:
        hits.append(
            DurableMemoryHit(
                memory_type="routine_meal",
                value=latest_log.meal_title,
                confidence="medium",
                source="meal_log",
            )
        )
    for text in reversed(lowered_messages[-12:]):
        normalized = text.lower()
        if any(token in normalized for token in ["不加糖", "無糖", "微糖", "半糖"]):
            hits.append(
                DurableMemoryHit(
                    memory_type="preference",
                    value=text,
                    confidence="medium",
                    source="transcript",
                )
            )
            break
    for text in reversed(lowered_messages[-12:]):
        normalized = text.lower()
        if any(token in normalized for token in ["減脂", "減肥", "控制熱量", "蛋白質"]):
            hits.append(
                DurableMemoryHit(
                    memory_type="goal",
                    value=text,
                    confidence="medium",
                    source="transcript",
                )
            )
            break
    return hits


def _build_active_meal_summary(
    *,
    latest_log: MealLog | None,
    conversation_digest: ConversationDigest,
) -> ActiveMealSummary:
    debug_steps = list(latest_log.debug_steps_json or []) if latest_log else []
    selected_evidence_titles = []
    for step in debug_steps:
        title = step.get("reference_title") or step.get("evidence_title")
        if title and title not in selected_evidence_titles:
            selected_evidence_titles.append(str(title))
    accepted_corrections = []
    if conversation_digest.last_explicit_correction:
        accepted_corrections.append(conversation_digest.last_explicit_correction)
    return ActiveMealSummary(
        meal_title=latest_log.meal_title if latest_log else None,
        status=latest_log.status if latest_log else None,
        unresolved_slots=[latest_log.pending_question] if latest_log and latest_log.pending_question else [],
        accepted_corrections=accepted_corrections,
        selected_evidence_titles=selected_evidence_titles[:3],
    )


def _build_recent_turn_summary(recent_messages: list[MessageBuffer]) -> RecentTurnSummary:
    return RecentTurnSummary(
        user_messages=[msg.content for msg in recent_messages if msg.role == "user"][-3:],
        assistant_messages=[msg.content for msg in recent_messages if msg.role == "assistant"][-3:],
    )


def _build_session_summary(
    *,
    latest_log: MealLog | None,
    conversation_digest: ConversationDigest,
    durable_memory_hits: list[DurableMemoryHit],
) -> SessionSummary:
    goal = next((hit.value for hit in durable_memory_hits if hit.memory_type == "goal"), None)
    return SessionSummary(
        active_goal=goal,
        active_meal_title=latest_log.meal_title if latest_log else None,
        open_questions=[latest_log.pending_question] if latest_log and latest_log.pending_question else [],
        recent_corrections=[conversation_digest.last_explicit_correction] if conversation_digest.last_explicit_correction else [],
    )


def _boundary_clarification_state(
    *,
    latest_log: MealLog | None,
    archive_messages: list[MessageBuffer],
) -> tuple[bool, int | None]:
    if latest_log and latest_log.pending_question == BOUNDARY_CLARIFICATION_QUESTION:
        return True, latest_log.id
    if not archive_messages:
        return False, None
    for msg in reversed(archive_messages):
        if msg.role != "assistant":
            continue
        if (msg.content or "").strip() == BOUNDARY_CLARIFICATION_QUESTION:
            return True, msg.linked_meal_log_id
        break
    return False, None


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
        transcript_records=[
            SessionTranscriptRecord(
                session_id=user_id,
                turn_id=msg.id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.created_at.isoformat(),
                trace_id=msg.trace_id,
                linked_meal_id=msg.linked_meal_log_id,
            ).model_dump(mode="json")
            for msg in archive_messages
        ],
        meal_records=[
            MealRecord(
                session_id=user_id,
                meal_id=log.id,
                title=log.meal_title,
                raw_input=log.raw_input,
                timestamp=log.timestamp.isoformat(),
                status=log.status,
                kcal=log.kcal,
                protein_g=log.protein_g,
                carb_g=log.carb_g,
                fat_g=log.fat_g,
                components=list(log.components_json or []),
                pending_question=log.pending_question,
                resolved_slots=[log.pending_question] if log.pending_question else [],
                parent_log_id=log.parent_log_id,
            ).model_dump(mode="json")
            for log in meal_history
        ],
    )
    archive_records = [
        ConversationArchiveRecord(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat(),
            linked_meal_log_id=msg.linked_meal_log_id,
        )
        for msg in archive_messages
    ]
    conversation_digest = _build_conversation_digest(
        latest_log=latest_log,
        recent_messages=archive_messages,
    )
    durable_memory_hits = _build_durable_memory_hits(
        latest_log=latest_log,
        archive_messages=archive_messages,
    )
    active_meal_summary = _build_active_meal_summary(
        latest_log=latest_log,
        conversation_digest=conversation_digest,
    )
    recent_turn_summary = _build_recent_turn_summary(recent_messages)
    session_summary = _build_session_summary(
        latest_log=latest_log,
        conversation_digest=conversation_digest,
        durable_memory_hits=durable_memory_hits,
    )
    retriever = ConversationContextRetriever()
    file_transcript_hits, file_meal_hits, active_meal_time_gap_seconds, retrieval_diagnostics = retrieve_planner_context(
        session_id=user_id,
        query=incoming_user_text or (latest_log.meal_title if latest_log else ""),
        active_meal_id=latest_log.id if latest_log else None,
        pending_question=latest_log.pending_question if latest_log else None,
    )
    boundary_clarification_open, boundary_clarification_source_meal_id = _boundary_clarification_state(
        latest_log=latest_log,
        archive_messages=archive_messages,
    )
    archive_hits = retriever.retrieve(
        archive=archive_records,
        query=incoming_user_text or (latest_log.meal_title if latest_log else ""),
        latest_meal_title=latest_log.meal_title if latest_log else None,
        pending_question=latest_log.pending_question if latest_log else None,
    )
    transcript_hits_for_archive = [
        ConversationRetrievalHit(
            message_id=int(chunk.source_id or 0),
            role=str(chunk.metadata.get("role") or "user"),
            content=chunk.content,
            created_at=chunk.timestamp or "",
            score=chunk.score,
            matched_terms=chunk.matched_terms,
            linked_meal_log_id=chunk.linked_meal_id,
        )
        for chunk in file_transcript_hits
    ]
    combined_archive_hits = transcript_hits_for_archive or archive_hits
    planner_state_digest = PlannerStateDigest(
        active_meal_log_id=latest_log.id if latest_log else None,
        active_meal_title=latest_log.meal_title if latest_log else None,
        active_parent_log_id=latest_log.id if latest_log and latest_log.status != "superseded" else None,
        pending_question=latest_log.pending_question if latest_log else None,
        candidate_components=[item.get("name", "") for item in list(latest_log.components_json or [])] if latest_log else [],
        recent_window_size=len(recent_messages),
        archive_hit_count=len(combined_archive_hits),
        answered_driver_signals=conversation_digest.answered_driver_signals,
        unresolved_driver_signals=conversation_digest.unresolved_driver_signals,
        last_explicit_correction=conversation_digest.last_explicit_correction,
    )
    state = ConversationState(
        user_id=user_id,
        latest_log_id=latest_log.id if latest_log else None,
        latest_log_status=latest_log.status if latest_log else None,
        active_unresolved_meal_id=latest_log.id if latest_log and latest_log.status in {"candidate_meal", "draft", "draft_unresolved"} else None,
        latest_meal_title=latest_log.meal_title if latest_log else None,
        latest_components=list(latest_log.components_json or []) if latest_log else [],
        pending_question=latest_log.pending_question if latest_log else None,
        recent_messages=[
            ConversationMessage(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat(),
            )
            for msg in recent_messages
        ],
        active_parent_log_id=latest_log.id if latest_log and latest_log.status != "superseded" else None,
        conversation_archive_count=len(archive_messages),
        conversation_window_size=len(recent_messages),
        conversation_archive_hits=combined_archive_hits,
        conversation_digest=conversation_digest,
        planner_state_digest=planner_state_digest,
        active_meal_summary=active_meal_summary,
        recent_turn_summary=recent_turn_summary,
        session_summary=session_summary,
        durable_memory_hits=durable_memory_hits,
        retrieved_transcript_chunks=file_transcript_hits,
        retrieved_meal_records=file_meal_hits,
        retrieval_diagnostics=retrieval_diagnostics,
        active_meal_time_gap_seconds=active_meal_time_gap_seconds,
        boundary_clarification_open=boundary_clarification_open,
        boundary_clarification_source_meal_id=boundary_clarification_source_meal_id,
    )
    return LoadedConversationContext(
        user=user,
        latest_log=latest_log,
        recent_messages=recent_messages,
        archive_messages=archive_messages,
        state=state,
    )
