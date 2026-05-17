from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.composition import manager_context_runtime
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1
from app.database import append_message, get_or_create_user
from app.intake.infrastructure.models import MealItemRecord, MealThreadRecord, MealVersionRecord
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


def test_runtime_manager_context_packet_excludes_current_request_trace_from_recent_chat_turns() -> None:
    engine, db = _session()
    try:
        user = get_or_create_user(db, "context-user")
        append_message(
            db,
            user,
            "user",
            "previous completed turn",
            trace_id="previous-turn",
            trace_json={"runtime_turn_trace": {"local_date": "2026-05-04"}},
        )
        append_message(
            db,
            user,
            "user",
            "current pending user turn",
            trace_id="current-turn",
            trace_json={"runtime_turn_trace": {"local_date": "2026-05-04"}},
        )
        append_message(
            db,
            user,
            "assistant",
            "處理中...",
            trace_id="current-turn",
            trace_json={"runtime_turn_trace": {"local_date": "2026-05-04"}},
        )

        packet = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=_context(),
            user_external_id="context-user",
            local_date="2026-05-04",
            session_id="session-1",
            exclude_trace_id="current-turn",
        )
    finally:
        db.close()
        engine.dispose()

    assert packet is not None
    contents = [message["content"] for message in packet["recent_chat_window"]["messages"]]
    assert contents == ["previous completed turn"]


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


def test_runtime_manager_context_packet_exposes_active_meal_estimate_basis_read_only() -> None:
    engine, db = _session()
    try:
        user = get_or_create_user(db, "context-user")
        thread = MealThreadRecord(user_id=user.id, title="早餐店鐵板麵套餐", active_version_id=None)
        db.add(thread)
        db.commit()
        db.refresh(thread)
        version = MealVersionRecord(
            meal_thread_id=thread.id,
            version_status="active",
            version_reason="new_intake",
            resolution_status="completed_meal",
            meal_title="早餐店鐵板麵套餐",
            raw_input="我早餐吃個早點店的鐵板麵套餐",
            local_date="2026-05-04",
            source_request_id="turn-breakfast",
            total_kcal=620,
            protein_g=24,
            carb_g=70,
            fat_g=22,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        thread.active_version_id = version.id
        db.add_all(
            [
                thread,
                MealItemRecord(
                    meal_version_id=version.id,
                    item_index=0,
                    name="鐵板麵",
                    quantity_hint="1 份",
                    source="fooddb",
                    evidence_role="component",
                    estimate_basis="fooddb_generic_component",
                    confidence_tier="medium",
                    estimated_kcal=420,
                    carb_g=62,
                    fat_g=14,
                    evidence_ids_json=["fdb-teppan-noodle"],
                ),
                MealItemRecord(
                    meal_version_id=version.id,
                    item_index=1,
                    name="荷包蛋",
                    quantity_hint="1 顆",
                    source="fooddb",
                    evidence_role="component",
                    estimate_basis="fooddb_component",
                    confidence_tier="high",
                    estimated_kcal=90,
                    protein_g=6,
                    fat_g=7,
                    evidence_ids_json=["fdb-fried-egg"],
                ),
            ]
        )
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

    assert packet is not None
    basis = packet["active_day_state"]["active_meal_estimate_basis"]
    assert basis["meal_thread_id"] == thread_id
    assert basis["meal_version_id"] == version_id
    assert basis["meal_title"] == "早餐店鐵板麵套餐"
    assert basis["raw_input"] == "我早餐吃個早點店的鐵板麵套餐"
    assert basis["total_kcal"] == 620
    assert basis["macro_summary"] == {
        "protein_g": 24,
        "carb_g": 70,
        "fat_g": 22,
        "macro_visibility_status": "present",
    }
    assert basis["truth_owner"] == "canonical_meal_read_model"
    assert basis["read_only"] is True
    assert basis["mutation_authority"] is False
    assert [item["canonical_name"] for item in basis["items"]] == ["鐵板麵", "荷包蛋"]
    assert basis["items"][0]["estimate_basis"] == "fooddb_generic_component"
    assert basis["items"][0]["evidence_id_count"] == 1
    assert all(item["read_only"] is True for item in basis["items"])
    assert all(item["mutation_authority"] is False for item in basis["items"])
    assert "intent_type" not in basis
    assert "final_action" not in basis
    assert "workflow_effect" not in basis

    candidates = packet["target_candidates"]["for_correction_or_removal"]
    assert candidates[0]["target_object_type"] == "meal_thread"
    assert candidates[0]["estimated_kcal"] == 620
    assert candidates[0]["estimate_basis"] == "active_meal_version_total"
    item_candidates = [candidate for candidate in candidates if candidate["target_object_type"] == "meal_item"]
    assert [candidate["canonical_name"] for candidate in item_candidates] == ["鐵板麵", "荷包蛋"]
    assert item_candidates[0]["estimated_kcal"] == 420
    assert item_candidates[0]["confidence_tier"] == "medium"
    assert all(candidate["read_only"] is True for candidate in candidates)
    assert all(candidate["mutation_authority"] is False for candidate in candidates)


def test_runtime_manager_context_packet_preserves_phase_a_meal_thread_candidates() -> None:
    context = _context().model_copy(
        update={
            "candidate_attachment_targets": [
                {
                    "target_object_type": "pending_followup",
                    "target_object_id": "pending-1",
                    "source": "pending_followup",
                    "pending_question": "which meal?",
                    "mutation_authority": False,
                },
                {
                    "target_object_type": "meal_thread",
                    "target_object_id": "lunch-thread",
                    "meal_thread_id": "lunch-thread",
                    "meal_version_id": "lunch-version",
                    "display_name": "lunch rice",
                    "source": "active_meal_view",
                    "confidence": "medium",
                    "mutation_authority": False,
                },
                {
                    "target_object_type": "meal_thread",
                    "target_object_id": "breakfast-thread",
                    "meal_thread_id": "breakfast-thread",
                    "meal_version_id": "breakfast-version",
                    "display_name": "breakfast teppan set",
                    "source": "recent_committed_meal",
                    "confidence": "medium",
                    "mutation_authority": False,
                },
            ],
            "recent_item_targets": [
                {
                    "target_object_type": "meal_item_candidate",
                    "target_object_id": "egg-item",
                    "meal_item_id": "egg-item",
                    "meal_thread_id": "breakfast-thread",
                    "meal_version_id": "breakfast-version",
                    "canonical_name": "egg",
                    "source": "recent_committed_meal",
                    "mutation_authority": False,
                }
            ],
        }
    )

    packet = build_runtime_manager_context_packet_v1(
        db=None,
        current_turn_context=context,
        user_external_id="context-user",
        local_date="2026-05-04",
        session_id="session-1",
    )

    candidates = packet["target_candidates"]["for_correction_or_removal"]
    assert all(candidate["target_object_type"] != "pending_followup" for candidate in candidates)
    meal_threads = [
        candidate for candidate in candidates if candidate["target_object_type"] == "meal_thread"
    ]
    assert [candidate["display_name"] for candidate in meal_threads] == [
        "lunch rice",
        "breakfast teppan set",
    ]
    assert [candidate["meal_thread_id"] for candidate in meal_threads] == [
        "lunch-thread",
        "breakfast-thread",
    ]
    assert [candidate["target_display_name"] for candidate in meal_threads] == [
        "lunch rice",
        "breakfast teppan set",
    ]
    assert candidates[2]["target_object_type"] == "meal_item_candidate"
    assert candidates[2]["canonical_name"] == "egg"
    assert all(candidate["read_only"] is True for candidate in candidates)
    assert all(candidate["mutation_authority"] is False for candidate in candidates)


def test_runtime_manager_context_packet_hides_llm_only_active_meal_macros() -> None:
    engine, db = _session()
    try:
        user = get_or_create_user(db, "context-user")
        thread = MealThreadRecord(user_id=user.id, title="breakfast shop teppan set", active_version_id=None)
        db.add(thread)
        db.commit()
        db.refresh(thread)
        version = MealVersionRecord(
            meal_thread_id=thread.id,
            version_status="active",
            version_reason="new_intake",
            resolution_status="completed_meal",
            meal_title="breakfast shop teppan set",
            raw_input="breakfast shop teppan set",
            local_date="2026-05-04",
            source_request_id="turn-breakfast",
            total_kcal=400,
            protein_g=18,
            carb_g=42,
            fat_g=12,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        thread.active_version_id = version.id
        db.add_all(
            [
                thread,
                MealItemRecord(
                    meal_version_id=version.id,
                    item_index=0,
                    name="breakfast shop teppan set",
                    source="llm",
                    evidence_role="none",
                    estimate_basis="llm_only",
                    confidence_tier="low",
                    estimated_kcal=400,
                    protein_g=18,
                    carb_g=42,
                    fat_g=12,
                    evidence_ids_json=[],
                ),
            ]
        )
        db.commit()

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

    basis = packet["active_day_state"]["active_meal_estimate_basis"]
    assert basis["macro_summary"] == {
        "protein_g": None,
        "carb_g": None,
        "fat_g": None,
        "macro_visibility_status": "hidden_missing_source",
        "macro_guard_reason": "unsupported_macro_source",
    }
    assert basis["items"][0]["protein_g"] is None
    assert basis["items"][0]["carb_g"] is None
    assert basis["items"][0]["fat_g"] is None
    assert basis["items"][0]["source"] == "unverified_estimate"
    assert basis["items"][0]["estimate_basis"] == "rough_estimate_without_source"
    assert basis["items"][0]["macro_visibility_status"] == "hidden_missing_source"


def test_runtime_manager_context_packet_separates_context_evidence_readonly_from_turn_mutability() -> None:
    engine, db = _session()
    try:
        get_or_create_user(db, "context-user")
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
    current_turn = packet["current_turn"]
    assert current_turn["context_evidence_read_only"] is True
    assert current_turn["user_utterance_may_request_mutation"] is True
    assert current_turn["semantic_owner"] == "manager_llm"
    assert current_turn["read_only"] is True
    assert current_turn["mutation_authority"] is False
    assert current_turn["read_only_scope"] == "context_packet_evidence"
    assert current_turn["mutation_authority_scope"] == "context_packet_not_product_action"
