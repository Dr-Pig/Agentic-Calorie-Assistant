from __future__ import annotations

from ...runtime.contracts.phase_a import AttachmentDecision, CurrentTurnContextV1

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
RESOLVED_TARGET_SOURCES = frozenset(
    {
        "manager_structured_target",
        "manager_context_candidates",
    }
)


def target_source_supports_resolved_attachment(*, source: str, confidence: str) -> bool:
    return source in RESOLVED_TARGET_SOURCES and confidence in {"medium", "high"}


def target_reference_opens_correction_workflow(target_meal_reference: dict[str, object]) -> bool:
    return (
        target_meal_reference.get("meal_thread_id") is not None
        and target_source_supports_resolved_attachment(
            source=str(target_meal_reference.get("target_resolution_source") or "").strip(),
            confidence=str(target_meal_reference.get("correction_confidence") or "").strip(),
        )
    )


def _normalized_text(raw_user_input: str) -> str:
    return str(raw_user_input or "").strip().lower()


def _looks_like_ambiguous_ack(raw_user_input: str) -> bool:
    normalized = _normalized_text(raw_user_input)
    return normalized in _AMBIGUOUS_TOKENS


def _looks_like_back_reference(raw_user_input: str) -> bool:
    normalized = _normalized_text(raw_user_input)
    return any(token in normalized for token in _BACK_REFERENCE_TOKENS)


def _source_supports_resolved_target(candidate: dict[str, object]) -> bool:
    source = str(candidate.get("source") or "").strip()
    confidence = str(candidate.get("confidence") or "").strip()
    return target_source_supports_resolved_attachment(source=source, confidence=confidence)


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

    if current_turn_context.pending_followup is not None and raw_user_input.strip():
        return AttachmentDecision(
            disposition="answer_only",
            target_object_type="none",
            target_object_id=None,
            reason="pending_followup_requires_manager_resolution",
            confidence="medium" if primary_target_id is not None else "low",
            ambiguity_flag=False,
            allowed_transition_class="none",
        )

    if target_candidates and primary_target_id is not None and _source_supports_resolved_target(target_candidates[0]):
        return AttachmentDecision(
            disposition="answer_only",
            target_object_type="none",
            target_object_id=None,
            reason="manager_target_candidate_requires_current_turn_resolution",
            confidence="high",
            ambiguity_flag=False,
            allowed_transition_class="none",
        )

    if _looks_like_back_reference(raw_user_input) and primary_target_id is not None:
        return AttachmentDecision(
            disposition="answer_only",
            target_object_type="none",
            target_object_id=None,
            reason="ambiguous_back_reference_requires_manager",
            confidence="low",
            ambiguity_flag=True,
            allowed_transition_class="none",
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
