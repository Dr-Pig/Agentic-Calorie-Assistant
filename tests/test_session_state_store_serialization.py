from __future__ import annotations

import json

from app.runtime.infrastructure import session_state_store
from app.shared.domain import MealRecord, SessionTranscriptRecord


def test_sync_session_records_serializes_domain_models_and_loads_jsonl(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(session_state_store, "SESSION_RECORD_ROOT", tmp_path)
    transcript = SessionTranscriptRecord(
        turn_id="turn-1",
        role="user",
        content="milk tea",
        timestamp="2026-04-30T01:00:00+00:00",
        local_date="2026-04-30",
    )
    meal = MealRecord(
        meal_id=10,
        meal_thread_id=77,
        meal_version_id=88,
        status="logged",
        title="milk tea",
        raw_input="I drank milk tea",
        timestamp="2026-04-30T01:00:00+00:00",
        local_date="2026-04-30",
    )

    session_state_store.sync_session_records(
        session_id="user/1",
        transcript_records=[transcript],
        meal_records=[meal],
    )

    transcript_line = session_state_store.transcript_path(tmp_path, "user/1").read_text(encoding="utf-8").splitlines()[0]
    meal_line = session_state_store.meal_path(tmp_path, "user/1").read_text(encoding="utf-8").splitlines()[0]

    assert json.loads(transcript_line)["turn_id"] == "turn-1"
    assert json.loads(meal_line)["meal_thread_id"] == 77
    assert session_state_store.load_transcript_records("user/1")[0].turn_id == "turn-1"
    assert session_state_store.load_meal_records("user/1")[0].meal_thread_id == 77
