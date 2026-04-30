from __future__ import annotations

from app.runtime.infrastructure.trace.text_meal_observability import build_multi_turn_context
from app.shared.conversation_prompt import render_conversation_state_prompt
from app.shared.domain import ConversationRetrievalHit, ConversationState


def _state_with_archive_hit() -> ConversationState:
    return ConversationState(
        conversation_archive_hits=[
            ConversationRetrievalHit(
                record_id=42,
                summary_text="User previously logged pearl milk tea.",
                local_date="2026-04-30",
                score=4.5,
                matched_terms=["pearl", "milk", "tea"],
                rationale="archive_summary",
            )
        ]
    )


def test_prompt_renderer_uses_current_conversation_retrieval_hit_contract() -> None:
    prompt = render_conversation_state_prompt(_state_with_archive_hit())

    assert "[ARCHIVE#42]" in prompt
    assert "2026-04-30" in prompt
    assert "User previously logged pearl milk tea." in prompt
    assert "pearl, milk, tea" in prompt
    assert "archive_summary" in prompt


def test_text_meal_observability_uses_current_conversation_retrieval_hit_contract() -> None:
    context = build_multi_turn_context(
        state=_state_with_archive_hit(),
        manager_intent="new_intake",
        context_snapshot="snapshot",
        retrieval_query_rewritten=False,
        original_retrieval_query=None,
        effective_retrieval_query=None,
    )

    assert context["conversation_archive_hit_count"] == 1
    assert context["conversation_hit_refs"] == [42]
