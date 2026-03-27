from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RouteTarget = Literal[
    "direct_estimate",
    "estimate_with_assumptions",
    "clarify_before_search",
    "answer_after_search",
    "clarify_after_search",
]

DecisionHint = Literal["estimate", "clarify", "search"]
SearchResolution = Literal["answer", "clarify"]
ConfidenceLevel = Literal["high", "provisional", "low"]


class EstimateRequest(BaseModel):
    text: str = Field(min_length=1)
    allow_search: bool = True


class ComponentEstimate(BaseModel):
    name: str
    source: Literal["explicit", "implicit"] = "explicit"
    quantity_hint: str | None = None
    estimated_kcal: int = 0
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0


class EstimatePayload(BaseModel):
    meal_title: str
    meal_category: str
    components: list[str] = Field(default_factory=list)
    known_quantities: list[str] = Field(default_factory=list)
    implicit_components: list[str] = Field(default_factory=list)
    missing_modifiers: list[str] = Field(default_factory=list)
    highest_impact_modifier: str | None = None
    parse_confidence: float = 0.0
    macro_confidence: float = 0.0
    external_verifiability: str = "unknown"
    search_eligibility: bool = True
    search_acceptability: bool | None = None
    confidence_level: ConfidenceLevel = "low"
    estimated_kcal: int = 0
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    component_estimates: list[ComponentEstimate] = Field(default_factory=list)
    action_taken: str
    route_target: RouteTarget
    route_reason: str
    assumptions: list[str] = Field(default_factory=list)
    followup_question: str | None = None
    used_search: bool = False
    search_query: str | None = None
    sources: list[dict] = Field(default_factory=list)
    debug_steps: list[dict] = Field(default_factory=list)
    reply_text: str


class InitialDecision(BaseModel):
    meal_title: str
    meal_category: str = "unknown"
    components: list[str] = Field(default_factory=list)
    known_quantities: list[str] = Field(default_factory=list)
    implicit_components: list[str] = Field(default_factory=list)
    missing_modifiers: list[str] = Field(default_factory=list)
    highest_impact_modifier: str | None = None
    parse_confidence: float = 0.0
    macro_confidence: float = 0.0
    external_verifiability: str = "unknown"
    search_eligibility: bool = True
    can_estimate_with_defaults: bool = False
    confidence_level: ConfidenceLevel = "low"
    decision: DecisionHint = "clarify"
    decision_reason: str = ""
    assumptions: list[str] = Field(default_factory=list)
    followup_question: str | None = None
    component_estimates: list[ComponentEstimate] = Field(default_factory=list)
    estimated_kcal: int = 0
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    search_query: str | None = None


class SearchDecision(BaseModel):
    resolution: SearchResolution = "clarify"
    resolution_reason: str = ""
    search_acceptability: bool = False
    assumptions: list[str] = Field(default_factory=list)
    followup_question: str | None = None
    component_estimates: list[ComponentEstimate] = Field(default_factory=list)
    estimated_kcal: int = 0
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0


class AuditEvent(BaseModel):
    timestamp: str
    text: str
    allow_search: bool
    status: Literal["ok", "error"]
    route_target: str | None = None
    action_taken: str | None = None
    debug_steps: list[dict] = Field(default_factory=list)
    payload: dict | None = None
    error: str | None = None
