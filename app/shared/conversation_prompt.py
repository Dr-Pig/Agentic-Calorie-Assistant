from __future__ import annotations

import json

from app.shared.domain import ConversationState
from ..schemas import TurnState


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
