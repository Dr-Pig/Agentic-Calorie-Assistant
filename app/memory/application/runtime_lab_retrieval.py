from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.runtime_lab_retrieval_policy import (
    contains_raw_field,
    context_entry,
    is_stale_or_expired,
    negative_blocked_types,
    requires_conflict_review,
    scope_matches,
    token_estimate,
)
from app.memory.application.runtime_lab_store import RuntimeLabMemoryStore
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_retrieval"
)


def build_shadow_memory_context_pack(
    store: RuntimeLabMemoryStore,
    scope_keys: Mapping[str, Any],
    *,
    token_budget: int,
    runtime_connected: bool = False,
) -> dict[str, Any]:
    records = store.list_candidates(scope_keys)
    eligible_blocker_records = [
        record
        for record in records
        if scope_matches(record, scope_keys)
        and not is_stale_or_expired(record)
        and not requires_conflict_review(record)
    ]
    blocked_types, blocker_ids = negative_blocked_types(eligible_blocker_records)
    entries: list[dict[str, Any]] = []
    omissions: list[dict[str, str]] = []
    used_tokens = 0

    for record in records:
        candidate = record["candidate"]
        candidate_id = str(candidate.get("candidate_id"))
        candidate_type = str(candidate.get("candidate_type"))
        if not scope_matches(record, scope_keys):
            omissions.append(_omission(candidate_id, "scope_mismatch"))
            continue
        if is_stale_or_expired(record):
            omissions.append(_omission(candidate_id, "stale_or_expired"))
            continue
        if requires_conflict_review(record):
            omissions.append(_omission(candidate_id, "conflict_review_required"))
            continue
        if candidate_type in blocked_types and candidate_id not in blocker_ids:
            omissions.append(_omission(candidate_id, "blocked_by_negative_preference"))
            continue
        entry = context_entry(record)
        if contains_raw_field(entry):
            omissions.append(_omission(candidate_id, "raw_field_blocked"))
            continue
        entry_tokens = token_estimate(entry)
        if used_tokens + entry_tokens > token_budget:
            omissions.append(_omission(candidate_id, "token_budget_exceeded"))
            continue
        entries.append(entry)
        used_tokens += entry_tokens

    return {
        "artifact_type": "shadow_memory_context_pack",
        "status": "pass",
        "entries": entries,
        "selected_candidate_ids": [entry["candidate_id"] for entry in entries],
        "negative_preference_blockers": blocker_ids,
        "omission_trace": omissions,
        "token_budget": token_budget,
        "token_estimate": used_tokens,
        "token_budget_retry_expansion_used": False,
        "runtime_connected": runtime_connected,
        "lab_isolated": True,
        "shadow_memory_context_pack_used": True,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "manager_context_injected": False,
    }


def _omission(candidate_id: str, reason: str) -> dict[str, str]:
    return {"candidate_id": candidate_id, "reason": reason}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_shadow_memory_context_pack"]
