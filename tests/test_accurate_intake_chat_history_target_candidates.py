from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.composition.accurate_intake_debug_routes import build_accurate_intake_chat_history_payload
from app.database import get_or_create_user
from app.models import Base
from app.shared.infra.models import MessageBuffer


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_chat_history_surfaces_target_candidates_as_read_only_backend_fields() -> None:
    db = _session()
    user = get_or_create_user(db, "chat-history-target-candidates")
    db.add(
        MessageBuffer(
            user_id=user.id,
            role="assistant",
            content="Which item should I update?",
            trace_id="target-candidate-trace",
            trace_json={
                "runtime_turn_trace": {
                    "local_date": "2026-05-05",
                    "context_policy_version": "accurate_intake_mvp_context_policy_v1",
                    "loaded_context_summary": {
                        "target_candidate_count": 2,
                        "pending_followup_present": False,
                    },
                    "omitted_context_summary": {
                        "policy_excluded_context_ids": ["raw_trace_dump", "long_term_memory"]
                    },
                    "manager_context_packet_v1": {
                        "hard_pins": {},
                        "target_candidates": {
                            "mutation_authority": False,
                            "for_correction_or_removal": [
                                {
                                    "target_object_type": "meal_thread",
                                    "target_object_id": "51",
                                    "display_name": "luwei",
                                    "source": "recent_committed_meal",
                                    "confidence": "medium",
                                },
                                {
                                    "target_object_type": "meal_thread",
                                    "target_object_id": "77",
                                    "display_name": "milk tea",
                                    "source": "recent_committed_meal",
                                    "confidence": "medium",
                                },
                            ],
                        },
                    },
                }
            },
        )
    )
    db.commit()

    payload = build_accurate_intake_chat_history_payload(
        db,
        user_external_id="chat-history-target-candidates",
        local_date="2026-05-05",
    )

    message = payload["messages"][0]
    assert message["target_candidate_count"] == 2
    assert message["target_candidates"] == [
        {
            "target_object_type": "meal_thread",
            "target_object_id": "51",
            "display_name": "luwei",
            "source": "recent_committed_meal",
            "confidence": "medium",
            "read_only": True,
            "mutation_authority": False,
            "selected_target": False,
        },
        {
            "target_object_type": "meal_thread",
            "target_object_id": "77",
            "display_name": "milk tea",
            "source": "recent_committed_meal",
            "confidence": "medium",
            "read_only": True,
            "mutation_authority": False,
            "selected_target": False,
        },
    ]
    assert payload["frontend_semantic_owner"] is False
