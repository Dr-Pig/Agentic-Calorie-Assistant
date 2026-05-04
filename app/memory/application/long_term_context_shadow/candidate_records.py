from __future__ import annotations

from datetime import datetime
from typing import Any

from app.memory.application.long_term_context_shadow.utils import (
    _candidate_non_runtime_truth_reason,
    _consumer_use_hints,
    _dedupe,
    _default_consumers,
    _normalize_datetime,
    _promotion_path,
    _redact_secret_values,
    _risk_if_wrong,
)
from app.memory.domain.long_term_context_candidates import (
    ContextValueReviewItem,
    LongTermContextCandidate,
)


def _candidate(
    *,
    candidate_id: str,
    candidate_type: str,
    user_id: str,
    source_trace_ids: list[str],
    source_object_refs: list[str],
    evidence_count: int,
    observed_at: list[datetime],
    confidence: float,
    proposed_memory_text: str,
    payload: dict[str, Any],
    reason_codes: list[str],
    intended_consumers: list[str] | None = None,
) -> LongTermContextCandidate:
    clean_observed_at = sorted(_normalize_datetime(value) for value in observed_at)
    redacted_payload, redacted_fields = _redact_secret_values(payload)
    secret_status = (
        "redacted_secret_fields_detected"
        if redacted_fields
        else "passed_no_secret_fields_detected"
    )
    return LongTermContextCandidate(
        candidate_id=candidate_id,
        candidate_type=candidate_type,
        user_id=user_id,
        source_trace_ids=_dedupe(source_trace_ids),
        source_object_refs=_dedupe(source_object_refs),
        evidence_count=evidence_count,
        evidence_window_start=clean_observed_at[0] if clean_observed_at else None,
        evidence_window_end=clean_observed_at[-1] if clean_observed_at else None,
        confidence=confidence,
        freshness_posture="recent" if clean_observed_at else "unknown",
        staleness_note=None,
        proposed_memory_text=proposed_memory_text,
        payload=redacted_payload,
        scope_keys={
            "user_id": user_id,
            "workspace_id": "fixture_workspace",
            "project_id": "fixture_project",
            "surface": "fixture_shadow_lab",
        },
        secret_scan={
            "status": secret_status,
            "raw_secret_values_stored": False,
            "redacted_fields": redacted_fields,
        },
        privacy_contract={
            "raw_secret_values_stored": False,
            "scope_keys_required": True,
            "source_refs_required": True,
            "runtime_prompt_injection_allowed": False,
        },
        retention_posture="shadow_review_artifact_only",
        injection_eligibility={
            "eligible": False,
            "reason": "shadow_lab_no_runtime_injection",
        },
        runtime_injection_allowed=False,
        intended_consumers=intended_consumers or _default_consumers(candidate_type),
        consumer_use_hints=_consumer_use_hints(
            intended_consumers or _default_consumers(candidate_type)
        ),
        risk_if_wrong=_risk_if_wrong(candidate_type),
        promotion_path=_promotion_path(candidate_type),
        why_this_is_not_runtime_truth=_candidate_non_runtime_truth_reason(
            candidate_type
        ),
        reason_codes=reason_codes,
    )


def _build_context_value_items(
    candidates: list[LongTermContextCandidate],
) -> list[ContextValueReviewItem]:
    items: list[ContextValueReviewItem] = []
    for candidate in candidates:
        if candidate.candidate_type == "golden_order":
            capabilities = ["recommendation", "intake_clarification"]
            action = "ask_user_to_confirm"
        elif candidate.candidate_type == "food_preference":
            capabilities = ["recommendation", "proactive", "intake_clarification"]
            action = "ask_user_to_confirm"
        elif candidate.candidate_type == "negative_preference":
            capabilities = ["recommendation", "proactive", "intake_clarification"]
            action = "ask_user_to_confirm"
        elif candidate.candidate_type == "temporary_preference":
            capabilities = ["recommendation", "chat_context", "proactive"]
            action = "ask_user_to_confirm"
        elif candidate.candidate_type == "user_language_pattern":
            capabilities = ["intake_clarification", "chat_context"]
            action = "keep_shadowing"
        elif candidate.candidate_type == "intake_estimation_bias":
            capabilities = ["calibration", "intake_risk_tagging"]
            action = "keep_shadowing"
        elif candidate.candidate_type == "app_usage_style":
            capabilities = ["chat_context", "proactive"]
            action = "keep_shadowing"
        elif candidate.candidate_type == "interaction_preference":
            capabilities = ["response_generation", "chat_context"]
            action = "keep_shadowing"
        elif candidate.candidate_type == "conversation_recall_context":
            capabilities = ["chat_context", "intake_clarification"]
            action = "keep_shadowing"
        elif "calibration" in candidate.reason_codes[0]:
            capabilities = ["calibration", "rescue"]
            action = "keep_shadowing"
        elif "overshoot" in candidate.reason_codes[0]:
            capabilities = ["proactive", "rescue"]
            action = "keep_shadowing"
        else:
            capabilities = ["recommendation", "proactive"]
            action = "keep_shadowing"
        strength = (
            "high"
            if candidate.confidence >= 0.8
            else "medium"
            if candidate.confidence >= 0.5
            else "low"
        )
        items.append(
            ContextValueReviewItem(
                review_item_id=f"context-value-{candidate.candidate_id}",
                source_candidate_id=candidate.candidate_id,
                context_found=candidate.proposed_memory_text or candidate.candidate_id,
                helps_capabilities=capabilities,
                why_it_may_be_useful="May reduce repeated clarification or improve shadow ranking once confirmed.",
                evidence_strength=strength,
                possible_harm_if_injected_too_early=(
                    "Could personalize or bias runtime before the user confirms the pattern."
                ),
                recommended_next_action=action,
            )
        )
    return items
