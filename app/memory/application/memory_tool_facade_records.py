from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import (
    REQUIRED_SCOPE_KEYS,
    validate_memory_record_contract,
)


def searchable_records(
    records: list[Mapping[str, Any]],
    scope_keys: Mapping[str, Any],
    consumer: str,
    limit: int,
) -> list[dict[str, Any]]:
    selected = [
        normalized
        for record in records
        for normalized in [_normalized(record)]
        if normalized
        and normalized.get("status") == "confirmed"
        and scope_matches(normalized, scope_keys)
        and (not consumer or consumer in normalized.get("consumers", []))
    ]
    return [public_record(record) for record in selected[:limit]]


def find_public_record(
    records: list[Mapping[str, Any]],
    scope_keys: Mapping[str, Any],
    memory_id: str,
    source_ref: str,
) -> dict[str, Any] | None:
    for record in records:
        normalized = _normalized(record)
        if not normalized or not scope_matches(normalized, scope_keys):
            continue
        if memory_id and normalized.get("id") == memory_id:
            return public_record(normalized)
        if source_ref and source_ref in normalized.get("source_refs", []):
            return public_record(normalized)
    return None


def scope_blockers(scope_keys: Mapping[str, Any]) -> list[str]:
    missing = [key for key in REQUIRED_SCOPE_KEYS if not scope_keys.get(key)]
    return [f"scope_keys.missing:{','.join(missing)}"] if missing else []


def scope_matches(record: Mapping[str, Any], scope_keys: Mapping[str, Any]) -> bool:
    record_scope = _mapping(record.get("scope_keys"))
    return all(
        str(record_scope.get(key) or "") == str(scope_keys.get(key) or "")
        for key in REQUIRED_SCOPE_KEYS
    )


def public_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record.get("id") or ""),
        "record_type": str(record.get("record_type") or ""),
        "family": str(record.get("family") or ""),
        "status": str(record.get("status") or ""),
        "summary": str(record.get("summary") or ""),
        "polarity": str(record.get("polarity") or ""),
        "strength": str(record.get("strength") or ""),
        "source_refs": [str(ref) for ref in record.get("source_refs", []) if ref],
        "consumers": [str(item) for item in record.get("consumers", []) if item],
    }


def _normalized(record: Mapping[str, Any]) -> Mapping[str, Any]:
    validation = validate_memory_record_contract(record)
    if validation["status"] != "pass":
        return {}
    return validation["normalized_record"]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "find_public_record",
    "public_record",
    "scope_blockers",
    "searchable_records",
]
