from __future__ import annotations

import json
from typing import Any

from ..domain import ConversationState, PlannerContextPayload
from ..schemas import TurnState
from .context_normalizer import normalize_text


def normalized_input_from_debug_steps(debug_steps: list[dict[str, Any]]) -> str | None:
    for step in debug_steps:
        if step.get("step") != "planner_pass":
            continue
        value = normalize_text(str(step.get("normalized_user_input", "")))
        if value:
            return value
    return None


def build_turn_state(state: ConversationState) -> TurnState:
    candidate_components = [comp.get("name", "") for comp in state.latest_components if comp.get("name")]
    return TurnState(
        active_meal_log_id=state.latest_log_id,
        pending_question=state.pending_question,
        last_estimate_mode=None,
        candidate_components=candidate_components,
        allowed_next_intents=["clarification", "modification", "new_intake", "general_chat"],
    )


def render_conversation_state_prompt(state: ConversationState) -> str:
    turn_state = build_turn_state(state)
    state_json = turn_state.model_dump(mode="json")
    parts: list[str] = [f"[Current TurnState]\n{json.dumps(state_json, ensure_ascii=False, indent=2)}"]
    if state.planner_state_digest:
        parts.append("[Planner State Digest]\n" + json.dumps(state.planner_state_digest.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if state.active_meal_summary:
        parts.append("[Active Meal Summary]\n" + json.dumps(state.active_meal_summary.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if state.active_meal_state:
        parts.append("[Active Meal State]\n" + json.dumps(state.active_meal_state.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if state.pending_followup_state:
        parts.append("[Pending Follow-up State]\n" + json.dumps(state.pending_followup_state.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if state.session_summary:
        parts.append("[Session Summary]\n" + json.dumps(state.session_summary.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if state.durable_memory_hits:
        parts.append("[Durable Memory Hits]\n" + json.dumps([hit.model_dump(mode="json") for hit in state.durable_memory_hits], ensure_ascii=False, indent=2))
    if state.recent_messages:
        lines = []
        for msg in list(state.recent_messages)[-5:]:
            prefix = "USER" if msg.role == "user" else "ASSISTANT"
            lines.append(f"[{prefix}] {msg.content}")
        parts.append("[Recent Conversation Context]\n" + "\n".join(lines))
    if state.recent_relevant_turns:
        relevant_lines = []
        for msg in state.recent_relevant_turns[-3:]:
            prefix = "USER" if msg.role == "user" else "ASSISTANT"
            relevant_lines.append(f"[{prefix}] {msg.content}")
        parts.append("[Recent Relevant Turns]\n" + "\n".join(relevant_lines))
    if state.conversation_archive_hits:
        hit_lines = []
        for hit in state.conversation_archive_hits[:4]:
            prefix = "USER" if hit.role == "user" else "ASSISTANT"
            hit_lines.append(f"[{prefix}#{hit.message_id}] {hit.content}")
        parts.append("[Retrieved Conversation Hits]\n" + "\n".join(hit_lines))
    if state.retrieved_meal_records:
        meal_lines = []
        for chunk in state.retrieved_meal_records[:3]:
            meal_lines.append(f"[MEAL#{chunk.source_id}] {chunk.metadata.get('title', '')} :: {chunk.content[:240]}")
        parts.append("[Retrieved Meal Records]\n" + "\n".join(meal_lines))
    return "\n\n".join(parts)


def build_planner_context_payload(
    *,
    raw_user_input: str,
    thin_sanitized_input: str,
    allow_search: bool,
    state: ConversationState,
) -> PlannerContextPayload:
    return PlannerContextPayload(
        raw_user_input=raw_user_input,
        thin_sanitized_input=thin_sanitized_input,
        allow_search=allow_search,
        pending_question=state.pending_question,
        latest_meal_summary=state.latest_meal_title,
        conversation_state_summary={
            "latest_log_id": state.latest_log_id,
            "latest_log_status": state.latest_log_status,
            "latest_meal_title": state.latest_meal_title,
            "latest_components": state.latest_components,
            "pending_question": state.pending_question,
            "active_parent_log_id": state.active_parent_log_id,
            "recent_message_count": len(state.recent_messages),
            "conversation_window_size": state.conversation_window_size,
            "conversation_archive_count": state.conversation_archive_count,
            "conversation_archive_hit_count": len(state.conversation_archive_hits),
            "is_multi_turn_candidate": state.is_multi_turn_candidate,
            "boundary_clarification_open": state.boundary_clarification_open,
            "boundary_clarification_source_meal_id": state.boundary_clarification_source_meal_id,
        },
        planner_state_digest=state.planner_state_digest.model_dump(mode="json"),
        retrieved_transcript_chunks=[chunk.model_dump(mode="json") for chunk in state.retrieved_transcript_chunks],
        retrieved_meal_records=[chunk.model_dump(mode="json") for chunk in state.retrieved_meal_records],
        active_meal_summary=state.active_meal_summary.model_dump(mode="json"),
        pending_followup_state=state.pending_followup_state.model_dump(mode="json"),
        session_summary=state.session_summary.model_dump(mode="json"),
        durable_memory_hits=[hit.model_dump(mode="json") for hit in state.durable_memory_hits],
        active_meal_state={
            **state.active_meal_state.model_dump(mode="json"),
            "active_meal_id": state.latest_log_id,
            "active_meal_status": state.latest_log_status,
        },
        recent_relevant_turns=[msg.model_dump(mode="json") for msg in state.recent_relevant_turns],
        dynamic_context_pack={
            "active_meal_summary": state.active_meal_summary.model_dump(mode="json"),
            "active_meal_state": state.active_meal_state.model_dump(mode="json"),
            "pending_followup_state": state.pending_followup_state.model_dump(mode="json"),
            "recent_relevant_turns": [msg.model_dump(mode="json") for msg in state.recent_relevant_turns],
            "retrieved_meal_records": [chunk.model_dump(mode="json") for chunk in state.retrieved_meal_records],
            "session_summary": state.session_summary.model_dump(mode="json"),
        },
        time_distance_features={"active_meal_time_gap_seconds": state.active_meal_time_gap_seconds},
        boundary_state={
            "boundary_clarification_open": state.boundary_clarification_open,
            "boundary_clarification_source_meal_id": state.boundary_clarification_source_meal_id,
        },
        retrieved_conversation_context=[hit.model_dump(mode="json") for hit in state.conversation_archive_hits],
    )
