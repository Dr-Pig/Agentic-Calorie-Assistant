from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("rescue.domain.shadow_options")

RescueOptionType = Literal[
    "informational_only",
    "same_day_soft_adjustment",
    "next_day_soft_adjustment",
    "multi_day_spread_candidate",
    "ask_user_context_first",
    "no_rescue_needed",
]
RescueOptionRiskIfWrong = Literal["low", "medium", "high"]


class RescueOptionBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RescueOptionCandidate(RescueOptionBaseModel):
    option_id: str
    option_type: RescueOptionType
    affected_dates: tuple[date, ...]
    suggested_adjustment_kcal_range: tuple[int, int]
    rationale: str
    risk_if_wrong: RescueOptionRiskIfWrong
    user_confirmation_required_later: Literal[True] = True
    runtime_effect_allowed: Literal[False] = False

    @field_validator("suggested_adjustment_kcal_range")
    @classmethod
    def validate_adjustment_range(cls, value: tuple[int, int]) -> tuple[int, int]:
        lower, upper = value
        if lower < 0 or upper < 0:
            raise ValueError("suggested_adjustment_kcal_range must be non-negative")
        if lower > upper:
            raise ValueError("suggested_adjustment_kcal_range lower bound must not exceed upper")
        return value


class RescueOptionRejection(RescueOptionBaseModel):
    reason_code: str
    rationale: str
    rejected_option_type: RescueOptionType | None = None


class RescueOptionPacket(RescueOptionBaseModel):
    """Offline shadow option artifact with no proposal or runtime authority."""

    artifact_type: Literal["rescue_option_packet"] = "rescue_option_packet"
    track: Literal["RescueShadow"] = "RescueShadow"
    slice_id: Literal["rs4_option_candidate_generator"] = (
        "rs4_option_candidate_generator"
    )
    shadow_mode: Literal[True] = True
    shadow_review_only: Literal[True] = True
    real_runtime_effect: Literal[False] = False
    runtime_effect_allowed: Literal[False] = False
    proposal_authority: Literal[False] = False
    option_candidates: tuple[RescueOptionCandidate, ...] = Field(default_factory=tuple)
    options_rejected: tuple[RescueOptionRejection, ...] = Field(default_factory=tuple)
    selected_shadow_option_id: str | None = None
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    rescue_committed: Literal[False] = False
    proposal_committed: Literal[False] = False
    day_budget_mutated: Literal[False] = False
    body_plan_mutated: Literal[False] = False
    meal_thread_mutated: Literal[False] = False
    durable_memory_written: Literal[False] = False
    manager_context_injected: Literal[False] = False
    proactive_sent: Literal[False] = False
    recommendation_served: Literal[False] = False
    live_provider_used: Literal[False] = False
    future_budget_overlay_created: Literal[False] = False
    product_readiness_claimed: Literal[False] = False
    private_self_use_approved: Literal[False] = False

    @model_validator(mode="after")
    def validate_selected_option(self) -> RescueOptionPacket:
        if self.selected_shadow_option_id is None:
            return self
        candidate_ids = {option.option_id for option in self.option_candidates}
        if self.selected_shadow_option_id not in candidate_ids:
            raise ValueError("selected_shadow_option_id must reference an option candidate")
        return self


__all__ = [
    "RescueOptionCandidate",
    "RescueOptionPacket",
    "RescueOptionRejection",
    "RescueOptionRiskIfWrong",
    "RescueOptionType",
    "SIDECAR_ACTIVATION_CONTRACT",
]
