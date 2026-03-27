from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RouteTarget = Literal[
    "direct_estimate",
    "estimate_with_assumptions",
    "clarify_before_search",
    "answer_after_search",
    "clarify_after_search",
]
SourceDecision = Literal["ready", "ask_user", "search"]
AnswerMode = Literal["direct_answer", "answer_with_uncertainty"]


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


class PhaseOneDecision(BaseModel):
    model_config = ConfigDict(extra="allow")

    components: list[str] = Field(default_factory=list)
    source_decision: SourceDecision = "ask_user"
    meal_title: str | None = None
    quantity_hints: list[str] = Field(default_factory=list)
    component_estimates: list[ComponentEstimate] = Field(default_factory=list)
    followup_question: str | None = None
    search_query: str | None = None


class PhaseTwoEstimate(BaseModel):
    model_config = ConfigDict(extra="allow")

    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    estimated_kcal: int = 0
    answer_mode: AnswerMode = "direct_answer"
    component_estimates: list[ComponentEstimate] = Field(default_factory=list)
    uncertain_macro_areas: list[str] = Field(default_factory=list)


class EstimatePayload(BaseModel):
    meal_title: str
    components: list[str] = Field(default_factory=list)
    quantity_hints: list[str] = Field(default_factory=list)
    component_estimates: list[ComponentEstimate] = Field(default_factory=list)
    protein_g: int = 0
    carb_g: int = 0
    fat_g: int = 0
    estimated_kcal: int = 0
    uncertain_macro_areas: list[str] = Field(default_factory=list)
    source_decision: SourceDecision = "ask_user"
    answer_mode: AnswerMode | None = None
    action_taken: str = ""
    route_target: RouteTarget = "clarify_before_search"
    route_reason: str = ""
    followup_question: str | None = None
    used_search: bool = False
    search_query: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    debug_steps: list[dict[str, Any]] = Field(default_factory=list)
    llm_traces: list[dict[str, Any]] = Field(default_factory=list)
    reply_text: str = ""


class AuditEvent(BaseModel):
    timestamp: str
    text: str
    allow_search: bool
    status: Literal["ok", "error"]
    route_target: str | None = None
    action_taken: str | None = None
    debug_steps: list[dict[str, Any]] = Field(default_factory=list)
    llm_traces: list[dict[str, Any]] = Field(default_factory=list)
    payload: dict[str, Any] | None = None
    error: str | None = None
