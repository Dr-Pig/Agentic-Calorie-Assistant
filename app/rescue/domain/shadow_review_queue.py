from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.rescue.domain.shadow_artifact import RescueShadowNoEffectFlags
from app.rescue.domain.shadow_options import RescueOptionType
from app.rescue.domain.shadow_trigger import RescueTriggerCandidate
from app.rescue.domain.shadow_viability import (
    RescueViabilityBand,
    RescueViabilityShadowReviewPosture,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.domain.shadow_review_queue"
)

RescueShadowReviewPriority = Literal["high", "medium", "low", "rejected_or_deferred"]


class RescueShadowReviewQueueItem(RescueShadowNoEffectFlags):
    scenario_id: str
    shadow_review_priority: RescueShadowReviewPriority
    reasons: tuple[str, ...] = Field(default_factory=tuple)
    shadow_review_posture: RescueViabilityShadowReviewPosture
    viability_band: RescueViabilityBand
    confidence: float = Field(ge=0.0, le=1.0)
    trigger_candidate: RescueTriggerCandidate
    selected_shadow_option_type_for_review: RescueOptionType | None = None


class RescueShadowReviewQueueSummary(RescueShadowNoEffectFlags):
    total_candidate_count: int = Field(ge=0)
    high_priority_count: int = Field(ge=0)
    medium_priority_count: int = Field(ge=0)
    low_priority_count: int = Field(ge=0)
    rejected_or_deferred_count: int = Field(ge=0)
    scenario_ids: tuple[str, ...] = Field(default_factory=tuple)
    claim_scope: Literal["offline_shadow_review_queue"] = "offline_shadow_review_queue"


class RescueShadowReviewQueue(RescueShadowNoEffectFlags):
    """Offline review queue only; it is not proposal or runtime authority."""

    artifact_type: Literal["rescue_shadow_review_queue"] = "rescue_shadow_review_queue"
    track: Literal["RescueShadow"] = "RescueShadow"
    slice_id: Literal["rs7_shadow_review_queue"] = "rs7_shadow_review_queue"
    summary: RescueShadowReviewQueueSummary
    high_priority_rescue_candidates: tuple[RescueShadowReviewQueueItem, ...] = Field(
        default_factory=tuple
    )
    medium_priority_rescue_candidates: tuple[RescueShadowReviewQueueItem, ...] = Field(
        default_factory=tuple
    )
    low_priority_rescue_candidates: tuple[RescueShadowReviewQueueItem, ...] = Field(
        default_factory=tuple
    )
    rejected_or_deferred: tuple[RescueShadowReviewQueueItem, ...] = Field(
        default_factory=tuple
    )
    reasons: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_bucket_priorities_and_summary(self) -> RescueShadowReviewQueue:
        bucket_expectations = (
            ("high", self.high_priority_rescue_candidates),
            ("medium", self.medium_priority_rescue_candidates),
            ("low", self.low_priority_rescue_candidates),
            ("rejected_or_deferred", self.rejected_or_deferred),
        )
        seen: set[str] = set()
        for expected_priority, items in bucket_expectations:
            for item in items:
                if item.shadow_review_priority != expected_priority:
                    raise ValueError("review queue item priority must match its bucket")
                if item.scenario_id in seen:
                    raise ValueError("scenario_id must appear in only one review bucket")
                seen.add(item.scenario_id)
        if self.summary.high_priority_count != len(self.high_priority_rescue_candidates):
            raise ValueError("summary.high_priority_count must match high bucket")
        if self.summary.medium_priority_count != len(self.medium_priority_rescue_candidates):
            raise ValueError("summary.medium_priority_count must match medium bucket")
        if self.summary.low_priority_count != len(self.low_priority_rescue_candidates):
            raise ValueError("summary.low_priority_count must match low bucket")
        if self.summary.rejected_or_deferred_count != len(self.rejected_or_deferred):
            raise ValueError("summary.rejected_or_deferred_count must match deferred bucket")
        if self.summary.total_candidate_count != len(seen):
            raise ValueError("summary.total_candidate_count must match review buckets")
        expected_scenario_ids = tuple(
            item.scenario_id
            for _priority, items in bucket_expectations
            for item in items
        )
        if self.summary.scenario_ids != expected_scenario_ids:
            raise ValueError("summary.scenario_ids must match review buckets")
        return self


__all__ = [
    "RescueShadowReviewPriority",
    "RescueShadowReviewQueue",
    "RescueShadowReviewQueueItem",
    "RescueShadowReviewQueueSummary",
    "SIDECAR_ACTIVATION_CONTRACT",
]
