from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.rescue.application import build_open_rescue_proposals_view
from app.rescue.application import RescueOverlayTargetDay
from app.rescue.application.response import (
    apply_rescue_plan_action,
    build_rescue_response_result,
    should_surface_rescue_response,
)
from app.rescue.application.runtime import (
    RescueAssessmentResult,
    RescueRuntimeInputs,
    RescueTriggerResult,
    build_rescue_runtime_artifact,
    persist_rescue_runtime_artifact,
)
from app.models import Base, ProposalContainerRecord, User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _user(db: Session, user_id: str = "rescue-response-user") -> User:
    user = User(user_id=user_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _runtime_inputs(*, overshoot_kcal: int = 450) -> RescueRuntimeInputs:
    return RescueRuntimeInputs(
        trigger_result=RescueTriggerResult(
            triggered=True,
            trigger_reason="daily overshoot exceeded soft threshold",
            overshoot_kcal=overshoot_kcal,
            current_local_date="2026-04-15",
            relevant_ledger_summary={"effective_budget_kcal": 1800, "consumed_kcal": 2250},
        ),
        assessment_result=RescueAssessmentResult(
            rescue_needed=True,
            rescue_horizon=3,
            recovery_viability="viable",
            recommended_rescue_family="short_horizon_spread",
            compression_summary={"horizon_days": 3, "overshoot_kcal": overshoot_kcal},
            escalation_risk="low",
            assessment_confidence="high",
        ),
        target_recovery_kcal=overshoot_kcal,
        target_days=(
            RescueOverlayTargetDay(local_date="2026-04-15", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-16", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-17", base_budget_kcal=1800),
        ),
        safety_floor_kcal=1500,
        activation_reference_hour_24=9,
    )


def _open_rescue_proposal(db: Session) -> tuple[User, object]:
    user = _user(db)
    artifact = build_rescue_runtime_artifact(_runtime_inputs())
    persist_rescue_runtime_artifact(db, user=user, artifact=artifact)
    proposals = build_open_rescue_proposals_view(db, user_id=user.id)
    return user, proposals[0]


def test_should_surface_rescue_response_only_for_open_like_rescue_proposal() -> None:
    db = _session()
    user, proposal = _open_rescue_proposal(db)

    assert should_surface_rescue_response(proposal=proposal, source="proactive") is True
    assert should_surface_rescue_response(proposal=proposal, source="reactive_explicit_rescue_request") is True

    proposal_record = db.get(ProposalContainerRecord, proposal.proposal_container_id)
    assert proposal_record is not None
    proposal_record.proposal_status = "accepted"
    db.commit()

    closed_proposal = build_open_rescue_proposals_view(db, user_id=user.id)
    assert closed_proposal == []


def test_build_rescue_response_result_returns_single_plan_chat_surface() -> None:
    db = _session()
    _, proposal = _open_rescue_proposal(db)

    result = build_rescue_response_result(
        proposal=proposal,
        source="proactive",
    )

    assert result.surfaced is True
    assert result.recommended_days == 2
    assert result.daily_kcal_adjustment == 225
    assert result.overshoot_kcal == 450
    assert result.backup_options == []
    assert "450 kcal" in result.reply_text
    assert "2 天" in result.reply_text
    assert result.ui_hints["delivery"] == "chat_only"
    assert result.ui_hints["ui_role"] == "proposal_inbox_mirror"
    assert [action["action"] for action in result.quick_actions] == [
        "accept_rescue_plan",
        "shorten_rescue_plan",
        "extend_rescue_plan",
        "defer_rescue_plan",
        "reject_rescue_plan",
        "explain_rescue_plan",
    ]


def test_shorten_rescue_plan_uses_aggressive_cap_when_possible() -> None:
    db = _session()
    _, proposal = _open_rescue_proposal(db)

    result = apply_rescue_plan_action(
        proposal=proposal,
        action="shorten_rescue_plan",
    )

    assert result.recommended_days == 2
    assert result.daily_kcal_adjustment == 225
    assert result.ui_hints["intensity"] == "normal"
    assert "最短方案" in result.reply_text


def test_extend_rescue_plan_makes_plan_more_gradual() -> None:
    db = _session()
    _, proposal = _open_rescue_proposal(db)

    result = apply_rescue_plan_action(
        proposal=proposal,
        action="extend_rescue_plan",
    )

    assert result.recommended_days == 3
    assert result.daily_kcal_adjustment == 150
    assert "3 天" in result.reply_text


def test_defer_reject_and_explain_actions_stay_in_chat() -> None:
    db = _session()
    _, proposal = _open_rescue_proposal(db)

    defer = apply_rescue_plan_action(proposal=proposal, action="defer_rescue_plan")
    reject = apply_rescue_plan_action(proposal=proposal, action="reject_rescue_plan")
    explain = apply_rescue_plan_action(proposal=proposal, action="explain_rescue_plan")

    assert defer.ui_hints["mode"] == "rescue_deferred_pending_reminder"
    assert "12 小時" in defer.reply_text
    assert reject.ui_hints["mode"] == "rescue_reject_reason_request"
    assert reject.ui_hints["reason_surface"] == "chat_only"
    assert "為什麼不要這次" in reject.reply_text
    assert "15%" in explain.reply_text
