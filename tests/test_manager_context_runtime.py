from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.composition import manager_context_runtime
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1
from app.database import append_message, get_or_create_user
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord
from app.models import Base
from app.runtime.contracts.phase_a import CurrentTurnContextV1, InteractionEvent


def _context() -> CurrentTurnContextV1:
    return CurrentTurnContextV1(
        user_utterance="today update",
        recent_chat_turns=[
            {"message_id": "phase-a-1", "role": "user", "content": "old phase a"},
            {"message_id": "phase-a-2", "role": "assistant", "content": "old phase a reply"},
        ],
        current_interaction_event=InteractionEvent(
            source="chat",
            event_type="user_message",
            raw_text="today update",
        ),
    )


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, session_local()


def test_runtime_manager_context_packet_loads_last_20_same_day_messages_from_db() -> None:
    engine, db = _session()
    try:
        user = get_or_create_user(db, "context-user")
        for index in range(3):
            append_message(
                db,
                user,
                "user",
                f"yesterday-{index}",
                trace_id=f"yesterday-{index}",
                trace_json={"runtime_turn_trace": {"local_date": "2026-05-03"}},
            )
        for index in range(25):
            append_message(
                db,
                user,
                "assistant" if index % 2 else "user",
                f"today-{index:02d}",
                trace_id=f"today-{index}",
                trace_json={"runtime_turn_trace": {"local_date": "2026-05-04"}},
            )

        packet = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=_context(),
            user_external_id="context-user",
            local_date="2026-05-04",
            session_id="session-1",
        )
    finally:
        db.close()
        engine.dispose()

    assert packet is not None
    messages = packet["recent_chat_window"]["messages"]
    assert packet["context_loading_artifact"]["loaded_message_count"] == 20
    assert packet["context_loading_artifact"]["omitted_count"] == 5
    assert [message["content"] for message in messages] == [f"today-{index:02d}" for index in range(5, 25)]
    assert all(message["local_date"] == "2026-05-04" for message in messages)
    assert all(not str(message["content"]).startswith("yesterday") for message in messages)


def test_runtime_manager_context_packet_filters_before_selecting_last_20_same_day_messages() -> None:
    engine, db = _session()
    try:
        user = get_or_create_user(db, "context-user")
        for index in range(20):
            append_message(
                db,
                user,
                "user",
                f"current-day-{index:02d}",
                trace_id=f"current-{index}",
                trace_json={"runtime_turn_trace": {"local_date": "2026-05-04"}},
            )
        for index in range(80):
            append_message(
                db,
                user,
                "assistant",
                f"newer-cross-day-{index:02d}",
                trace_id=f"cross-{index}",
                trace_json={"runtime_turn_trace": {"local_date": "2026-05-05"}},
            )

        packet = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=_context(),
            user_external_id="context-user",
            local_date="2026-05-04",
            session_id="session-1",
        )
    finally:
        db.close()
        engine.dispose()

    assert packet is not None
    messages = packet["recent_chat_window"]["messages"]
    assert packet["context_loading_artifact"]["loaded_message_count"] == 20
    assert packet["context_loading_artifact"]["omitted_count"] == 0
    assert [message["content"] for message in messages] == [f"current-day-{index:02d}" for index in range(20)]
    assert all(message["local_date"] == "2026-05-04" for message in messages)


def test_runtime_manager_context_packet_scan_is_bounded_before_python_date_filtering() -> None:
    engine, db = _session()
    try:
        user = get_or_create_user(db, "context-user")
        append_message(
            db,
            user,
            "user",
            "outside-scan-current-day",
            trace_id="outside-scan-current-day",
            trace_json={"runtime_turn_trace": {"local_date": "2026-05-04"}},
        )
        scan_limit = getattr(manager_context_runtime, "MANAGER_CONTEXT_RECENT_SCAN_LIMIT", 500)
        for index in range(scan_limit):
            append_message(
                db,
                user,
                "assistant",
                f"newer-cross-day-{index:03d}",
                trace_id=f"newer-cross-day-{index}",
                trace_json={"runtime_turn_trace": {"local_date": "2026-05-05"}},
            )

        packet = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=_context(),
            user_external_id="context-user",
            local_date="2026-05-04",
            session_id="session-1",
        )
    finally:
        db.close()
        engine.dispose()

    assert packet is not None
    contents = [message["content"] for message in packet["recent_chat_window"]["messages"]]
    assert "outside-scan-current-day" not in contents
    assert all(not str(content).startswith("newer-cross-day") for content in contents)


def test_runtime_manager_context_packet_loads_same_day_pending_draft_pin() -> None:
    engine, db = _session()
    try:
        user = get_or_create_user(db, "context-user")
        thread = MealThreadRecord(user_id=user.id, title="pending soup", active_version_id=None)
        db.add(thread)
        db.commit()
        db.refresh(thread)
        version = MealVersionRecord(
            meal_thread_id=thread.id,
            version_status="active",
            resolution_status="draft_unresolved",
            meal_title="pending soup",
            raw_input="soup, need portion",
            local_date="2026-05-04",
            source_request_id="turn-draft",
            total_kcal=0,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        thread.active_version_id = version.id
        db.add(thread)
        db.commit()
        thread_id = thread.id
        version_id = version.id

        packet = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=_context(),
            user_external_id="context-user",
            local_date="2026-05-04",
            session_id="session-1",
        )
    finally:
        db.close()
        engine.dispose()

    pending_draft = packet["hard_pins"]["pending_draft"]
    assert pending_draft == {
        "meal_thread_id": thread_id,
        "meal_version_id": version_id,
        "meal_title": "pending soup",
        "resolution_status": "draft_unresolved",
        "source_request_id": "turn-draft",
        "read_only": True,
        "mutation_authority": False,
    }
