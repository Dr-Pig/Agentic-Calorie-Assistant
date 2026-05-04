from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("rescue.domain.shadow_trigger")

RescueTriggerCandidate = Literal[
    "today_overshoot",
    "weekly_overshoot",
    "repeated_overshoot_pattern",
    "budget_remaining_too_low_for_day_part",
    "accepted_calibration_recently",
    "low_adherence_recently",
    "no_rescue_needed",
]

RescueTriggerStrength = Literal["none", "low", "medium", "high"]

NoRescueCandidateReason = Literal[
    "no_trigger",
    "informational_only",
    "no_active_budget_or_body_plan",
    "open_proposal_exists",
]


class RescueTriggerDetectionResult(BaseModel):
    """Offline trigger preflight output, not runtime activation authority."""

    model_config = ConfigDict(extra="forbid")

    trigger_candidate: RescueTriggerCandidate
    trigger_reason_codes: list[str]
    trigger_strength: RescueTriggerStrength
    should_generate_rescue_candidate: bool
    why_no_rescue_candidate: NoRescueCandidateReason | None = None


__all__ = [
    "NoRescueCandidateReason",
    "RescueTriggerCandidate",
    "RescueTriggerDetectionResult",
    "RescueTriggerStrength",
    "SIDECAR_ACTIVATION_CONTRACT",
]
