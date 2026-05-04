from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("rescue.domain.shadow_viability")

RescueViabilityBand = Literal["not_needed", "low", "medium", "high"]
RescueViabilityShadowReviewPosture = Literal[
    "discard",
    "keep_shadowing",
    "ask_user",
    "promote_later",
]
RescueViabilityHarmIfWrong = Literal["low", "medium", "high"]


class RescueViabilityScoreResult(BaseModel):
    """Offline shadow-review artifact, not product readiness or runtime authority.

    ``shadow_review_posture`` is a shadow review posture only. It is not runtime,
    proposal, recommendation, or mutation disposition.
    """

    model_config = ConfigDict(extra="forbid")

    shadow_review_only: Literal[True] = True
    runtime_effect_allowed: Literal[False] = False
    proposal_authority: Literal[False] = False
    rescue_viability_score: float = Field(ge=0.0, le=1.0)
    viability_band: RescueViabilityBand
    reason_codes: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    harm_if_wrong: RescueViabilityHarmIfWrong
    shadow_review_posture: RescueViabilityShadowReviewPosture


__all__ = [
    "RescueViabilityBand",
    "RescueViabilityHarmIfWrong",
    "RescueViabilityScoreResult",
    "RescueViabilityShadowReviewPosture",
    "SIDECAR_ACTIVATION_CONTRACT",
]
