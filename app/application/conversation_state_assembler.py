from __future__ import annotations

from typing import Any

from ..domain import (
    ActiveMealState,
    ActiveMealSummary,
    ConversationArchiveRecord,
    ConversationDigest,
    ConversationMessage,
    ConversationRetrievalHit,
    ConversationState,
    DurableMemoryHit,
    MealRecord,
    PendingFollowupState,
    PlannerStateDigest,
    RecentTurnSummary,
    SessionSummary,
    SessionTranscriptRecord,
)
from .time_labels import describe_time_fields

BOUNDARY_CLARIFICATION_QUESTION = "這是在補充剛剛那餐，還是你另外又吃了一份新的？"

MEAL_TYPE_TOKENS = {
    "breakfast": ("早餐", "早上", "breakfast"),
    "lunch": ("午餐", "中午", "lunch"),
    "dinner": ("晚餐", "晚上", "dinner"),
    "snack": ("點心", "宵夜", "snack"),
}
CORRECTION_KEYWORDS = ("不是", "改成", "更正", "其實", "不要")
PREFERENCE_KEYWORDS = ("不加糖", "無糖", "微糖", "半糖", "少冰", "去冰")
GOAL_KEYWORDS = ("減脂", "減肥", "控制熱量", "蛋白質")
ANSWERED_SIGNAL_KEYWORDS = ("大", "小", "半", "一碗", "幾口", "幾顆", "無糖", "微糖", "少冰", "去冰")


def infer_meal_type(text: str) -> str:
    normalized = (text or "").lower()
    for meal_type, tokens in MEAL_TYPE_TOKENS.items():
        if any(token in normalized for token in tokens):
            return meal_type
    return "unknown"


def extract_current_session_preferences(archive_messages: list[Any]) -> list[str]:
    preferences: list[str] = []
    for msg in reversed(archive_messages[-12:]):
        if msg.role != "user":
            continue
        content = (msg.content or "").strip()
        if not content:
            continue
        normalized = content.lower()
        if any(token in normalized for token in PREFERENCE_KEYWORDS):
            if content not in preferences:
                preferences.append(content)
        if len(preferences) >= 3:
            break
    return list(reversed(preferences))


def build_session_transcript_records(*, session_id: str, archive_messages: list[Any]) -> list[dict[str, Any]]:
    return [
        SessionTranscriptRecord(
            session_id=session_id,
            turn_id=msg.id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.created_at.isoformat(),
            trace_id=msg.trace_id,
            linked_meal_id=msg.linked_meal_log_id,
        ).model_dump(mode="json")
        for msg in archive_messages
    ]


def build_session_meal_records(*, session_id: str, meal_history: list[Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for log in meal_history:
        time_fields = describe_time_fields(log.timestamp.isoformat())
        records.append(
            MealRecord(
                session_id=session_id,
                meal_id=log.id,
                title=log.meal_title,
                raw_input=log.raw_input,
                timestamp=log.timestamp.isoformat(),
                status=log.status,
                conversation_id=session_id,
                user_id=session_id,
                created_at_utc=log.timestamp.isoformat(),
                updated_at_utc=log.timestamp.isoformat(),
                occurred_at_utc=time_fields.get("occurred_at_utc"),
                occurred_at_local=time_fields.get("occurred_at_local"),
                local_date=time_fields.get("local_date"),
                timezone=time_fields.get("timezone"),
                relative_time_label=time_fields.get("relative_time_label"),
                meal_type=infer_meal_type(f"{log.meal_title} {log.raw_input}"),
                normalized_user_input=log.raw_input,
                resolved_food_items=[
                    str(item.get("name") or "")
                    for item in list(log.components_json or [])
                    if str(item.get("name") or "").strip()
                ],
                kcal=log.kcal,
                protein_g=log.protein_g,
                carb_g=log.carb_g,
                fat_g=log.fat_g,
                components=list(log.components_json or []),
                component_breakdown=list(log.components_json or []),
                pending_question=log.pending_question,
                followup_status="open" if log.pending_question else "closed",
                missing_slots=[log.pending_question] if log.pending_question else [],
                resolved_slots=[log.pending_question] if log.pending_question else [],
                parent_log_id=log.parent_log_id,
                correction_parent_meal_id=log.parent_log_id,
            ).model_dump(mode="json")
        )
    return records


def build_archive_records(archive_messages: list[Any]) -> list[ConversationArchiveRecord]:
    return [
        ConversationArchiveRecord(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat(),
            linked_meal_log_id=msg.linked_meal_log_id,
        )
        for msg in archive_messages
    ]


def _build_conversation_digest(*, latest_log: Any | None, recent_messages: list[Any]) -> ConversationDigest:
    recent_user_messages = [msg.content for msg in recent_messages if msg.role == "user"]
    last_explicit_correction = next(
        (
            content
            for content in reversed(recent_user_messages)
            if any(keyword in content for keyword in CORRECTION_KEYWORDS)
        ),
        None,
    )
    answered_driver_signals = [
        content
        for content in recent_user_messages[-3:]
        if any(keyword in content for keyword in ANSWERED_SIGNAL_KEYWORDS)
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


def _build_durable_memory_hits(*, latest_log: Any | None, archive_messages: list[Any]) -> list[DurableMemoryHit]:
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
        if any(token in normalized for token in PREFERENCE_KEYWORDS):
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
        if any(token in normalized for token in GOAL_KEYWORDS):
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


def _build_active_meal_summary(*, latest_log: Any | None, conversation_digest: ConversationDigest) -> ActiveMealSummary:
    debug_steps = list(latest_log.debug_steps_json or []) if latest_log else []
    selected_evidence_titles: list[str] = []
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


def _build_active_meal_state(*, latest_log: Any | None, conversation_digest: ConversationDigest) -> ActiveMealState:
    if latest_log is None:
        return ActiveMealState()
    time_fields = describe_time_fields(latest_log.timestamp.isoformat() if latest_log.timestamp else None)
    debug_steps = list(latest_log.debug_steps_json or [])
    trace_contract = next(
        (
            dict(step.get("trace_contract") or {})
            for step in reversed(debug_steps)
            if isinstance(step, dict) and step.get("trace_contract")
        ),
        {},
    )
    return ActiveMealState(
        meal_id=latest_log.id,
        meal_title=latest_log.meal_title,
        status=latest_log.status,
        estimate_mode=str(trace_contract.get("best_estimate_mode") or "") or None,
        confidence=str(trace_contract.get("estimate_confidence_tier") or "") or None,
        pending_question=latest_log.pending_question,
        missing_slots=[latest_log.pending_question] if latest_log.pending_question else [],
        resolved_slots=[],
        resolved_food_items=[
            str(item.get("name") or "")
            for item in list(latest_log.components_json or [])
            if str(item.get("name") or "").strip()
        ],
        accepted_corrections=[conversation_digest.last_explicit_correction] if conversation_digest.last_explicit_correction else [],
        relative_time_label=time_fields.get("relative_time_label") or None,
        local_date=time_fields.get("local_date") or None,
    )


def _build_pending_followup_state(*, latest_log: Any | None) -> PendingFollowupState:
    if latest_log is None or not latest_log.pending_question:
        return PendingFollowupState()
    return PendingFollowupState(
        is_open=True,
        source_meal_id=latest_log.id,
        pending_question=latest_log.pending_question,
        missing_high_impact_slots=[latest_log.pending_question],
        asked_questions_history=[latest_log.pending_question],
        reason_not_direct_answer="high_impact_slot_missing",
    )


def _build_recent_turn_summary(recent_messages: list[Any]) -> RecentTurnSummary:
    return RecentTurnSummary(
        user_messages=[msg.content for msg in recent_messages if msg.role == "user"][-3:],
        assistant_messages=[msg.content for msg in recent_messages if msg.role == "assistant"][-3:],
    )


def _build_session_summary(
    *,
    latest_log: Any | None,
    conversation_digest: ConversationDigest,
    durable_memory_hits: list[DurableMemoryHit],
    archive_messages: list[Any],
) -> SessionSummary:
    goal = next((hit.value for hit in durable_memory_hits if hit.memory_type == "goal"), None)
    return SessionSummary(
        active_goal=goal,
        active_meal_title=latest_log.meal_title if latest_log else None,
        open_questions=[latest_log.pending_question] if latest_log and latest_log.pending_question else [],
        recent_corrections=[conversation_digest.last_explicit_correction] if conversation_digest.last_explicit_correction else [],
        current_session_preferences_light=extract_current_session_preferences(archive_messages),
    )


def _boundary_clarification_state(*, latest_log: Any | None, archive_messages: list[Any]) -> tuple[bool, int | None]:
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


def assemble_conversation_state(
    *,
    user_id: str,
    latest_log: Any | None,
    recent_messages: list[Any],
    archive_messages: list[Any],
    archive_hits: list[Any],
    file_transcript_hits: list[Any],
    file_meal_hits: list[Any],
    retrieval_diagnostics: dict[str, Any],
    active_meal_time_gap_seconds: int | None,
) -> ConversationState:
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
    active_meal_state = _build_active_meal_state(
        latest_log=latest_log,
        conversation_digest=conversation_digest,
    )
    pending_followup_state = _build_pending_followup_state(latest_log=latest_log)
    recent_turn_summary = _build_recent_turn_summary(recent_messages)
    session_summary = _build_session_summary(
        latest_log=latest_log,
        conversation_digest=conversation_digest,
        durable_memory_hits=durable_memory_hits,
        archive_messages=archive_messages,
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
    boundary_clarification_open, boundary_clarification_source_meal_id = _boundary_clarification_state(
        latest_log=latest_log,
        archive_messages=archive_messages,
    )
    recent_relevant_turns = [
        ConversationMessage(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat(),
        )
        for msg in recent_messages[-3:]
    ]
    return ConversationState(
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
        active_meal_state=active_meal_state,
        pending_followup_state=pending_followup_state,
        recent_turn_summary=recent_turn_summary,
        session_summary=session_summary,
        durable_memory_hits=durable_memory_hits,
        retrieved_transcript_chunks=file_transcript_hits,
        retrieved_meal_records=file_meal_hits,
        recent_relevant_turns=recent_relevant_turns,
        retrieval_diagnostics=retrieval_diagnostics,
        active_meal_time_gap_seconds=active_meal_time_gap_seconds,
        boundary_clarification_open=boundary_clarification_open,
        boundary_clarification_source_meal_id=boundary_clarification_source_meal_id,
    )
