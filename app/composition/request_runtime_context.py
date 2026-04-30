from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.composition.conversation_state_loader import load_conversation_state
from app.shared.conversation_prompt import render_conversation_state_prompt
from app.shared.domain import ConversationState


@dataclass
class RequestRuntimeContext:
    user: Any | None
    latest_log: Any | None
    conversation_state: ConversationState
    incoming_user_message_id: int | None
    context_str: str
    manager_llm: Any


def load_request_runtime_context(
    *,
    request: Any,
    db: Session | None,
    provider: Any,
) -> RequestRuntimeContext:
    user = None
    latest_log = None
    incoming_user_message_id: int | None = None
    conversation_state = ConversationState(user_id=request.user_id)

    if db:
        loaded_context = load_conversation_state(db, user_id=request.user_id, incoming_user_text=request.text)
        user = loaded_context.user
        latest_log = loaded_context.latest_log
        conversation_state = loaded_context.state
        if loaded_context.recent_messages and loaded_context.recent_messages[-1].role == "user":
            incoming_user_message_id = loaded_context.recent_messages[-1].id

    return RequestRuntimeContext(
        user=user,
        latest_log=latest_log,
        conversation_state=conversation_state,
        incoming_user_message_id=incoming_user_message_id,
        context_str=render_conversation_state_prompt(conversation_state) if conversation_state else "",
        manager_llm=provider,
    )
