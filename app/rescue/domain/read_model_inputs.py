from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.domain.read_model_inputs"
)


class RescueCurrentBudgetReadModel(BaseModel):
    view_name: Literal["CurrentBudgetView"] = "CurrentBudgetView"
    view_available: bool
    local_date: str = ""
    base_budget_kcal: int = 0
    effective_budget_kcal: int = 0
    meal_consumption_total_kcal: int = 0
    remaining_kcal: int = 0
    overshoot_kcal: int = 0
    source: str = ""


class RescueCommittedMealReadModel(BaseModel):
    meal_thread_id: str
    meal_title: str = ""
    total_kcal: int = 0


class RescueRecentCommittedMealsReadModel(BaseModel):
    view_name: Literal["RecentCommittedMealsView"] = "RecentCommittedMealsView"
    view_available: bool
    meal_count: int = 0
    meals: list[RescueCommittedMealReadModel] = Field(default_factory=list)


class RescueTargetDayReadModel(BaseModel):
    local_date: str
    base_budget_kcal: int = 0
    calibration_adjustment_total_kcal: int = 0


class RescueActiveBodyPlanReadModel(BaseModel):
    view_name: Literal["ActiveBodyPlanView"] = "ActiveBodyPlanView"
    view_available: bool
    safety_floor_kcal: int = 0
    target_day_count: int = 0
    target_days: list[RescueTargetDayReadModel] = Field(default_factory=list)
    source: str = ""


class RescueOpenProposalsReadModel(BaseModel):
    view_name: Literal["OpenProposalsView"] = "OpenProposalsView"
    view_available: bool
    open_rescue_proposal_count: int = 0
    active_proposal_ids: list[str] = Field(default_factory=list)


class RescueProactiveStatusReadModel(BaseModel):
    view_name: Literal["ProactiveStatusView"] = "ProactiveStatusView"
    view_available: bool
    budget_alert_cooldown_active: bool = False
    suppressed_trigger_types: list[str] = Field(default_factory=list)
    next_allowed_signal: str | None = None


class RescueReadModelInputPacket(BaseModel):
    artifact_type: Literal["rescue_read_model_input_packet"] = (
        "rescue_read_model_input_packet"
    )
    status: Literal["ready", "blocked"]
    blockers: list[str] = Field(default_factory=list)
    owner: Literal["app/rescue"] = "app/rescue"
    consumer: str = "rescue_phase1_runtime_lab_nodes"
    scope_keys: dict[str, str]
    source_trace_ids: list[str] = Field(default_factory=list)
    canonical_source_refs: list[dict[str, str]] = Field(default_factory=list)
    view_source_order: list[str] = Field(default_factory=list)
    forbidden_input_sources: list[str] = Field(default_factory=list)
    current_budget_view: RescueCurrentBudgetReadModel
    recent_committed_meals_view: RescueRecentCommittedMealsReadModel
    active_body_plan_view: RescueActiveBodyPlanReadModel
    open_proposals_view: RescueOpenProposalsReadModel
    proactive_status_view: RescueProactiveStatusReadModel
    rescue_history_summary: dict[str, Any] = Field(default_factory=dict)
    adherence_summary: dict[str, Any] = Field(default_factory=dict)
    lab_enabled: Literal[True] = True
    lab_isolated: Literal[True] = True
    mainline_activation_enabled: Literal[False] = False
    mainline_runtime_connected: Literal[False] = False
    runtime_effect_allowed: Literal[False] = False
    canonical_mutation_changed: Literal[False] = False
    production_scheduler_delivery_allowed: Literal[False] = False
    manager_context_packet_changed_in_mainline: Literal[False] = False
    durable_product_memory_written_in_mainline: Literal[False] = False


__all__ = [
    "RescueActiveBodyPlanReadModel",
    "RescueCommittedMealReadModel",
    "RescueCurrentBudgetReadModel",
    "RescueOpenProposalsReadModel",
    "RescueProactiveStatusReadModel",
    "RescueReadModelInputPacket",
    "RescueRecentCommittedMealsReadModel",
    "RescueTargetDayReadModel",
    "SIDECAR_ACTIVATION_CONTRACT",
]
