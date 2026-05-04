from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rescue.domain.shadow_options import (
    RescueOptionCandidate,
    RescueOptionRejection,
)
from app.rescue.domain.shadow_trigger import RescueTriggerCandidate
from app.rescue.domain.shadow_viability import (
    RescueViabilityBand,
    RescueViabilityHarmIfWrong,
    RescueViabilityShadowReviewPosture,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("rescue.domain.shadow_artifact")


class RescueShadowArtifactBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RescueShadowNoEffectFlags(RescueShadowArtifactBaseModel):
    shadow_mode: Literal[True] = True
    real_runtime_effect: Literal[False] = False
    runtime_effect_allowed: Literal[False] = False
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


class RescueShadowInputContextSummary(RescueShadowArtifactBaseModel):
    source: Literal["RescueContextFixture"] = "RescueContextFixture"
    user_id: str
    local_date: date
    timezone: str
    current_budget_active: bool
    daily_budget_kcal: int = Field(ge=0)
    consumed_kcal: int = Field(ge=0)
    remaining_kcal: int
    day_part: str
    active_body_plan_active: bool
    daily_target_kcal: int = Field(ge=0)
    safety_floor_kcal: int = Field(ge=0)
    meal_count_today: int = Field(ge=0)
    logging_coverage: float = Field(ge=0.0, le=1.0)
    weekly_deficit_gap_kcal: int
    weekly_deficit_posture: str
    calibration_posture: str
    calibration_confidence: float = Field(ge=0.0, le=1.0)
    calibration_recently_accepted: bool
    calibration_uncertain: bool
    logging_quality: str
    adherence_score: float = Field(ge=0.0, le=1.0)
    recent_low_adherence: bool
    user_strictness_tolerance: str
    app_usage_style: str
    recent_rescue_count: int = Field(ge=0)
    recent_non_viable_count: int = Field(ge=0)
    ignored_strict_plans: bool
    rescue_history_quality: str
    has_open_rescue_like_proposal: bool
    has_open_calibration_proposal: bool
    proactive_suppressed: bool | None = None
    proactive_quiet_hours_active: bool | None = None


class RescueShadowOvershootSummary(RescueShadowArtifactBaseModel):
    today_overshoot_kcal: int = Field(ge=0)
    weekly_overshoot_kcal: int = Field(ge=0)
    recent_overshoot_days: int = Field(ge=0)


class RescueShadowCandidateArtifact(RescueShadowNoEffectFlags):
    scenario_id: str
    input_context_summary: RescueShadowInputContextSummary
    overshoot_summary: RescueShadowOvershootSummary
    trigger_candidate: RescueTriggerCandidate
    rescue_viability_score: float = Field(ge=0.0, le=1.0)
    viability_band: RescueViabilityBand
    option_candidates: tuple[RescueOptionCandidate, ...] = Field(default_factory=tuple)
    selected_shadow_option_for_review: RescueOptionCandidate | None = None
    options_rejected: tuple[RescueOptionRejection, ...] = Field(default_factory=tuple)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    confidence: float = Field(ge=0.0, le=1.0)
    harm_if_wrong: RescueViabilityHarmIfWrong
    shadow_review_posture: RescueViabilityShadowReviewPosture
    context_candidates_used: tuple[str, ...] = Field(default_factory=tuple)
    context_candidates_ignored: tuple[str, ...] = Field(default_factory=tuple)
    future_required_gate_before_runtime: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_selected_shadow_option_for_review(self) -> RescueShadowCandidateArtifact:
        candidate_ids = [option.option_id for option in self.option_candidates]
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("option_candidates must not contain duplicate option_ids")
        if self.selected_shadow_option_for_review is None:
            return self
        matching = [
            option
            for option in self.option_candidates
            if option.option_id == self.selected_shadow_option_for_review.option_id
        ]
        if not matching:
            raise ValueError("selected_shadow_option_for_review must reference an option candidate")
        if matching[0] != self.selected_shadow_option_for_review:
            raise ValueError(
                "selected_shadow_option_for_review must exactly match option candidate"
            )
        return self


class RescueShadowCandidatesSummary(RescueShadowArtifactBaseModel):
    candidate_count: int = Field(ge=0)
    selected_shadow_option_for_review_count: int = Field(ge=0)
    rejected_option_count: int = Field(ge=0)
    scenario_ids: tuple[str, ...] = Field(default_factory=tuple)
    claim_scope: Literal["offline_fixture_shadow_artifact"] = (
        "offline_fixture_shadow_artifact"
    )


class RescueShadowCandidatesArtifact(RescueShadowNoEffectFlags):
    artifact_type: Literal["rescue_shadow_candidates"] = "rescue_shadow_candidates"
    track: Literal["RescueShadow"] = "RescueShadow"
    summary: RescueShadowCandidatesSummary
    rescue_shadow_candidates: tuple[RescueShadowCandidateArtifact, ...] = Field(
        default_factory=tuple
    )

    @model_validator(mode="after")
    def validate_summary_matches_candidates(self) -> RescueShadowCandidatesArtifact:
        candidates = self.rescue_shadow_candidates
        selected_count = sum(
            candidate.selected_shadow_option_for_review is not None
            for candidate in candidates
        )
        rejected_count = sum(len(candidate.options_rejected) for candidate in candidates)
        scenario_ids = tuple(candidate.scenario_id for candidate in candidates)
        if self.summary.candidate_count != len(candidates):
            raise ValueError("summary.candidate_count must match candidates")
        if self.summary.selected_shadow_option_for_review_count != selected_count:
            raise ValueError(
                "summary.selected_shadow_option_for_review_count must match candidates"
            )
        if self.summary.rejected_option_count != rejected_count:
            raise ValueError("summary.rejected_option_count must match candidates")
        if self.summary.scenario_ids != scenario_ids:
            raise ValueError("summary.scenario_ids must match candidates")
        return self


__all__ = [
    "RescueShadowArtifactBaseModel",
    "RescueShadowCandidateArtifact",
    "RescueShadowCandidatesArtifact",
    "RescueShadowCandidatesSummary",
    "RescueShadowInputContextSummary",
    "RescueShadowNoEffectFlags",
    "RescueShadowOvershootSummary",
    "SIDECAR_ACTIVATION_CONTRACT",
]
