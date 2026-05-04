from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RouteTarget = Literal[
    "direct_answer",
    "retrieve_then_answer",
    "clarify_user_private",
    "retry_repair",
    "best_effort_answer",
]
SourceDecision = Literal["ready", "ask_user", "retrieve"]
AnswerMode = Literal["direct_answer", "answer_with_uncertainty", "best_effort"]
MealBoundary = Literal["continue_active_meal", "start_new_meal", "boundary_clarification"]
MealStatus = Literal["candidate_meal", "draft_unresolved", "completed_meal"]
TaskScope = Literal["meal_specific", "food_general", "non_food"]
MealLinkAction = Literal["attach_to_existing_meal", "create_new_meal", "boundary_ambiguous", "none"]
DecisionNextAction = Literal["run_tool_lookup", "run_clarify"]
ResolutionMode = Literal[
    "exact_label_finalize",
    "near_exact_finalize",
    "component_estimate",
    "provisional_estimate",
    "cannot_estimate_yet",
]
ResolutionBasis = Literal[
    "exact_item_evidence",
    "official_source_evidence",
    "component_model",
    "calibrated_component_model",
]
PassExecutionStatus = Literal["success", "degraded", "failed"]
CommitVersionReason = Literal["new_intake", "clarification_completion", "correction", "historical_correction"]
RecommendationCandidateKind = Literal["golden_order", "nearby", "safe_fallback", "generic"]
RecommendationBudgetPosture = Literal["on_track", "tight", "over_budget", "unknown"]
StageTraceStatus = Literal["ok", "error"]
LogicalModelRole = Literal["fast_router_model", "strict_reasoner_model", "response_writer_model", "vision_parser_model"]
CalibrationEstimateAction = Literal[
    "accept_calibration_proposal",
    "defer_calibration_proposal",
    "reject_calibration_proposal",
]


class ComponentContext(BaseModel):
    name: str
    portion_hint: str | None = None


class EstimateSessionState(BaseModel):
    session_id: str
    original_input: str
    last_known_components: list[ComponentContext] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)


class EstimateRequest(BaseModel):
    text: str = Field(min_length=1)
    allow_search: bool = True
    user_id: str = "default_user"
    local_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    session_state: EstimateSessionState | None = None
    calibration_preview_requested: bool = False
    persist_calibration_proposal: bool = False
    calibration_proposal_container_id: int | None = Field(default=None, ge=1)
    calibration_action: CalibrationEstimateAction | None = None


class TurnState(BaseModel):
    active_meal_log_id: int | None = None
    pending_question: str | None = None
    last_estimate_mode: str | None = None
    candidate_components: list[str] = Field(default_factory=list)
    allowed_next_intents: list[str] = Field(default_factory=list)
