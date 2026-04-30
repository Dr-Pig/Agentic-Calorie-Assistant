from __future__ import annotations

from app.runtime.application.conversation_state_assembler import assemble_conversation_state
from app.shared.domain import RetrievedContextChunk


def test_assemble_conversation_state_maps_transcript_hits_to_archive_hit_contract() -> None:
    state = assemble_conversation_state(
        user_id="user-1",
        latest_log=None,
        recent_messages=[],
        archive_messages=[],
        archive_hits=[],
        file_transcript_hits=[
            RetrievedContextChunk(
                chunk_id="transcript:1",
                source_type="transcript",
                source_id=1,
                content="milk tea context",
                timestamp="2026-04-30T01:00:00+00:00",
                score=3.0,
                matched_terms=["milk", "tea"],
                metadata={"local_date": "2026-04-30"},
            )
        ],
        file_meal_hits=[],
        retrieval_diagnostics={},
        active_meal_time_gap_seconds=None,
    )

    assert state.conversation_archive_hits[0].record_id == 1
    assert state.conversation_archive_hits[0].summary_text == "milk tea context"
    assert state.conversation_archive_hits[0].local_date == "2026-04-30"
