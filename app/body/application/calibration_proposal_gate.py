from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .calibration_model import CalibrationConfidence, CalibrationModelResult, CalibrationPosture

CalibrationProposalOptionFamily = Literal[
    "monitor_only",
    "logging_quality_first",
    "budget_adjustment",
    "pace_adjustment",
    "plan_reset",
]

CurrentBudgetStatus = Literal["on_track", "tight", "over_budget", "unknown"]
BodyPlanStatus = Literal["active", "inactive", "unknown"]
RecoveryViability = Literal["viable", "strained", "non_viable", "unknown"]

ALL_OPTION_FAMILIES: tuple[CalibrationProposalOptionFamily, ...] = (
    "monitor_only",
    "logging_quality_first",
    "budget_adjustment",
    "pace_adjustment",
    "plan_reset",
)

_CONFIDENCE_ORDER: dict[CalibrationConfidence, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
}


@dataclass(frozen=True)
class CalibrationProposalGateInputs:
    calibration_result: CalibrationModelResult
    current_budget_status: CurrentBudgetStatus = "unknown"
    active_body_plan_status: BodyPlanStatus = "unknown"
    rescue_recovery_viability: RecoveryViability = "unknown"
    recent_similar_proposal_open: bool = False
    proposal_cooldown_active: bool = False
    proposal_cooldown_reason: str | None = None


@dataclass(frozen=True)
class CalibrationProposalGateResult:
    decision_mode: Literal["deterministic"] = "deterministic"
    decision_reason: str = "deterministic proposal eligibility gate over calibration posture and active plan summaries"
    proposal_eligibility: bool = False
    allowed_option_families: tuple[CalibrationProposalOptionFamily, ...] = ()
    blocked_option_families: tuple[CalibrationProposalOptionFamily, ...] = ALL_OPTION_FAMILIES
    primary_policy_posture: CalibrationPosture = "insufficient_data"
    calibration_confidence: CalibrationConfidence = "low"
    gate_rationale: tuple[str, ...] = ()


def _confidence_rank(confidence: CalibrationConfidence) -> int:
    return _CONFIDENCE_ORDER[confidence]


def _filter_blocked(allowed: tuple[CalibrationProposalOptionFamily, ...]) -> tuple[CalibrationProposalOptionFamily, ...]:
    allowed_set = set(allowed)
    return tuple(family for family in ALL_OPTION_FAMILIES if family not in allowed_set)


def _should_block_entire_flow(inputs: CalibrationProposalGateInputs) -> tuple[bool, tuple[str, ...]]:
    calibration = inputs.calibration_result
    reasons: list[str] = []

    if _confidence_rank(calibration.calibration_confidence) < _confidence_rank("medium"):
        reasons.append(f"calibration confidence {calibration.calibration_confidence} is below the proposal threshold")

    if not calibration.proposal_eligibility:
        reasons.append(f"upstream calibration posture {calibration.calibration_posture} does not enter proposal flow")

    if calibration.calibration_posture in {"insufficient_data", "logging_quality_first", "monitor_only"}:
        reasons.append(f"calibration posture {calibration.calibration_posture} is blocked from proposal flow")

    if inputs.current_budget_status == "unknown":
        reasons.append("current budget summary is unknown")

    if inputs.active_body_plan_status != "active":
        reasons.append(f"active body plan status is {inputs.active_body_plan_status}")

    if inputs.recent_similar_proposal_open:
        reasons.append("a similar calibration proposal is still open")

    if inputs.proposal_cooldown_active:
        reasons.append(inputs.proposal_cooldown_reason or "proposal cooldown is active")

    return bool(reasons), tuple(reasons)


def _build_allowed_option_families(inputs: CalibrationProposalGateInputs) -> tuple[CalibrationProposalOptionFamily, ...]:
    calibration = inputs.calibration_result
    allowed: list[CalibrationProposalOptionFamily] = []

    if calibration.calibration_posture == "calibration_candidate":
        allowed.append("budget_adjustment")
        return tuple(allowed)

    if calibration.calibration_posture == "high_confidence_mismatch":
        allowed.append("budget_adjustment")
        if calibration.mismatch_attribution in {"likely_expenditure_shift", "mixed_uncertainty"}:
            allowed.append("pace_adjustment")
        if inputs.rescue_recovery_viability == "non_viable":
            allowed.append("plan_reset")
        return tuple(allowed)

    return tuple()


def build_calibration_proposal_gate(
    inputs: CalibrationProposalGateInputs,
) -> CalibrationProposalGateResult:
    blocked_flow, gate_rationale = _should_block_entire_flow(inputs)
    if blocked_flow:
        return CalibrationProposalGateResult(
            proposal_eligibility=False,
            allowed_option_families=tuple(),
            blocked_option_families=ALL_OPTION_FAMILIES,
            primary_policy_posture=inputs.calibration_result.calibration_posture,
            calibration_confidence=inputs.calibration_result.calibration_confidence,
            gate_rationale=gate_rationale,
        )

    allowed_option_families = _build_allowed_option_families(inputs)
    if not allowed_option_families:
        return CalibrationProposalGateResult(
            proposal_eligibility=False,
            allowed_option_families=tuple(),
            blocked_option_families=ALL_OPTION_FAMILIES,
            primary_policy_posture=inputs.calibration_result.calibration_posture,
            calibration_confidence=inputs.calibration_result.calibration_confidence,
            gate_rationale=gate_rationale + ("no proposal family is allowed under the current calibration posture",),
        )

    return CalibrationProposalGateResult(
        proposal_eligibility=True,
        allowed_option_families=allowed_option_families,
        blocked_option_families=_filter_blocked(allowed_option_families),
        primary_policy_posture=inputs.calibration_result.calibration_posture,
        calibration_confidence=inputs.calibration_result.calibration_confidence,
        gate_rationale=gate_rationale
        + (f"proposal flow allowed for {', '.join(allowed_option_families)}",),
    )
