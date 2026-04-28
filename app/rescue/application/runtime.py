from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Sequence

from sqlalchemy.orm import Session

from ...intake.application.canonical_quarantine_bridge import persist_proposal_artifact_skeleton
from .overlay import RescueOverlayTargetDay
from .proposal import (
    RescueProposalArtifact,
    RescueProposalFamily,
    RescueProposalInputs,
    RecoveryViability,
    build_rescue_proposal,
)
from ...models import User

AssessmentConfidence = Literal["low", "medium", "high"]
EscalationRisk = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class RescueTriggerResult:
    triggered: bool
    trigger_reason: str
    overshoot_kcal: int
    current_local_date: str
    relevant_ledger_summary: dict[str, Any]


@dataclass(frozen=True)
class RescueAssessmentResult:
    rescue_needed: bool
    rescue_horizon: int | None
    recovery_viability: RecoveryViability
    recommended_rescue_family: RescueProposalFamily
    compression_summary: dict[str, Any]
    escalation_risk: EscalationRisk = "low"
    assessment_confidence: AssessmentConfidence = "high"


@dataclass(frozen=True)
class RescueRuntimeInputs:
    trigger_result: RescueTriggerResult
    assessment_result: RescueAssessmentResult
    target_recovery_kcal: int
    target_days: Sequence[RescueOverlayTargetDay]
    safety_floor_kcal: int
    activation_reference_hour_24: int | None = None


@dataclass(frozen=True)
class RescueAssessmentPacket:
    trigger_summary: RescueTriggerResult
    overshoot_summary: dict[str, Any]
    rescue_needed: bool
    rescue_horizon: int | None
    recovery_viability: RecoveryViability
    recommended_rescue_family: RescueProposalFamily
    escalation_risk: EscalationRisk
    assessment_confidence: AssessmentConfidence
    safety_floor_kcal: int
    target_recovery_kcal: int
    allowed_rescue_families: tuple[RescueProposalFamily, ...]
    blocked_rescue_families: tuple[RescueProposalFamily, ...]
    compression_summary: dict[str, Any]


@dataclass(frozen=True)
class RescueRuntimeArtifact:
    rescue_assessment_packet: RescueAssessmentPacket
    rescue_result: RescueProposalArtifact
    no_rescue: bool = False


def _normalize_non_negative(value: int) -> int:
    return max(0, int(value))


def build_rescue_runtime_artifact(inputs: RescueRuntimeInputs) -> RescueRuntimeArtifact:
    rescue_horizon = inputs.assessment_result.rescue_horizon or 0
    target_recovery_kcal = _normalize_non_negative(inputs.target_recovery_kcal)
    safety_floor_kcal = _normalize_non_negative(inputs.safety_floor_kcal)
    rescue_needed = (
        inputs.trigger_result.triggered
        and inputs.assessment_result.rescue_needed
        and target_recovery_kcal > 0
    )

    proposal = build_rescue_proposal(
        RescueProposalInputs(
            rescue_needed=rescue_needed,
            recovery_viability=inputs.assessment_result.recovery_viability,
            rescue_horizon=rescue_horizon,
            target_recovery_kcal=target_recovery_kcal,
            target_days=tuple(inputs.target_days),
            safety_floor_kcal=safety_floor_kcal,
            activation_reference_hour_24=inputs.activation_reference_hour_24,
        )
    )

    packet = RescueAssessmentPacket(
        trigger_summary=inputs.trigger_result,
        overshoot_summary={
            "overshoot_kcal": inputs.trigger_result.overshoot_kcal,
            "current_local_date": inputs.trigger_result.current_local_date,
            "ledger_summary": inputs.trigger_result.relevant_ledger_summary,
        },
        rescue_needed=rescue_needed,
        rescue_horizon=inputs.assessment_result.rescue_horizon,
        recovery_viability=inputs.assessment_result.recovery_viability,
        recommended_rescue_family=proposal.recommended_rescue_family,
        escalation_risk=inputs.assessment_result.escalation_risk,
        assessment_confidence=inputs.assessment_result.assessment_confidence,
        safety_floor_kcal=safety_floor_kcal,
        target_recovery_kcal=target_recovery_kcal,
        allowed_rescue_families=proposal.allowed_rescue_families,
        blocked_rescue_families=proposal.blocked_rescue_families,
        compression_summary=inputs.assessment_result.compression_summary,
    )
    return RescueRuntimeArtifact(
        rescue_assessment_packet=packet,
        rescue_result=proposal,
        no_rescue=proposal.proposal_posture == "no_rescue",
    )


def persist_rescue_runtime_artifact(
    db: Session,
    *,
    user: User,
    artifact: RescueRuntimeArtifact,
) -> dict[str, int | None]:
    options = [
        {
            "option_type": option.option_family,
            "option_label": option.option_label,
            "option_summary": option.option_summary,
            "rank_order": option.rank_order,
            "is_primary": option.is_primary,
            "effect_payload_json": {
                **dict(option.effect_payload),
                "activation_mode": option.activation_mode,
                "horizon_days": option.horizon_days,
                "daily_kcal_adjustments": list(option.daily_kcal_adjustments),
                "confidence": option.confidence,
                "guardrail_summary": option.guardrail_summary,
            },
        }
        for option in artifact.rescue_result.option_payloads
    ]
    metadata = {
        "proposal_posture": artifact.rescue_result.proposal_posture,
        "rescue_needed": artifact.rescue_assessment_packet.rescue_needed,
        "rescue_horizon": artifact.rescue_assessment_packet.rescue_horizon,
        "recovery_viability": artifact.rescue_assessment_packet.recovery_viability,
        "recommended_rescue_family": artifact.rescue_assessment_packet.recommended_rescue_family,
        "escalation_risk": artifact.rescue_assessment_packet.escalation_risk,
        "assessment_confidence": artifact.rescue_assessment_packet.assessment_confidence,
        "target_recovery_kcal": artifact.rescue_assessment_packet.target_recovery_kcal,
        "safety_floor_kcal": artifact.rescue_assessment_packet.safety_floor_kcal,
        "compression_summary": artifact.rescue_assessment_packet.compression_summary,
        "allowed_rescue_families": list(artifact.rescue_assessment_packet.allowed_rescue_families),
        "blocked_rescue_families": list(artifact.rescue_assessment_packet.blocked_rescue_families),
        "trigger_summary": {
            "triggered": artifact.rescue_assessment_packet.trigger_summary.triggered,
            "trigger_reason": artifact.rescue_assessment_packet.trigger_summary.trigger_reason,
            "overshoot_kcal": artifact.rescue_assessment_packet.trigger_summary.overshoot_kcal,
            "current_local_date": artifact.rescue_assessment_packet.trigger_summary.current_local_date,
            "relevant_ledger_summary": artifact.rescue_assessment_packet.trigger_summary.relevant_ledger_summary,
        },
    }
    return persist_proposal_artifact_skeleton(
        db,
        user=user,
        proposal_type="rescue",
        options=options,
        metadata=metadata,
    )
