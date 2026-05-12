from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import (
    NON_MUTATION_FLAGS,
    REQUIRED_SCOPE_KEYS,
    validate_memory_record_contract,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.memory_record_context_pack"
)


def build_memory_record_context_pack(
    *,
    memory_records: list[Mapping[str, Any]],
    scope_keys: Mapping[str, Any],
    consumer: str,
    token_budget: int,
    as_of: str | None = None,
) -> dict[str, Any]:
    blockers = _contract_blockers(memory_records)
    if blockers:
        return _pack(status="blocked", blockers=blockers, entries=[], omissions=[], token_budget=token_budget)

    used_tokens = 0
    entries: list[dict[str, Any]] = []
    omissions: list[dict[str, str]] = []
    for record in _ordered_records(memory_records):
        normalized = validate_memory_record_contract(record)["normalized_record"]
        record_id = str(normalized["id"])
        reason = _omission_reason(normalized, scope_keys, consumer, as_of)
        if reason:
            omissions.append({"record_id": record_id, "reason": reason})
            continue
        entry = _entry(normalized, record)
        entry_tokens = _token_estimate(entry)
        if used_tokens + entry_tokens > token_budget:
            omissions.append({"record_id": record_id, "reason": "token_budget_exceeded"})
            continue
        entries.append(entry)
        used_tokens += entry_tokens

    pack = _pack(
        status="pass",
        blockers=[],
        entries=entries,
        omissions=omissions,
        token_budget=token_budget,
    )
    pack["token_estimate"] = used_tokens
    return pack


def _contract_blockers(records: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for record in records:
        record_id = str(record.get("id") or "memory_record")
        validation = validate_memory_record_contract(record)
        blockers.extend(f"{record_id}.{item}" for item in validation["blockers"])
    return blockers


def _ordered_records(records: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        records,
        key=lambda record: (
            0 if record.get("record_type") == "negative_preference" else 1,
            str(record.get("id") or ""),
        ),
    )


def _omission_reason(
    record: Mapping[str, Any],
    scope_keys: Mapping[str, Any],
    consumer: str,
    as_of: str | None,
) -> str:
    if not _scope_matches(record, scope_keys):
        return "scope_mismatch"
    if record.get("status") != "confirmed":
        return "not_confirmed"
    if consumer and consumer not in record.get("consumers", []):
        return "consumer_mismatch"
    if record.get("record_type") == "temporary_preference" and _expired(record, as_of):
        return "stale_or_expired"
    return ""


def _entry(normalized: Mapping[str, Any], original: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": str(normalized.get("id") or ""),
        "record_type": str(normalized.get("record_type") or ""),
        "family": str(normalized.get("family") or ""),
        "summary": str(normalized.get("summary") or ""),
        "polarity": str(normalized.get("polarity") or ""),
        "strength": str(normalized.get("strength") or ""),
        "source_refs": [str(ref) for ref in normalized.get("source_refs", []) if ref],
        "subject_keys": _string_list(original.get("subject_keys")),
        "store_name": str(original.get("store_name") or ""),
        "item_names": _string_list(original.get("item_names")),
        "estimated_kcal": _int_or_none(original.get("estimated_kcal")),
        "surface_role": "memory_record_summary",
    }


def _pack(
    *,
    status: str,
    blockers: list[str],
    entries: list[dict[str, Any]],
    omissions: list[dict[str, str]],
    token_budget: int,
) -> dict[str, Any]:
    negative_entries = [entry for entry in entries if entry["polarity"] == "negative"]
    return {
        "artifact_type": "shadow_memory_context_pack",
        "status": status,
        "blockers": blockers,
        "entries": entries,
        "selected_record_ids": [entry["record_id"] for entry in entries],
        "negative_preference_blockers": [entry["record_id"] for entry in negative_entries],
        "negative_blocker_subject_keys": _dedupe(
            [key for entry in negative_entries for key in entry["subject_keys"]]
        ),
        "omission_trace": omissions,
        "token_budget": token_budget,
        "token_estimate": 0,
        "token_budget_retry_expansion_used": False,
        "summary_first": True,
        "source_lookup_required_for_evidence": True,
        "shadow_memory_context_pack_used": True,
        "manager_context_injected": False,
        **NON_MUTATION_FLAGS,
    }


def _scope_matches(record: Mapping[str, Any], scope_keys: Mapping[str, Any]) -> bool:
    record_scope = _mapping(record.get("scope_keys"))
    return all(
        str(record_scope.get(key) or "") == str(scope_keys.get(key) or "")
        for key in REQUIRED_SCOPE_KEYS
    )


def _expired(record: Mapping[str, Any], as_of: str | None) -> bool:
    validity = record.get("validity")
    valid_until = validity.get("valid_until") if isinstance(validity, Mapping) else None
    if not isinstance(valid_until, str) or not as_of:
        return False
    return _parse(valid_until) < _parse(as_of)


def _parse(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.combine(date.fromisoformat(value), datetime.min.time(), timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _token_estimate(entry: Mapping[str, Any]) -> int:
    return max(1, len(str(entry.get("summary") or "").split()))


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_memory_record_context_pack",
]
