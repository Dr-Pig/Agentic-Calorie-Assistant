from __future__ import annotations

from app.runtime.infrastructure.conversation_archive_retriever import ConversationArchiveRetriever
from app.shared.domain import ConversationArchiveRecord, ConversationMessage


def test_conversation_archive_retriever_uses_archive_record_contract() -> None:
    retriever = ConversationArchiveRetriever()
    archive = [
        ConversationArchiveRecord(
            record_id=101,
            user_id="user-1",
            local_date="2026-04-30",
            summary_text="User drank milk tea.",
            transcript_excerpt=[
                ConversationMessage(
                    role="user",
                    content="bubble tea half sugar",
                    timestamp="2026-04-30T01:00:00+00:00",
                )
            ],
        )
    ]

    hits = retriever.retrieve(
        archive=archive,
        query="milk tea",
        latest_meal_title=None,
        pending_question=None,
    )

    assert len(hits) == 1
    assert hits[0].record_id == 101
    assert hits[0].summary_text == "User drank milk tea."
    assert hits[0].local_date == "2026-04-30"
    assert hits[0].matched_terms == ["milk", "tea"]
