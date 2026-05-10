from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_action_projection import (
    memory_action_projection_from_context,
)
from app.advanced_shadow_lab.product_lab_memory_records import (
    ACCEPTED_REVIEW_STATUSES,
    DEFAULT_CONSUMERS,
    context_entry,
    scope_keys,
    segment_blockers,
    token_estimate,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore


def build_product_lab_memory_context_pack(
    *,
    store: ProductLabMemoryStore,
    session_id: str,
    turn_id: str,
    consumers: list[str] | tuple[str, ...] = DEFAULT_CONSUMERS,
    token_budget: int,
    lab_now_minute: int = 0,
) -> dict[str, Any]:
    blockers = segment_blockers(session_id=session_id, turn_id=turn_id)
    selected: list[dict[str, Any]] = []
    omissions: list[dict[str, str]] = []
    used_tokens = 0
    if not blockers:
        allowed_consumers = set(consumers)
        for record in store.list_records(session_id):
            entry = context_entry(record)
            reason = _omission_reason(
                entry,
                record,
                allowed_consumers,
                lab_now_minute=lab_now_minute,
            )
            if reason:
                omissions.append({"record_id": entry["record_id"], "reason": reason})
                continue
            entry_tokens = token_estimate(entry)
            if used_tokens + entry_tokens > token_budget:
                omissions.append(
                    {"record_id": entry["record_id"], "reason": "token_budget_exceeded"}
                )
                continue
            selected.append(entry)
            used_tokens += entry_tokens
    return _context_pack(
        session_id=session_id,
        turn_id=turn_id,
        selected=selected,
        omissions=omissions,
        token_budget=token_budget,
        blockers=blockers,
        consumers=list(consumers),
        token_estimate_value=used_tokens,
    )


def empty_product_lab_memory_context_pack(*, session_id: str, turn_id: str) -> dict[str, Any]:
    return _context_pack(
        session_id=session_id,
        turn_id=turn_id,
        selected=[],
        omissions=[],
        token_budget=0,
        blockers=[],
        consumers=list(DEFAULT_CONSUMERS),
    )


def _context_pack(
    *,
    session_id: str,
    turn_id: str,
    selected: list[dict[str, Any]],
    omissions: list[dict[str, str]],
    token_budget: int,
    blockers: list[str],
    consumers: list[str],
    token_estimate_value: int = 0,
) -> dict[str, Any]:
    selected_ids = [str(entry["record_id"]) for entry in selected]
    return {
        "artifact_type": "advanced_product_lab_memory_context_pack",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "scope_keys": scope_keys(session_id),
        "session_id": session_id,
        "turn_id": turn_id,
        "requested_consumers": list(consumers),
        "entries": selected,
        "selected_record_ids": selected_ids,
        "negative_preference_blockers": [
            entry["record_id"] for entry in selected if entry.get("memory_type") == "negative_preference"
        ],
        "memory_action_projection": memory_action_projection_from_context(
            {"artifact_type": "advanced_product_lab_memory_context_pack", "entries": selected}
        ),
        "omission_trace": omissions,
        "token_budget": token_budget,
        "token_estimate": token_estimate_value,
        "memory_tools_enabled": True,
        "memory_tool_calls": [{"turn_id": turn_id, "tool": "memory.search", "selected_record_ids": selected_ids}],
        "memory_context_injected": bool(selected) and not blockers,
        "lab_manager_context_injected": bool(selected) and not blockers,
        "lab_memory_context_pack_used": bool(selected) and not blockers,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "mainline_runtime_connected": False,
        "production_db_migration_allowed": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "raw_transcript_included": False,
        "blockers": blockers,
    }


def _omission_reason(
    entry: Mapping[str, Any],
    record: Mapping[str, Any],
    allowed_consumers: set[str],
    *,
    lab_now_minute: int,
) -> str:
    record_state = str(entry.get("record_state") or record.get("record_state") or "")
    if record_state in {"archived_lab", "deleted_lab", "forgotten_lab"}:
        return record_state
    if entry.get("conflict_review_required") is True:
        return "conflict_review_required"
    if str(entry.get("freshness_posture") or "") in {"archived", "stale", "expired"}:
        return "stale_or_expired"
    valid_until = entry.get("valid_until_minute")
    if (
        isinstance(valid_until, int | float)
        and valid_until < lab_now_minute
    ):
        return "stale_or_expired"
    if record.get("review_status") not in ACCEPTED_REVIEW_STATUSES:
        return "not_accepted_lab"
    if not allowed_consumers.intersection(set(entry.get("intended_consumers") or [])):
        return "consumer_not_requested"
    return ""


__all__ = [
    "build_product_lab_memory_context_pack",
    "empty_product_lab_memory_context_pack",
]
