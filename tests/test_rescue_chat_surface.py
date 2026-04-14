from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.open_proposals_read_model import build_open_rescue_proposals_view
from app.application.rescue_chat_surface import apply_rescue_chat_action, build_rescue_chat_surface
from app.application.rescue_overlay import RescueOverlayTargetDay
from app.application.rescue_runtime import (
    RescueAssessmentResult,
    RescueRuntimeInputs,
    RescueTriggerResult,
    build_rescue_runtime_artifact,
    persist_rescue_runtime_artifact,
)
from app.models import Base, LedgerEntryRecord, ProposalContainerRecord, User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _user(db: Session, user_id: str = "rescue-chat-user") -> User:
    user = User(user_id=user_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_open_rescue_proposal(db: Session) -> User:
    user = _user(db)
    artifact = build_rescue_runtime_artifact(
        RescueRuntimeInputs(
            trigger_result=RescueTriggerResult(
                triggered=True,
                trigger_reason="daily overshoot exceeded soft threshold",
                overshoot_kcal=450,
                current_local_date="2026-04-15",
                relevant_ledger_summary={"effective_budget_kcal": 1800, "consumed_kcal": 2250},
            ),
            assessment_result=RescueAssessmentResult(
                rescue_needed=True,
                rescue_horizon=3,
                recovery_viability="viable",
                recommended_rescue_family="short_horizon_spread",
                compression_summary={"horizon_days": 3, "overshoot_kcal": 450},
                escalation_risk="low",
                assessment_confidence="high",
            ),
            target_recovery_kcal=450,
            target_days=(
                RescueOverlayTargetDay(local_date="2026-04-15", base_budget_kcal=1800),
                RescueOverlayTargetDay(local_date="2026-04-16", base_budget_kcal=1800),
                RescueOverlayTargetDay(local_date="2026-04-17", base_budget_kcal=1800),
            ),
            safety_floor_kcal=1500,
            activation_reference_hour_24=9,
        )
    )
    persist_rescue_runtime_artifact(db, user=user, artifact=artifact)
    return user


def test_build_rescue_chat_surface_supports_proactive_and_reactive_modes() -> None:
    db = _session()
    user = _seed_open_rescue_proposal(db)

    proactive = build_rescue_chat_surface(db, user_id=user.id, mode="proactive")
    reactive = build_rescue_chat_surface(db, user_id=user.id, mode="reactive_explicit_rescue_request")

    assert proactive.surfaced is True
    assert reactive.surfaced is True
    assert proactive.response.ui_hints["delivery"] == "chat_only"
    assert reactive.response.ui_hints["delivery"] == "chat_only"
    assert proactive.proposal_container_id is not None
    assert reactive.proposal_container_id == proactive.proposal_container_id


def test_accept_action_marks_proposal_accepted_and_applies_overlay_entries() -> None:
    db = _session()
    user = _seed_open_rescue_proposal(db)

    result = apply_rescue_chat_action(db, user_id=user.id, action="accept_rescue_plan")

    proposal = db.get(ProposalContainerRecord, result.proposal_container_id)
    assert proposal is not None
    assert proposal.proposal_status == "accepted"
    assert proposal.accepted_at is not None
    assert result.response.ui_hints["mode"] == "rescue_accept_applied"
    assert result.writeback is not None
    assert result.writeback["status"] == "applied"
    assert len(result.writeback["entry_ids"]) == 3
    assert build_open_rescue_proposals_view(db, user_id=user.id) == []

    entries = db.execute(
        select(LedgerEntryRecord)
        .where(LedgerEntryRecord.source_type == "rescue_proposal_accept", LedgerEntryRecord.source_id == proposal.id)
        .order_by(LedgerEntryRecord.local_date.asc())
    ).scalars().all()
    assert len(entries) == 3
    assert [entry.delta_kcal for entry in entries] == [-150, -150, -150]


def test_second_accept_after_close_returns_no_open_proposal_without_duplicate_writeback() -> None:
    db = _session()
    user = _seed_open_rescue_proposal(db)

    first = apply_rescue_chat_action(db, user_id=user.id, action="accept_rescue_plan")
    second = apply_rescue_chat_action(db, user_id=user.id, action="accept_rescue_plan")

    assert first.writeback is not None
    assert first.writeback["status"] == "applied"
    assert second.surfaced is False
    assert second.response.ui_hints["mode"] == "no_open_rescue_proposal"

    entries = db.execute(
        select(LedgerEntryRecord)
        .where(LedgerEntryRecord.source_type == "rescue_proposal_accept")
        .order_by(LedgerEntryRecord.id.asc())
    ).scalars().all()
    assert len(entries) == 3


def test_reject_action_without_reason_requests_reason_but_keeps_open() -> None:
    db = _session()
    user = _seed_open_rescue_proposal(db)

    result = apply_rescue_chat_action(db, user_id=user.id, action="reject_rescue_plan")

    proposal = db.get(ProposalContainerRecord, result.proposal_container_id)
    assert proposal is not None
    assert proposal.proposal_status == "open"
    assert result.response.ui_hints["mode"] == "rescue_reject_reason_request"


def test_reject_action_with_reason_marks_proposal_rejected() -> None:
    db = _session()
    user = _seed_open_rescue_proposal(db)

    result = apply_rescue_chat_action(
        db,
        user_id=user.id,
        action="reject_rescue_plan",
        reject_reason="我這幾天行程不固定，現在不想套這個節奏。",
    )

    proposal = db.get(ProposalContainerRecord, result.proposal_container_id)
    assert proposal is not None
    assert proposal.proposal_status == "rejected"
    assert proposal.metadata_json["rejected_reason"] == "我這幾天行程不固定，現在不想套這個節奏。"
    assert result.response.ui_hints["mode"] == "rescue_proposal_closed"
