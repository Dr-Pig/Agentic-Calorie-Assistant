from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.runtime_lab_retrieval import (
    build_shadow_memory_context_pack,
)
from app.memory.application.runtime_lab_reviewed_memory_store import (
    RuntimeLabReviewedMemoryStore,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_reviewed_memory_retrieval"
)


def build_shadow_memory_context_pack_from_reviewed_store(
    store: RuntimeLabReviewedMemoryStore,
    scope_keys: Mapping[str, Any],
    *,
    token_budget: int,
    runtime_connected: bool = False,
) -> dict[str, Any]:
    records = store.list_records(scope_keys)
    active_records, inactive_omissions = _partition_records(records)
    pack = build_shadow_memory_context_pack(
        _ReviewedMemoryCandidateSource(active_records),
        scope_keys,
        token_budget=token_budget,
        runtime_connected=runtime_connected,
    )
    pack["source_store_type"] = "runtime_lab_reviewed_memory_store"
    pack["reviewed_memory_store_used"] = True
    pack["reviewed_memory_record_ids"] = [
        _record_id(record) for record in active_records
    ]
    pack["omission_trace"] = [
        *pack.get("omission_trace", []),
        *inactive_omissions,
    ]
    pack["manager_context_packet_changed"] = False
    pack["manager_context_injected"] = False
    pack["runtime_effect_allowed"] = False
    pack["durable_product_memory_written"] = False
    return pack


class _ReviewedMemoryCandidateSource:
    def __init__(self, records: list[Mapping[str, Any]]) -> None:
        self._records = records

    def list_candidates(self, scope_keys: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [_candidate_record(record) for record in self._records]


def _partition_records(
    records: list[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[dict[str, str]]]:
    active_records: list[Mapping[str, Any]] = []
    omissions: list[dict[str, str]] = []
    for record in records:
        if record.get("active_in_lab_context") is True:
            active_records.append(record)
            continue
        omissions.append(
            {
                "candidate_id": _candidate_id(record),
                "reason": _omission_reason(record),
            }
        )
    return active_records, omissions


def _candidate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    candidate = {
        "candidate_id": _candidate_id(record),
        "candidate_type": str(record.get("candidate_type") or "memory"),
        "scope_keys": dict(_mapping(record.get("scope_keys"))),
        "source_object_refs": _source_object_refs(record),
        "review_status": _review_status(record),
        "payload": {
            "summary": str(record.get("memory_text") or ""),
            "blocks_candidate_types": _blocks_candidate_types(record),
        },
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }
    return {
        "record_type": "runtime_lab_reviewed_memory_retrieval_projection",
        "candidate_id": candidate["candidate_id"],
        "scope_keys": candidate["scope_keys"],
        "candidate": candidate,
        "review_status": candidate["review_status"],
        "source_object_refs": candidate["source_object_refs"],
        "lab_isolated": True,
        "canonical_db_changed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def _candidate_id(record: Mapping[str, Any]) -> str:
    return str(record.get("source_candidate_id") or _record_id(record))


def _record_id(record: Mapping[str, Any]) -> str:
    return str(record.get("memory_record_id") or "")


def _source_object_refs(record: Mapping[str, Any]) -> list[str]:
    provenance = _mapping(record.get("provenance"))
    refs = provenance.get("source_object_refs")
    return [str(ref) for ref in refs] if isinstance(refs, list) else []


def _review_status(record: Mapping[str, Any]) -> str:
    state = str(record.get("record_state") or "")
    if state in {"accepted_shadow", "corrected_shadow"}:
        return "accepted"
    if state == "expired_shadow":
        return "expired"
    return state or "pending"


def _blocks_candidate_types(record: Mapping[str, Any]) -> list[str]:
    if record.get("candidate_type") == "negative_preference":
        return ["recommendation_candidate"]
    return []


def _omission_reason(record: Mapping[str, Any]) -> str:
    if record.get("record_state") == "deleted_shadow":
        return "deleted_by_reviewer"
    return str(record.get("record_state") or "inactive_reviewed_memory")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_shadow_memory_context_pack_from_reviewed_store",
]
