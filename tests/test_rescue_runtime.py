from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.rescue_overlay import RescueOverlayTargetDay
from app.application.rescue_runtime import (
    RescueAssessmentResult,
    RescueRuntimeInputs,
    RescueTriggerResult,
    build_rescue_runtime_artifact,
    persist_rescue_runtime_artifact,
)
from app.models import Base, ProposalContainerRecord, ProposalOptionRecord, User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _user(db: Session) -> User:
    user = User(user_id="rescue-user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _runtime_inputs(
    *,
    triggered: bool = True,
    rescue_needed: bool = True,
    rescue_horizon: int | None = 3,
    recovery_viability: str = "viable",
    recommended_rescue_family: str = "short_horizon_spread",
    target_recovery_kcal: int = 450,
    safety_floor_kcal: int = 1500,
    activation_reference_hour_24: int | None = 9,
) -> RescueRuntimeInputs:
    return RescueRuntimeInputs(
        trigger_result=RescueTriggerResult(
            triggered=triggered,
            trigger_reason="daily overshoot exceeded soft threshold",
            overshoot_kcal=target_recovery_kcal,
            current_local_date="2026-04-15",
            relevant_ledger_summary={"effective_budget_kcal": 1800, "consumed_kcal": 2250},
        ),
        assessment_result=RescueAssessmentResult(
            rescue_needed=rescue_needed,
            rescue_horizon=rescue_horizon,
            recovery_viability=recovery_viability,  # type: ignore[arg-type]
            recommended_rescue_family=recommended_rescue_family,  # type: ignore[arg-type]
            compression_summary={"horizon_days": rescue_horizon, "overshoot_kcal": target_recovery_kcal},
            escalation_risk="medium" if recovery_viability == "strained" else "low",
            assessment_confidence="high",
        ),
        target_recovery_kcal=target_recovery_kcal,
        target_days=(
            RescueOverlayTargetDay(local_date="2026-04-15", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-16", base_budget_kcal=1800),
            RescueOverlayTargetDay(local_date="2026-04-17", base_budget_kcal=1800),
        ),
        safety_floor_kcal=safety_floor_kcal,
        activation_reference_hour_24=activation_reference_hour_24,
    )


def test_build_rescue_runtime_artifact_returns_no_rescue_when_trigger_is_false() -> None:
    artifact = build_rescue_runtime_artifact(
        _runtime_inputs(
            triggered=False,
            rescue_needed=False,
            rescue_horizon=None,
            recommended_rescue_family="no_rescue",
            target_recovery_kcal=0,
        )
    )

    assert artifact.no_rescue is True
    assert artifact.rescue_result.proposal_posture == "no_rescue"
    assert artifact.rescue_assessment_packet.rescue_needed is False
    assert artifact.rescue_assessment_packet.allowed_rescue_families == ()


def test_build_rescue_runtime_artifact_integrates_assessment_packet_with_ranked_proposal() -> None:
    artifact = build_rescue_runtime_artifact(_runtime_inputs())

    assert artifact.no_rescue is False
    assert artifact.rescue_result.proposal_posture == "proposal"
    assert artifact.rescue_assessment_packet.recommended_rescue_family == "short_horizon_spread"
    assert artifact.rescue_assessment_packet.allowed_rescue_families == artifact.rescue_result.allowed_rescue_families
    assert artifact.rescue_result.top_option is not None
    assert artifact.rescue_result.top_option.option_family == "short_horizon_spread"
    assert artifact.rescue_result.top_option.activation_mode == "today_lunch"
    assert artifact.rescue_assessment_packet.target_recovery_kcal == 450
    assert artifact.rescue_assessment_packet.overshoot_summary["overshoot_kcal"] == 450


def test_build_rescue_runtime_artifact_keeps_stop_and_escalate_for_non_viable_assessment() -> None:
    artifact = build_rescue_runtime_artifact(
        _runtime_inputs(
            recovery_viability="non_viable",
            recommended_rescue_family="rescue_stop_and_escalate",
            target_recovery_kcal=240,
        )
    )

    assert artifact.rescue_result.proposal_posture == "rescue_stop_and_escalate"
    assert artifact.rescue_assessment_packet.recommended_rescue_family == "rescue_stop_and_escalate"
    assert artifact.rescue_result.top_option is not None
    assert artifact.rescue_result.top_option.option_family == "rescue_stop_and_escalate"
    assert artifact.rescue_result.top_option.effect_type == "escalation"


def test_persist_rescue_runtime_artifact_creates_ranked_proposal_container() -> None:
    db = _session()
    user = _user(db)
    artifact = build_rescue_runtime_artifact(_runtime_inputs())

    persisted = persist_rescue_runtime_artifact(db, user=user, artifact=artifact)

    proposal = db.get(ProposalContainerRecord, persisted["proposal_container_id"])
    assert proposal is not None
    assert proposal.proposal_type == "rescue"
    assert proposal.top_option_id == persisted["top_option_id"]
    assert proposal.metadata_json["recommended_rescue_family"] == "short_horizon_spread"
    assert proposal.metadata_json["target_recovery_kcal"] == 450
    assert proposal.metadata_json["trigger_summary"]["triggered"] is True

    options = (
        db.query(ProposalOptionRecord)
        .filter(ProposalOptionRecord.proposal_container_id == proposal.id)
        .order_by(ProposalOptionRecord.rank_order.asc())
        .all()
    )
    assert len(options) == persisted["option_count"] == 2
    assert options[0].is_primary is True
    assert options[0].option_type == "short_horizon_spread"
    assert options[0].effect_payload_json["activation_mode"] == "today_lunch"
    assert options[0].effect_payload_json["daily_kcal_adjustments"] == [-150, -150, -150]
    assert options[1].option_type == "same_day_soft_cap"
