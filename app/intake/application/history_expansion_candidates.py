from __future__ import annotations

from datetime import date, timedelta
import re
from typing import Any

from ...runtime.contracts.phase_a import CurrentTurnContextV1

LEXICAL_STOPWORDS = {
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


def normalized_text(text: str) -> str:
    return str(text or "").strip().lower()


def tokenize_history_text(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", normalized_text(text))
        if len(token) > 1 and token not in LEXICAL_STOPWORDS
    }


def as_history_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return dict(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return dict(value)
    return {}


def recent_candidates_from_context(current_turn_context: CurrentTurnContextV1) -> list[dict[str, Any]]:
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


def historical_candidates_from_state(resolved_state: Any) -> list[dict[str, Any]]:
    conversation_state = getattr(resolved_state, "conversation_state", None)
    raw_items = list(getattr(conversation_state, "retrieved_meal_records", []) or [])
    if not raw_items:
        raw_items = list(getattr(conversation_state, "historical_meal_chunks", []) or [])
    candidates: list[dict[str, Any]] = []
    for item in raw_items:
        payload = as_history_dict(item)
        metadata = as_history_dict(payload.get("metadata"))
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


def transcript_support_inventory(resolved_state: Any) -> tuple[str, ...]:
    conversation_state = getattr(resolved_state, "conversation_state", None)
    raw_items = list(getattr(conversation_state, "transcript_chunks", []) or [])
    inventory: list[str] = []
    for item in raw_items[:2]:
        payload = as_history_dict(item)
        chunk_id = str(payload.get("chunk_id") or "").strip()
        if chunk_id:
            inventory.append(chunk_id)
    return tuple(inventory)


def strong_history_candidates(
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


def _expected_relative_date(raw_user_input: str, *, local_date: str | None) -> str | None:
    if not local_date:
        return None
    try:
        base = date.fromisoformat(local_date)
    except ValueError:
        return None
    normalized = normalized_text(raw_user_input)
    if "yesterday" in normalized:
        return (base - timedelta(days=1)).isoformat()
    if "today" in normalized:
        return base.isoformat()
    return None


def _candidate_context_supported(candidate: dict[str, Any], current_turn_context: CurrentTurnContextV1) -> bool:
    candidate_id = str(candidate.get("meal_thread_id") or "")
    if not candidate_id:
        return False
    if any(str(target.get("target_object_id") or "") == candidate_id for target in current_turn_context.candidate_attachment_targets):
        return True
    active_thread = as_history_dict(current_turn_context.active_meal_thread_ref)
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
    utterance_tokens = tokenize_history_text(raw_user_input)
    label_tokens = tokenize_history_text(str(candidate.get("label") or ""))
    content_tokens = tokenize_history_text(str(candidate.get("content") or ""))
    if utterance_tokens.intersection(label_tokens) or utterance_tokens.intersection(content_tokens):
        return True
    return _candidate_context_supported(candidate, current_turn_context)


candidate_temporal_match = _candidate_temporal_match
candidate_lexical_match = _candidate_lexical_match


__all__ = [
    "candidate_lexical_match",
    "candidate_temporal_match",
    "historical_candidates_from_state",
    "recent_candidates_from_context",
    "strong_history_candidates",
    "transcript_support_inventory",
]
