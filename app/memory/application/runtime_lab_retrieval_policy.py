from __future__ import annotations

from typing import Any, Mapping


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


__all__ = [
    "candidate_summary",
    "contains_raw_field",
    "context_entry",
    "is_stale_or_expired",
    "negative_blocked_types",
    "token_estimate",
]
