from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping

from app.memory.application.runtime_lab_trace_ingress_contracts import (
    REQUIRED_SCOPE_KEYS,
)


RAW_FIELD_DENYLIST = {
    "raw_user_input",
    "raw_transcript",
    "sanitized_source_trace",
    "request_text",
}


def candidate_summary(candidate: Mapping[str, Any]) -> str:
    candidate_type = str(candidate.get("candidate_type") or "memory")
    payload = _payload(candidate)
    summary = payload.get("summary") or payload.get("proposed_memory_text")
    if not summary:
        summary = f"{candidate_type} from {len(candidate.get('source_object_refs', []))} refs"
    return f"{candidate_type}: {summary}"


def is_stale_or_expired(record: Mapping[str, Any]) -> bool:
    candidate = _candidate(record)
    payload = _payload(candidate)
    return (
        candidate.get("review_status") == "expired"
        or payload.get("freshness_posture") == "stale"
        or candidate.get("freshness_posture") == "stale"
        or _has_expired_validity_window(payload)
    )


def requires_conflict_review(record: Mapping[str, Any]) -> bool:
    candidate = _candidate(record)
    payload = _payload(candidate)
    conflict_status = str(payload.get("conflict_status") or "").strip()
    return (
        candidate.get("candidate_type") == "contradiction_review"
        or payload.get("contradiction_review_required") is True
        or bool(payload.get("conflicts_with"))
        or conflict_status in {"conflicted", "contradictory", "requires_review"}
    )


def negative_blocked_types(records: list[Mapping[str, Any]]) -> tuple[set[str], list[str]]:
    blocked_types: set[str] = set()
    blocker_ids: list[str] = []
    for record in records:
        candidate = _candidate(record)
        if candidate.get("candidate_type") != "negative_preference":
            continue
        payload = _payload(candidate)
        blocked = payload.get("blocks_candidate_types")
        if isinstance(blocked, list):
            blocked_types.update(str(item) for item in blocked)
            blocker_ids.append(str(candidate.get("candidate_id")))
    return blocked_types, blocker_ids


def scope_matches(record: Mapping[str, Any], requested_scope: Mapping[str, Any]) -> bool:
    requested = {key: str(requested_scope.get(key) or "") for key in REQUIRED_SCOPE_KEYS}
    candidate = _candidate(record)
    candidate_scope = _mapping(candidate.get("scope_keys")) or _mapping(
        record.get("scope_keys")
    )
    return all(
        requested.get(key) and str(candidate_scope.get(key) or "") == requested[key]
        for key in REQUIRED_SCOPE_KEYS
    )


def context_entry(record: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _candidate(record)
    return {
        "candidate_id": str(candidate.get("candidate_id")),
        "candidate_type": str(candidate.get("candidate_type")),
        "summary": candidate_summary(candidate),
        "source_object_refs": list(candidate.get("source_object_refs", [])),
        "review_status": str(candidate.get("review_status") or "pending"),
    }


def token_estimate(entry: Mapping[str, Any]) -> int:
    return max(1, len(str(entry.get("summary") or "").split()))


def contains_raw_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in RAW_FIELD_DENYLIST or contains_raw_field(item):
                return True
    if isinstance(value, list):
        return any(contains_raw_field(item) for item in value)
    return False


def _candidate(record: Mapping[str, Any]) -> Mapping[str, Any]:
    candidate = record.get("candidate")
    if isinstance(candidate, Mapping):
        return candidate
    return record


def _payload(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = candidate.get("payload")
    if isinstance(payload, Mapping):
        return payload
    return {}


def _has_expired_validity_window(payload: Mapping[str, Any]) -> bool:
    return _valid_until_date_has_passed(payload.get("valid_until")) or _is_past_timestamp(
        payload.get("expires_at")
    )


def _valid_until_date_has_passed(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    raw = value.strip()
    try:
        parsed_date = date.fromisoformat(raw)
    except ValueError:
        return _is_past_timestamp(raw)
    return parsed_date < datetime.now(timezone.utc).date()


def _is_past_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed_date = date.fromisoformat(raw)
        except ValueError:
            return False
        return parsed_date < datetime.now(timezone.utc).date()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed <= datetime.now(timezone.utc)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "candidate_summary",
    "contains_raw_field",
    "context_entry",
    "is_stale_or_expired",
    "negative_blocked_types",
    "requires_conflict_review",
    "scope_matches",
    "token_estimate",
]
