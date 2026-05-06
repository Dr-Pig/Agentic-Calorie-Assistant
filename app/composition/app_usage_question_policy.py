from __future__ import annotations

from typing import Any


def build_app_usage_question_policy() -> dict[str, Any]:
    return {
        "workflow_effect": "answer_general_product_question_without_state_mutation",
        "reply_text": "I can answer general product questions here, but I will not change state from this path.",
        "required_read_surfaces": [],
        "ui_hints": {"mode": "general_chat_fallback_answer", "delivery": "chat_only"},
    }


__all__ = ["build_app_usage_question_policy"]
