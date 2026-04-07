"""
Conversation State Manager - Load and update conversation state.

Responsibilities:
- Load conversation state from database
- Update state after successful estimation
- Maintain state consistency across passes

Best Practices:
- State loaded once at request start
- State updates are atomic
- Full audit trail maintained
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...domain import ConversationState
from ...infrastructure.conversation_state_loader import load_conversation_state
from ...infrastructure.meal_log_persistence import persist_text_meal_result


@dataclass
class LoadedContext:
    """Result of loading conversation context."""
    state: ConversationState
    user: Any
    latest_log: Any
    recent_messages: list[Any]
    incoming_user_message_id: int | None = None


class ConversationStateManager:
    """
    Manages conversation state lifecycle.

    Best Practices:
    - Single source of truth for state
    - Atomic updates
    - Proper error handling
    """

    def load(
        self,
        db: Any,
        user_id: str,
        user_input: str,
    ) -> LoadedContext | None:
        """
        Load conversation state for a request.

        Returns:
            LoadedContext with all state or None on failure
        """
        try:
            loaded = load_conversation_state(
                db,
                user_id=user_id,
                incoming_user_text=user_input,
            )

            incoming_message_id = None
            if (
                loaded.recent_messages
                and loaded.recent_messages[-1].role == "user"
            ):
                incoming_message_id = loaded.recent_messages[-1].id

            return LoadedContext(
                state=loaded.state,
                user=loaded.user,
                latest_log=loaded.latest_log,
                recent_messages=loaded.recent_messages or [],
                incoming_user_message_id=incoming_message_id,
            )
        except Exception:
            return None

    def persist(
        self,
        db: Any,
        user: Any,
        latest_log: Any,
        planner_intent: str,
        payload: Any,
        raw_input: str,
        request_id: str,
        incoming_user_message_id: int | None,
    ) -> dict[str, Any] | None:
        """
        Persist estimation result to state.

        Returns:
            Persistence decision dict or None on failure
        """
        try:
            return persist_text_meal_result(
                db,
                user=user,
                latest_log=latest_log,
                planner_intent=planner_intent,
                payload=payload,
                raw_input=raw_input,
                request_id=request_id,
                incoming_user_message_id=incoming_user_message_id,
            )
        except Exception:
            return None

    def get_context_string(self, state: ConversationState) -> str:
        """Render conversation state as prompt string."""
        from ...application.context_assembly import render_conversation_state_prompt
        return render_conversation_state_prompt(state)
