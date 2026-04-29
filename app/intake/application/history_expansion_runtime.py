from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import re
from typing import Any

from ...runtime.agent.manager_fallback_policy import looks_like_budget_query, looks_like_correction
from ...runtime.contracts.phase_a import (
    AttachmentDecision,
    CurrentTurnContextV1,
    HistoryExpansionRequest,
    HistoryExpansionResult,
    TransitionGuardResult,
)
from .attachment_resolver import resolve_attachment_decision
from .history_expansion_policy import (
    build_history_expansion_request,
    build_history_expansion_result,
)
from .transition_guard import resolve_transition_guard

_OLDER_REFERENCE_TOKENS = (
    "yesterday",
    "last night",
    "earlier",
    "before",
    "previous",
)
_LEXICAL_STOPWORDS = {
    "actually",
    "change",
    "that",
    "meal",
    "half",
    "bowl",
    "yesterday",
    "today",
    "last",
    "night",
    "earlier",
    "before",
    "previous",
    "rice",
    "sugar",
}


@dataclass(frozen=True)
class HistoryExpansionActivationResult:
    applied: bool
    request: HistoryExpansionRequest | None
    result: HistoryExpansionResult | None
    atomic_blocks_status: str
    pre_attachment_decision: AttachmentDecision
    pre_transition_guard_result: TransitionGuardResult
    post_attachment_decision: AttachmentDecision
    post_transition_guard_result: TransitionGuardResult
    enriched_current_turn_context: CurrentTurnContextV1
    resolution_gain: bool
    selected_candidate_ids: tuple[str, ...] = ()
    ambiguity_detected: bool = False
    transcript_support_inventory: tuple[str, ...] = ()

    def trace_payload(self) -> dict[str, Any]:
        result_summary = None
        if self.result is not None:
            result_summary = {
                "meal_candidate_count": len(self.result.meal_candidates),
                "atomic_block_count": len(self.result.atomic_blocks),
                "transcript_support_count": len(self.result.transcript_snippets),
            }
        return {
            "triggered": self.applied,
            "reason": self.request.reason if self.request is not None else None,
            "scope": self.request.scope if self.request is not None else None,
            "request": self.request.model_dump(mode="json") if self.request is not None else None,
            "result_summary": result_summary,
            "atomic_blocks_status": self.atomic_blocks_status,
            "pre_decision": self.pre_attachment_decision.model_dump(mode="json"),
            "post_decision": self.post_attachment_decision.model_dump(mode="json"),
            "resolution_gain": self.resolution_gain,
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "ambiguity_detected": self.ambiguity_detected,
            "transcript_support_inventory": list(self.transcript_support_inventory),
        }


def _normalized_text(text: str) -> str:
    return str(text or "").strip().lower()


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", _normalized_text(text))
        if len(token) > 1 and token not in _LEXICAL_STOPWORDS
    }


def _looks_like_older_meal_reference(text: str) -> bool:
    normalized = _normalized_text(text)
    return any(token in normalized for token in _OLDER_REFERENCE_TOKENS)


def _expected_relative_date(raw_user_input: str, *, local_date: str | None) -> str | None:
    if not local_date:
        return None
    try:
        base = date.fromisoformat(local_date)
    except ValueError:
        return None
    normalized = _normalized_text(raw_user_input)
    if "yesterday" in normalized:
        return (base - timedelta(days=1)).isoformat()
    if "today" in normalized:
        return base.isoformat()
    return None


def _request_reason(
    *,
    current_turn_context: CurrentTurnContextV1,
    pre_attachment_decision: AttachmentDecision,
    pre_transition_guard_result: TransitionGuardResult,
) -> str | None:
    if current_turn_context.current_interaction_event.surface_mode != "chat_freeform":
        return None
    if current_turn_context.current_interaction_event.target_object_id:
        return None
    if looks_like_budget_query(current_turn_context.user_utterance):
        return None
    if current_turn_context.pending_followup is not None and pre_attachment_decision.target_object_id is not None:
        return None
    unresolved_enough = pre_attachment_decision.disposition == "answer_only" or pre_transition_guard_result.verdict == "clarify_required"
    if not unresolved_enough:
        return None
    if _looks_like_older_meal_reference(current_turn_context.user_utterance):
        return "older_meal_reference"
    if looks_like_correction(current_turn_context.user_utterance):
        return "correction_reference"
    return None


def _request_scope(reason: str) -> str:
    return "recent_meals" if reason == "correction_reference" else "committed_meals"


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return dict(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return dict(value)
    return {}


def _recent_candidates_from_context(current_turn_context: CurrentTurnContextV1) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for meal in current_turn_context.recent_committed_meal_refs:
        if not isinstance(meal, dict) or meal.get("meal_thread_id") is None:
            continue
        candidates.append(
            {
                "meal_thread_id": str(meal["meal_thread_id"]),
                "meal_version_id": str(meal.get("meal_version_id") or "") or None,
                "label": str(meal.get("meal_title") or ""),
                "occurred_at": meal.get("occurred_at"),
                "local_date": str(meal.get("local_date") or ""),
                "relative_time_label": str(meal.get("relative_time_label") or ""),
                "matched_terms": [],
                "source": "recent_committed_meal",
                "content": str(meal.get("meal_title") or ""),
            }
        )
    return candidates


def _historical_candidates_from_state(resolved_state: Any) -> list[dict[str, Any]]:
    conversation_state = getattr(resolved_state, "conversation_state", None)
    raw_items = list(getattr(conversation_state, "retrieved_meal_records", []) or [])
    if not raw_items:
        raw_items = list(getattr(conversation_state, "historical_meal_chunks", []) or [])
    candidates: list[dict[str, Any]] = []
    for item in raw_items:
        payload = _as_dict(item)
        metadata = _as_dict(payload.get("metadata"))
        meal_thread_id = metadata.get("meal_thread_id")
        if meal_thread_id is None:
            continue
        candidates.append(
            {
                "meal_thread_id": str(meal_thread_id),
                "meal_version_id": str(metadata.get("meal_version_id") or "") or None,
                "label": str(metadata.get("title") or ""),
                "occurred_at": payload.get("timestamp"),
                "local_date": str(metadata.get("local_date") or ""),
                "relative_time_label": str(metadata.get("relative_time_label") or ""),
                "matched_terms": [str(term) for term in list(payload.get("matched_terms") or []) if str(term).strip()],
                "source": "retrieved_meal_record",
                "content": str(payload.get("content") or ""),
            }
        )
    return candidates


def _transcript_support_inventory(resolved_state: Any) -> tuple[str, ...]:
    conversation_state = getattr(resolved_state, "conversation_state", None)
    raw_items = list(getattr(conversation_state, "transcript_chunks", []) or [])
    inventory: list[str] = []
    for item in raw_items[:2]:
        payload = _as_dict(item)
        chunk_id = str(payload.get("chunk_id") or "").strip()
        if chunk_id:
            inventory.append(chunk_id)
    return tuple(inventory)


def _candidate_context_supported(candidate: dict[str, Any], current_turn_context: CurrentTurnContextV1) -> bool:
    candidate_id = str(candidate.get("meal_thread_id") or "")
    if not candidate_id:
        return False
    if any(str(target.get("target_object_id") or "") == candidate_id for target in current_turn_context.candidate_attachment_targets):
        return True
    active_thread = _as_dict(current_turn_context.active_meal_thread_ref)
    return str(active_thread.get("meal_thread_id") or "") == candidate_id


def _candidate_temporal_match(candidate: dict[str, Any], *, reason: str, raw_user_input: str, local_date: str | None) -> bool:
    candidate_local_date = str(candidate.get("local_date") or "")
    if reason == "correction_reference":
        return not local_date or not candidate_local_date or candidate_local_date == str(local_date or "")
    expected_date = _expected_relative_date(raw_user_input, local_date=local_date)
    if expected_date:
        return candidate_local_date == expected_date
    if not local_date:
        return "yesterday" in str(candidate.get("relative_time_label") or "").lower() or bool(candidate_local_date)
    return candidate_local_date and candidate_local_date != str(local_date or "")


def _candidate_lexical_match(candidate: dict[str, Any], *, raw_user_input: str, current_turn_context: CurrentTurnContextV1) -> bool:
    if candidate.get("matched_terms"):
        return True
    utterance_tokens = _tokenize(raw_user_input)
    label_tokens = _tokenize(str(candidate.get("label") or ""))
    content_tokens = _tokenize(str(candidate.get("content") or ""))
    if utterance_tokens.intersection(label_tokens) or utterance_tokens.intersection(content_tokens):
        return True
    return _candidate_context_supported(candidate, current_turn_context)


def _strong_candidates(
    candidates: list[dict[str, Any]],
    *,
    reason: str,
    raw_user_input: str,
    current_turn_context: CurrentTurnContextV1,
    local_date: str | None,
) -> list[dict[str, Any]]:
    strong: list[dict[str, Any]] = []
    for candidate in candidates:
        if not _candidate_temporal_match(candidate, reason=reason, raw_user_input=raw_user_input, local_date=local_date):
            continue
        if not _candidate_lexical_match(candidate, raw_user_input=raw_user_input, current_turn_context=current_turn_context):
            continue
        strong.append(candidate)
    return strong


def _enrich_current_turn_context(
    *,
    current_turn_context: CurrentTurnContextV1,
    selected_candidate: dict[str, Any] | None,
    activation_result: HistoryExpansionResult | None,
) -> CurrentTurnContextV1:
    target_candidates = [dict(item) for item in current_turn_context.candidate_attachment_targets]
    if selected_candidate is not None:
        selected_target_id = str(selected_candidate.get("meal_thread_id") or "")
        selected_entry = {
            "target_object_type": "meal_thread",
            "target_object_id": selected_target_id,
            "source": str(selected_candidate.get("source") or "history_expansion"),
            "confidence": "high",
        }
        target_candidates = [
            selected_entry,
            *[item for item in target_candidates if str(item.get("target_object_id") or "") != selected_target_id],
        ]
    source_views = dict(current_turn_context.source_views)
    source_view = source_views.get("candidate_attachment_targets")
    if source_view is not None:
        source_views["candidate_attachment_targets"] = source_view.model_copy(
            update={
                "availability": "present" if target_candidates else "none",
                "summary": {
                    "count": len(target_candidates),
                    "history_expansion_meal_candidates": len(activation_result.meal_candidates) if activation_result is not None else 0,
                },
            }
        )
    runtime_summary = dict(current_turn_context.current_turn_runtime_summary)
    runtime_summary.update(
        {
            "history_expansion_applied": activation_result is not None,
            "history_expansion_candidate_count": len(activation_result.meal_candidates) if activation_result is not None else 0,
        }
    )
    return current_turn_context.model_copy(
        update={
            "candidate_attachment_targets": target_candidates,
            "source_views": source_views,
            "current_turn_runtime_summary": runtime_summary,
        }
    )


def activate_pre_manager_history_expansion(
    *,
    current_turn_context: CurrentTurnContextV1,
    resolved_state: Any,
    pre_attachment_decision: AttachmentDecision | None = None,
    pre_transition_guard_result: TransitionGuardResult | None = None,
) -> HistoryExpansionActivationResult:
    pre_attachment = pre_attachment_decision or resolve_attachment_decision(current_turn_context)
    pre_guard = pre_transition_guard_result or resolve_transition_guard(current_turn_context, pre_attachment)
    reason = _request_reason(
        current_turn_context=current_turn_context,
        pre_attachment_decision=pre_attachment,
        pre_transition_guard_result=pre_guard,
    )
    if reason is None:
        return HistoryExpansionActivationResult(
            applied=False,
            request=None,
            result=None,
            atomic_blocks_status="not_requested",
            pre_attachment_decision=pre_attachment,
            pre_transition_guard_result=pre_guard,
            post_attachment_decision=pre_attachment,
            post_transition_guard_result=pre_guard,
            enriched_current_turn_context=current_turn_context,
            resolution_gain=False,
        )

    request = build_history_expansion_request(
        reason=reason,
        scope=_request_scope(reason),
    )
    if request.scope == "recent_meals":
        normalized_candidates = _recent_candidates_from_context(current_turn_context) + _historical_candidates_from_state(resolved_state)
    else:
        normalized_candidates = _historical_candidates_from_state(resolved_state) + _recent_candidates_from_context(current_turn_context)
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in normalized_candidates:
        target_id = str(candidate.get("meal_thread_id") or "")
        if not target_id or target_id in seen:
            continue
        seen.add(target_id)
        deduped.append(candidate)

    history_result = build_history_expansion_result(
        meal_candidates=[
            {
                "meal_thread_id": candidate["meal_thread_id"],
                "meal_version_id": candidate.get("meal_version_id"),
                "label": candidate.get("label") or "",
                "occurred_at": candidate.get("occurred_at"),
                "reason": candidate.get("source") or request.reason,
            }
            for candidate in deduped
        ],
        atomic_blocks=[],
        transcript_snippets=[],
    )
    atomic_blocks_status = "not_supplied"
    strong_candidates = _strong_candidates(
        deduped,
        reason=reason,
        raw_user_input=current_turn_context.user_utterance,
        current_turn_context=current_turn_context,
        local_date=getattr(resolved_state, "local_date", None),
    )
    selected_candidate = strong_candidates[0] if len(strong_candidates) == 1 else None
    enriched_context = _enrich_current_turn_context(
        current_turn_context=current_turn_context,
        selected_candidate=selected_candidate,
        activation_result=history_result,
    )
    post_attachment = resolve_attachment_decision(enriched_context)
    post_guard = resolve_transition_guard(enriched_context, post_attachment)
    resolution_gain = (
        pre_attachment.disposition == "answer_only"
        and post_attachment.disposition in {"attach_existing_thread", "target_committed_thread"}
    )
    return HistoryExpansionActivationResult(
        applied=True,
        request=request,
        result=history_result,
        atomic_blocks_status=atomic_blocks_status,
        pre_attachment_decision=pre_attachment,
        pre_transition_guard_result=pre_guard,
        post_attachment_decision=post_attachment,
        post_transition_guard_result=post_guard,
        enriched_current_turn_context=enriched_context,
        resolution_gain=resolution_gain,
        selected_candidate_ids=(str(selected_candidate["meal_thread_id"]),) if selected_candidate is not None else (),
        ambiguity_detected=len(strong_candidates) > 1,
        transcript_support_inventory=_transcript_support_inventory(resolved_state),
    )


__all__ = [
    "HistoryExpansionActivationResult",
    "activate_pre_manager_history_expansion",
]
