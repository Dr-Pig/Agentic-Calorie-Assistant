from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ContextAvailability = Literal["present", "none", "unknown"]
InteractionSource = Literal["chat", "ui", "smart_chip"]
SurfaceMode = Literal["chat_freeform", "ui_anchored_action"]
InteractionTargetType = Literal["meal_thread", "meal_item", "proposal", "none"]
AttachmentTargetType = Literal["meal_thread", "proposal", "none"]
OpenWorkflowType = Literal["none", "meal_followup", "meal_correction", "proposal", "unknown"]
AttachmentDisposition = Literal[
    "create_new_workflow",
    "attach_existing_thread",
    "target_committed_thread",
    "answer_only",
]
RoutingConfidence = Literal["high", "medium", "low"]
TransitionGuardVerdict = Literal["pass", "block", "answer_only", "clarify_required"]
ClarificationMode = Literal["direct_commit", "estimate_with_followup", "clarify_before_estimate", "none"]
CommitBoundaryIntent = Literal["commit", "draft", "no_mutation"]
PredictedMealStatus = Literal["candidate_meal", "draft_unresolved", "completed_meal", "none"]
BudgetAnswerMode = Literal["ready", "degraded", "not_applicable"]
OwnerAlignment = Literal["aligned", "contradictory", "not_applicable"]
HistoryExpansionReason = Literal["target_ambiguity", "correction_reference", "older_meal_reference", "unresolved_followup"]
HistoryExpansionScope = Literal["active_thread", "recent_meals", "committed_meals", "conversation_atomic_blocks"]
ShadowVisibilityPosture = Literal["internal_only", "uncertainty_visible"]
AtomicBlockType = Literal["clarification_answer", "correction_request", "confirm", "reject", "topic_reset"]


class ContextSourceView(BaseModel):
    owner: str
    availability: ContextAvailability = "unknown"
    summary: dict[str, Any] = Field(default_factory=dict)


class InteractionEvent(BaseModel):
    source: InteractionSource
    surface_mode: SurfaceMode | None = None
    event_type: str
    raw_text: str | None = None
    action_id: str | None = None
    target_object_type: InteractionTargetType = "none"
    target_object_id: str | None = None
    occurred_at: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _default_surface_mode(self) -> "InteractionEvent":
        if self.surface_mode is None:
            self.surface_mode = "chat_freeform" if self.source == "chat" else "ui_anchored_action"
        return self


class CurrentTurnContextV1(BaseModel):
    user_utterance: str
    last_system_question: str | None = None
    active_meal_thread_ref: dict[str, Any] | None = None
    pending_followup: dict[str, Any] | None = None
    recent_committed_meal_refs: list[dict[str, Any]] = Field(default_factory=list)
    current_interaction_event: InteractionEvent
    candidate_attachment_targets: list[dict[str, Any]] = Field(default_factory=list)
    open_workflow_type: OpenWorkflowType = "unknown"
    context_risk_flags: list[str] = Field(default_factory=list)
    source_views: dict[str, ContextSourceView] = Field(default_factory=dict)
    current_turn_runtime_summary: dict[str, Any] = Field(default_factory=dict)


class ContextInjectionPolicy(BaseModel):
    must_inject: list[str] = Field(default_factory=list)
    available_if_needed: list[str] = Field(default_factory=list)
    trace_only: list[str] = Field(default_factory=list)
    not_for_manager: list[str] = Field(default_factory=list)


class ManagerContextPack(BaseModel):
    policy: ContextInjectionPolicy
    manager_context: dict[str, Any] = Field(default_factory=dict)
    available_if_needed: dict[str, Any] = Field(default_factory=dict)
    trace_only: dict[str, Any] = Field(default_factory=dict)
    not_for_manager: dict[str, Any] = Field(default_factory=dict)


class AttachmentDecision(BaseModel):
    disposition: AttachmentDisposition
    target_object_type: AttachmentTargetType = "none"
    target_object_id: str | None = None
    reason: str
    confidence: RoutingConfidence = "low"
    ambiguity_flag: bool = False
    allowed_transition_class: str = "none"


class TransitionGuardResult(BaseModel):
    verdict: TransitionGuardVerdict
    reason: str
    blocked_mutation: str | None = None
    affected_object_type: AttachmentTargetType = "none"
    affected_object_id: str | None = None


class ClarificationDecision(BaseModel):
    mode: ClarificationMode = "none"
    followup_required: bool = False
    followup_targets: list[str] = Field(default_factory=list)
    provisional_range_allowed: bool = False


class CommitBoundaryDecision(BaseModel):
    intent: CommitBoundaryIntent = "no_mutation"
    predicted_meal_status: PredictedMealStatus = "none"
    canonical_write_allowed: bool = False
    ledger_mutation_allowed: bool = False
    macro_visible_allowed: bool = False


class FallbackHonestyDecision(BaseModel):
    budget_answer_mode: BudgetAnswerMode = "not_applicable"
    concrete_remaining_kcal_allowed: bool = False
    onboarding_guidance_allowed: bool = False
    intake_allowed_without_plan: bool = True


class PhaseABoundaryProjection(BaseModel):
    clarification_decision: ClarificationDecision
    commit_boundary_decision: CommitBoundaryDecision
    fallback_honesty_decision: FallbackHonestyDecision
    owner_alignment: OwnerAlignment = "not_applicable"
    consistency_flags: list[str] = Field(default_factory=list)
    legacy_projection: dict[str, Any] = Field(default_factory=dict)


class HistoryExpansionPolicy(BaseModel):
    max_calls: int = 1
    max_results: int = 5
    max_atomic_blocks: int = 5
    max_transcript_snippets: int = 2


class HistoryExpansionRequest(BaseModel):
    reason: HistoryExpansionReason
    scope: HistoryExpansionScope
    max_results: int = 5
    max_atomic_blocks: int = 5
    max_transcript_snippets: int = 2


class HistoryMealCandidate(BaseModel):
    meal_thread_id: str
    meal_version_id: str | None = None
    label: str = ""
    occurred_at: str | None = None
    reason: str = ""


class ConversationAtomicBlock(BaseModel):
    block_type: AtomicBlockType
    object_ref: dict[str, Any] = Field(default_factory=dict)
    summary: str
    timestamp: str | None = None
    raw_ref: str | None = None


class TranscriptSnippet(BaseModel):
    snippet_id: str
    content: str
    role: Literal["support_only"] = "support_only"
    timestamp: str | None = None


class HistoryExpansionResult(BaseModel):
    meal_candidates: list[HistoryMealCandidate] = Field(default_factory=list)
    atomic_blocks: list[ConversationAtomicBlock] = Field(default_factory=list)
    transcript_snippets: list[TranscriptSnippet] = Field(default_factory=list)


class ShadowHypothesis(BaseModel):
    hypothesis_id: str
    target_object_type: InteractionTargetType = "none"
    target_object_id: str | None = None
    intent: str
    confidence: RoutingConfidence = "low"
    visibility_posture: ShadowVisibilityPosture = "internal_only"
    created_from: str
    expires_on: str | None = None
    invalidation_reasons: list[str] = Field(default_factory=list)
    mutation_authority: bool = False


__all__ = [
    "AttachmentDecision",
    "AtomicBlockType",
    "BudgetAnswerMode",
    "ClarificationDecision",
    "ClarificationMode",
    "CommitBoundaryDecision",
    "CommitBoundaryIntent",
    "ContextInjectionPolicy",
    "ContextAvailability",
    "ContextSourceView",
    "ConversationAtomicBlock",
    "CurrentTurnContextV1",
    "FallbackHonestyDecision",
    "HistoryExpansionPolicy",
    "HistoryExpansionReason",
    "HistoryExpansionRequest",
    "HistoryExpansionResult",
    "HistoryExpansionScope",
    "HistoryMealCandidate",
    "InteractionEvent",
    "ManagerContextPack",
    "OwnerAlignment",
    "PhaseABoundaryProjection",
    "PredictedMealStatus",
    "ShadowHypothesis",
    "ShadowVisibilityPosture",
    "SurfaceMode",
    "TranscriptSnippet",
    "TransitionGuardResult",
]
