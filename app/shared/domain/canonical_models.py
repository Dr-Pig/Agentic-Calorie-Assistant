from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class MealItem(BaseModel):
    name: str
    quantity_hint: str | None = None
    source: str = "llm"
    evidence_role: str = "unknown"
    estimate_basis: str = "llm_only"
    confidence_tier: Literal["high", "medium", "low"] = "low"
    estimated_kcal: int = 0
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    classification: dict[str, Any] = Field(default_factory=dict)


class MealVersion(BaseModel):
    version_id: int | None = None
    meal_thread_id: int | None = None
    parent_version_id: int | None = None
    version_status: str = "active"
    version_reason: str = "new_intake"
    reason_payload: dict[str, Any] = Field(default_factory=dict)
    meal_title: str = ""
    raw_input: str = ""
    source_request_id: str | None = None
    planner_intent: str | None = None
    resolution_status: str = "completed_meal"
    total_kcal: int = 0
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    occurred_at: datetime | None = None
    local_date: str = ""
    superseded_at: datetime | None = None
    created_at: datetime | None = None
    items: list[MealItem] = Field(default_factory=list)


class MealThread(BaseModel):
    meal_thread_id: int | None = None
    user_id: int | None = None
    title: str = ""
    thread_kind: str = "text_intake"
    active_version_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    active_version: MealVersion | None = None


class LedgerEntry(BaseModel):
    entry_id: int | None = None
    user_id: int | None = None
    local_date: str = ""
    entry_type: str = ""
    source_type: str = ""
    source_id: int | None = None
    delta_kcal: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class DayBudgetLedger(BaseModel):
    ledger_id: int | None = None
    user_id: int | None = None
    local_date: str = ""
    budget_kcal: int = 0
    consumed_kcal: int = 0
    adjustment_kcal: int = 0
    remaining_kcal: int = 0
    last_recomputed_at: datetime | None = None


class CurrentBudgetMealSummary(BaseModel):
    meal_thread_id: int | None = None
    meal_version_id: int | None = None
    meal_title: str = ""
    total_kcal: int = 0
    occurred_at: datetime | None = None
    resolution_status: str = "completed_meal"
    planner_intent: str | None = None
    source_request_id: str | None = None


class CurrentBudgetView(BaseModel):
    user_id: int | None = None
    local_date: str = ""
    budget_kcal: int = 0
    consumed_kcal: int = 0
    consumed_protein: int = 0
    consumed_carbs: int = 0
    consumed_fat: int = 0
    show_macro: bool = False
    macro_guard_reason: str | None = None
    adjustment_kcal: int = 0
    remaining_kcal: int = 0
    active_meal_count: int = 0
    meals: list[CurrentBudgetMealSummary] = Field(default_factory=list)
    last_recomputed_at: datetime | None = None


class BodyObservation(BaseModel):
    observation_id: int | None = None
    user_id: int | None = None
    observation_type: str = "weight"
    value: float = 0.0
    unit: str = "kg"
    observed_at: datetime | None = None
    local_date: str = ""
    source: str = "manual"
    metadata: dict[str, Any] = Field(default_factory=dict)


class BodyProfile(BaseModel):
    body_profile_id: int | None = None
    user_id: int | None = None
    profile_status: str = "active"
    sex: str = "female"
    age_years: int = 0
    height_cm: float = 0.0
    current_weight_kg: float = 0.0
    activity_level: str = "sedentary"
    goal_type: str = "lose_weight"
    target_weight_kg: float | None = None
    weekly_target_rate_kg: float | None = None
    timezone: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BodyPlan(BaseModel):
    body_plan_id: int | None = None
    user_id: int | None = None
    plan_status: str = "active"
    plan_label: str = ""
    estimated_tdee: int = 0
    daily_budget_kcal: int = 0
    safety_floor_kcal: int = 0
    target_pace_kg_per_week: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    ended_at: datetime | None = None


class ActiveBodyPlanView(BaseModel):
    body_plan_id: int | None = None
    user_id: int | None = None
    plan_status: str = "inactive"
    goal_type: str | None = None
    current_weight_kg: float | None = None
    target_weight_kg: float | None = None
    age_years: int | None = None
    height_cm: float | None = None
    activity_level: str | None = None
    daily_budget_kcal: int = 0
    recommended_target_kcal: int = 0
    daily_deficit_kcal: int = 0
    safety_floor_kcal: int = 0
    estimated_tdee: int = 0
    target_pace_kg_per_week: float | None = None
    plan_source: str | None = None
    profile_status: str = "missing"
    last_updated_at: datetime | None = None


class ProposalOption(BaseModel):
    proposal_option_id: int | None = None
    option_type: str = ""
    option_label: str = ""
    option_summary: str = ""
    rank_order: int = 0
    is_primary: bool = False
    effect_payload: dict[str, Any] = Field(default_factory=dict)


class ProposalContainer(BaseModel):
    proposal_container_id: int | None = None
    user_id: int | None = None
    proposal_type: str = ""
    proposal_status: str = "open"
    top_option_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    accepted_at: datetime | None = None
    created_at: datetime | None = None
    options: list[ProposalOption] = Field(default_factory=list)


class ProactiveTrigger(BaseModel):
    proactive_trigger_id: int | None = None
    user_id: int | None = None
    trigger_type: str = ""
    trigger_status: str = "created"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
