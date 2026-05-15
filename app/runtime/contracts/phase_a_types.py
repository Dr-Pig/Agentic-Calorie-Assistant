from __future__ import annotations

from typing import Literal

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
TranscriptSnippetRole = Literal["support_only"]
ManagerSemanticAuthority = Literal["manager_llm", "deterministic_fake_provider", "degraded_fallback", "missing"]
ManagerSemanticIntent = Literal[
    "log_meal",
    "answer_query",
    "correct_meal",
    "complete_onboarding",
    "answer_remaining_budget",
    "onboarding_required",
    "body_observation",
    "general_chat",
    "set_manual_daily_target",
    "unknown",
]
ManagerMutationIntentCandidate = Literal[
    "canonical_write",
    "draft_write",
    "correction_write",
    "body_observation_write",
    "ledger_read",
    "budget_target_write",
    "no_mutation",
    "unknown",
]


__all__ = [
    "AttachmentDisposition",
    "AttachmentTargetType",
    "AtomicBlockType",
    "BudgetAnswerMode",
    "ClarificationMode",
    "CommitBoundaryIntent",
    "ContextAvailability",
    "HistoryExpansionReason",
    "HistoryExpansionScope",
    "InteractionSource",
    "InteractionTargetType",
    "ManagerMutationIntentCandidate",
    "ManagerSemanticAuthority",
    "ManagerSemanticIntent",
    "OpenWorkflowType",
    "OwnerAlignment",
    "PredictedMealStatus",
    "RoutingConfidence",
    "ShadowVisibilityPosture",
    "SurfaceMode",
    "TranscriptSnippetRole",
    "TransitionGuardVerdict",
]
