from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.rescue.application import build_open_rescue_proposals_view
from app.rescue.application.runtime import (
    RescueAssessmentResult,
    RescueRuntimeInputs,
    RescueTriggerResult,
    build_rescue_runtime_artifact,
    persist_rescue_runtime_artifact,
)
from app.rescue.application import RescueOverlayTargetDay
from app.models import Base, ProposalContainerRecord, User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _user(db: Session, user_id: str = "proposal-read-user") -> User:
    user = User(user_id=user_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _runtime_inputs(*, target_recovery_kcal: int = 450) -> RescueRuntimeInputs:
    return RescueRuntimeInputs(
        trigger_result=RescueTriggerResult(
            triggered=True,
            trigger_reason="daily overshoot exceeded soft threshold",
            overshoot_kcal=target_recovery_kcal,
            current_local_date="2026-04-15",
            relevant_ledger_summary={"effective_budget_kcal": 1800, "consumed_kcal": 2250},
        ),
        assessment_result=RescueAssessmentResult(
            rescue_needed=True,
            rescue_horizon=3,
            recovery_viability="viable",
            recommended_rescue_family="short_horizon_spread",
            compression_summary={"horizon_days": 3, "overshoot_kcal": target_recovery_kcal},
            escalation_risk="low",
            assessment_confidence="high",
        ),
        target_recovery_kcal=target_recovery_kcal,
        target_days=(
            RescueOverlayTargetDay(local_date="2026-04-15", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-16", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-17", base_budget_kcal=1800),
        ),
        safety_floor_kcal=1500,
        activation_reference_hour_24=9,
    )


def test_build_open_rescue_proposals_view_reads_open_rescue_proposal_with_top_option() -> None:
    db = _session()
    user = _user(db)
    artifact = build_rescue_runtime_artifact(_runtime_inputs())
    persist_rescue_runtime_artifact(db, user=user, artifact=artifact)

    proposals = build_open_rescue_proposals_view(db, user_id=user.id)

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proposal_type == "rescue"
    assert proposal.proposal_status == "open"
    assert proposal.top_option_id is not None
    assert proposal.metadata["recommended_rescue_family"] == "short_horizon_spread"
    assert len(proposal.options) == 2
    assert proposal.options[0].is_primary is True
    assert proposal.options[0].option_type == "short_horizon_spread"
    assert proposal.options[0].effect_payload["activation_mode"] == "today_lunch"


def test_build_open_rescue_proposals_view_excludes_non_rescue_or_non_open_proposals() -> None:
    db = _session()
    user = _user(db, user_id="proposal-read-user-2")
    artifact = build_rescue_runtime_artifact(_runtime_inputs(target_recovery_kcal=300))
    persisted = persist_rescue_runtime_artifact(db, user=user, artifact=artifact)

    proposal = db.get(ProposalContainerRecord, persisted["proposal_container_id"])
    assert proposal is not None
    proposal.proposal_status = "accepted"
    db.commit()

    proposals = build_open_rescue_proposals_view(db, user_id=user.id)

    assert proposals == []


def test_build_open_rescue_proposals_view_keeps_deferred_pending_rescue_proposals() -> None:
    db = _session()
    user = _user(db, user_id="proposal-read-user-3")
    artifact = build_rescue_runtime_artifact(_runtime_inputs(target_recovery_kcal=300))
    persisted = persist_rescue_runtime_artifact(db, user=user, artifact=artifact)

    proposal = db.get(ProposalContainerRecord, persisted["proposal_container_id"])
    assert proposal is not None
    proposal.proposal_status = "deferred_pending_reminder"
    proposal.metadata_json = {
        **dict(proposal.metadata_json or {}),
        "next_reminder_at": "2026-04-15T21:00:00",
        "reason_bridge": {
            "raw_reason_text": "我今天先不要，晚一點再說。",
            "reason_hint": "not_now",
            "reason_source": "defer",
            "captured_at": "2026-04-15T09:00:00",
        },
    }
    db.commit()

    proposals = build_open_rescue_proposals_view(db, user_id=user.id)

    assert len(proposals) == 1
    assert proposals[0].proposal_status == "deferred_pending_reminder"
    assert proposals[0].metadata["next_reminder_at"] == "2026-04-15T21:00:00"
    assert proposals[0].metadata["reason_bridge"]["reason_hint"] == "not_now"
