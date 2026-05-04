from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("rescue.domain.shadow_context")

HARD_RESCUE_CONTEXT_BLOCKS = ["CurrentBudgetView", "OvershootSummary"]
SOFT_RESCUE_CONTEXT_BLOCKS = [
    "AdherenceSummary",
    "RescueHistorySummary",
    "app_usage_style",
    "CalibrationPosture",
]


class RescueFixtureBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CurrentBudgetViewFixture(RescueFixtureBaseModel):
    active: bool
    daily_budget_kcal: int
    consumed_kcal: int
    remaining_kcal: int
    day_part: str = "unknown"


class ActiveBodyPlanViewFixture(RescueFixtureBaseModel):
    active: bool
    daily_target_kcal: int
    safety_floor_kcal: int


class RecentCommittedMealsViewFixture(RescueFixtureBaseModel):
    meal_count_today: int = 0
    logging_coverage: float = 0.0


class DeficitSummaryFixture(RescueFixtureBaseModel):
    weekly_deficit_gap_kcal: int = 0
    weekly_deficit_posture: str = "unknown"


class OvershootSummaryFixture(RescueFixtureBaseModel):
    today_overshoot_kcal: int = 0
    weekly_overshoot_kcal: int = 0
    recent_overshoot_days: int = 0


class CalibrationPostureFixture(RescueFixtureBaseModel):
    posture: str = "unknown"
    confidence: float = 0.0
    recently_accepted: bool = False
    uncertain: bool = False
    body_plan_mutation_allowed: Literal[False] = False


class AdherenceSummaryFixture(RescueFixtureBaseModel):
    logging_quality: str = "unknown"
    adherence_score: float = 0.0
    recent_low_adherence: bool = False
    user_strictness_tolerance: str = "medium"
    app_usage_style: str = "unknown"


class RescueHistorySummaryFixture(RescueFixtureBaseModel):
    recent_rescue_count: int = 0
    recent_non_viable_count: int = 0
    ignored_strict_plans: bool = False
    history_quality: str = "sparse"


class OpenProposalsViewFixture(RescueFixtureBaseModel):
    has_open_rescue_like_proposal: bool = False
    has_open_calibration_proposal: bool = False


class ProactiveStatusViewFixture(RescueFixtureBaseModel):
    suppressed: bool = False
    quiet_hours_active: bool = False
    proactive_send_allowed: Literal[False] = False


class RescueContextFixture(RescueFixtureBaseModel):
    user_id: str
    local_date: date
    timezone: str
    current_budget: CurrentBudgetViewFixture
    active_body_plan: ActiveBodyPlanViewFixture
    recent_committed_meals: RecentCommittedMealsViewFixture
    deficit_summary: DeficitSummaryFixture
    overshoot_summary: OvershootSummaryFixture
    calibration_posture: CalibrationPostureFixture
    adherence_summary: AdherenceSummaryFixture
    rescue_history_summary: RescueHistorySummaryFixture
    open_proposals: OpenProposalsViewFixture
    proactive_status: ProactiveStatusViewFixture | None = None


def build_rescue_context_fixture_contract_status() -> dict[str, object]:
    return {
        "artifact_type": "rescue_context_fixture_contract_status",
        "track": "RescueShadow",
        "slice_id": "rs1_context_fixture_contract",
        "fixture_only": True,
        "runtime_effect_allowed": False,
        "hard_context_blocks": list(HARD_RESCUE_CONTEXT_BLOCKS),
        "soft_context_blocks": list(SOFT_RESCUE_CONTEXT_BLOCKS),
    }


__all__ = [
    "ActiveBodyPlanViewFixture",
    "AdherenceSummaryFixture",
    "CalibrationPostureFixture",
    "CurrentBudgetViewFixture",
    "DeficitSummaryFixture",
    "HARD_RESCUE_CONTEXT_BLOCKS",
    "OpenProposalsViewFixture",
    "OvershootSummaryFixture",
    "ProactiveStatusViewFixture",
    "RecentCommittedMealsViewFixture",
    "RescueContextFixture",
    "RescueHistorySummaryFixture",
    "SIDECAR_ACTIVATION_CONTRACT",
    "SOFT_RESCUE_CONTEXT_BLOCKS",
    "build_rescue_context_fixture_contract_status",
]
