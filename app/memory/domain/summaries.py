from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("memory.domain.summaries")


class CommittedMealEvent(BaseModel):
    event_id: str
    occurred_at: datetime
    item_names: list[str] = Field(default_factory=list)
    store_name: str | None = None
    cuisine_family: str | None = None


class InteractionPreferenceEvent(BaseModel):
    event_id: str
    occurred_at: datetime
    trigger_type: str
    action: Literal["dismissed", "ignored", "clicked", "accepted"]


class CountedLabel(BaseModel):
    label: str
    count: int


class PreferenceProfileSummary(BaseModel):
    source_kind: Literal["derived_read_model"] = "derived_read_model"
    is_durable_memory_truth: Literal[False] = False
    event_count: int = 0
    top_items: list[CountedLabel] = Field(default_factory=list)
    top_stores: list[CountedLabel] = Field(default_factory=list)
    cuisine_families: list[CountedLabel] = Field(default_factory=list)


class IntakeCompletenessSummary(BaseModel):
    source_kind: Literal["derived_read_model"] = "derived_read_model"
    is_durable_memory_truth: Literal[False] = False
    meal_event_count: int = 0
    logged_day_count: int = 0
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    coverage_posture: Literal["insufficient_fixture", "partial", "reviewable"] = (
        "insufficient_fixture"
    )


class AdherenceSummary(BaseModel):
    source_kind: Literal["derived_read_model"] = "derived_read_model"
    is_durable_memory_truth: Literal[False] = False
    budget_day_count: int = 0
    at_or_under_target_day_count: int = 0
    overshoot_day_count: int = 0
    average_overshoot_kcal: float = 0.0
    adherence_posture: Literal["insufficient_fixture", "mixed", "mostly_on_target"] = (
        "insufficient_fixture"
    )


class RescueHistorySummary(BaseModel):
    source_kind: Literal["derived_read_model"] = "derived_read_model"
    is_durable_memory_truth: Literal[False] = False
    rescue_event_count: int = 0
    overshoot_day_count: int = 0
    rescue_viability_posture: Literal[
        "insufficient_fixture",
        "shadow_candidate_only",
    ] = "insufficient_fixture"


class CalibrationHistorySummary(BaseModel):
    source_kind: Literal["derived_read_model"] = "derived_read_model"
    is_durable_memory_truth: Literal[False] = False
    diagnostic_count: int = 0
    latest_expected_weight_delta_kg: float | None = None
    latest_observed_weight_delta_kg: float | None = None
    latest_bias_posture: Literal[
        "unknown",
        "likely_underestimate_or_expenditure_overestimate",
        "likely_overestimate_or_expenditure_underestimate",
        "aligned",
    ] = "unknown"


class GoldenOrder(BaseModel):
    store_name: str
    item_names: list[str]
    count: int
    last_seen_at: datetime


class GoldenOrderSummary(BaseModel):
    source_kind: Literal["derived_read_model"] = "derived_read_model"
    is_durable_memory_truth: Literal[False] = False
    orders: list[GoldenOrder] = Field(default_factory=list)


class SuppressionSignal(BaseModel):
    trigger_type: str
    count: int
    actions: list[str] = Field(default_factory=list)


class SuppressionSummary(BaseModel):
    source_kind: Literal["derived_read_model"] = "derived_read_model"
    is_durable_memory_truth: Literal[False] = False
    suppression_signals: list[SuppressionSignal] = Field(default_factory=list)
