from __future__ import annotations

from ...runtime.agent.manager_fallback_policy import looks_like_budget_query, looks_like_correction
from ...runtime.contracts.phase_a import AttachmentDecision, CurrentTurnContextV1

_TOPIC_RESET_TOKENS = (
    "ignore that",
    "never mind",
    "not that",
    "leave that",
    "skip that",
    "forget that",
)
_INTAKE_TOKENS = (
    "eat",
    "ate",
    "meal",
    "log",
    "breakfast",
    "lunch",
    "dinner",
    "snack",
)
_AMBIGUOUS_TOKENS = {"ok", "okay", "sure", "fine", "good", "yes", "yep"}
_BACK_REFERENCE_TOKENS = (
    "that",
    "this",
    "same",
    "previous",
    "earlier",
    "just",
    "剛剛",
    "剛才",
    "那杯",
    "這杯",
    "那份",
    "這份",
    "那個",
    "這個",
)


def _normalized_text(raw_user_input: str) -> str:
    return str(raw_user_input or "").strip().lower()


def _looks_like_intake_request(raw_user_input: str) -> bool:
    normalized = _normalized_text(raw_user_input)
    return any(token in normalized for token in _INTAKE_TOKENS)


def _looks_like_topic_reset(raw_user_input: str) -> bool:
    normalized = _normalized_text(raw_user_input)
    return any(token in normalized for token in _TOPIC_RESET_TOKENS)


def _looks_like_ambiguous_ack(raw_user_input: str) -> bool:
    normalized = _normalized_text(raw_user_input)
    return normalized in _AMBIGUOUS_TOKENS


def _looks_like_back_reference(raw_user_input: str) -> bool:
    normalized = _normalized_text(raw_user_input)
    return any(token in normalized for token in _BACK_REFERENCE_TOKENS)


def resolve_attachment_decision(current_turn_context: CurrentTurnContextV1) -> AttachmentDecision:
    event = current_turn_context.current_interaction_event
    raw_user_input = current_turn_context.user_utterance
    target_candidates = current_turn_context.candidate_attachment_targets
    primary_target_id = target_candidates[0]["target_object_id"] if target_candidates else None

    if event.surface_mode == "ui_anchored_action" and event.target_object_type == "meal_thread" and event.target_object_id:
        return AttachmentDecision(
            disposition="attach_existing_thread",
            target_object_type="meal_thread",
            target_object_id=event.target_object_id,
            reason="explicit_interaction_target",
            confidence="high",
            ambiguity_flag=False,
            allowed_transition_class="interpretation_update",
        )

    if _looks_like_topic_reset(raw_user_input) and _looks_like_intake_request(raw_user_input):
        return AttachmentDecision(
            disposition="create_new_workflow",
            target_object_type="none",
            target_object_id=None,
            reason="explicit_topic_reset",
            confidence="high",
            ambiguity_flag=False,
            allowed_transition_class="observation_write",
        )

    if looks_like_budget_query(raw_user_input):
        return AttachmentDecision(
            disposition="answer_only",
            target_object_type="none",
            target_object_id=None,
            reason="info_query",
            confidence="high",
            ambiguity_flag=False,
            allowed_transition_class="none",
        )

    if looks_like_correction(raw_user_input) and primary_target_id is not None:
        return AttachmentDecision(
            disposition="target_committed_thread",
            target_object_type="meal_thread",
            target_object_id=primary_target_id,
            reason="identified_correction_target",
            confidence="high",
            ambiguity_flag=False,
            allowed_transition_class="interpretation_update",
        )

    if _looks_like_back_reference(raw_user_input) and primary_target_id is not None:
        return AttachmentDecision(
            disposition="attach_existing_thread",
            target_object_type="meal_thread",
            target_object_id=primary_target_id,
            reason="identified_back_reference_target",
            confidence="medium",
            ambiguity_flag=False,
            allowed_transition_class="interpretation_update",
        )

    if current_turn_context.pending_followup is not None and raw_user_input.strip():
        return AttachmentDecision(
            disposition="attach_existing_thread",
            target_object_type="meal_thread",
            target_object_id=primary_target_id,
            reason="pending_followup_answer",
            confidence="high" if primary_target_id is not None else "medium",
            ambiguity_flag=False,
            allowed_transition_class="interpretation_update",
        )

    if _looks_like_intake_request(raw_user_input):
        return AttachmentDecision(
            disposition="create_new_workflow",
            target_object_type="none",
            target_object_id=None,
            reason="new_intake_request",
            confidence="high",
            ambiguity_flag=False,
            allowed_transition_class="observation_write",
        )

    if _looks_like_ambiguous_ack(raw_user_input):
        return AttachmentDecision(
            disposition="answer_only",
            target_object_type="none",
            target_object_id=None,
            reason="ambiguous_utterance",
            confidence="low",
            ambiguity_flag=True,
            allowed_transition_class="none",
        )

    return AttachmentDecision(
        disposition="answer_only",
        target_object_type="none",
        target_object_id=None,
        reason="no_attachment_signal",
        confidence="low",
        ambiguity_flag=True,
        allowed_transition_class="none",
    )
