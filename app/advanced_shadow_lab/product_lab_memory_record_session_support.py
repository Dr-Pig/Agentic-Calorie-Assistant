from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_record_context_pack import (
    build_memory_record_context_pack,
)


def memory_write(turn_spec: Mapping[str, Any], *, session_id: str) -> dict[str, Any]:
    confirmed = _confirmed_review_ids(turn_spec)
    records: list[dict[str, Any]] = []
    pending: list[str] = []
    blockers: list[str] = []
    for signal in _signals(turn_spec):
        signal_id = str(signal.get("signal_id") or "")
        if signal_id not in confirmed:
            pending.append(signal_id)
            continue
        record = _record(signal, session_id=session_id)
        if record["blockers"]:
            blockers.extend(f"{signal_id}.{item}" for item in record["blockers"])
            continue
        records.append(record["record"])
    return {
        "artifact_type": "advanced_product_lab_memory_record_write_artifact",
        "status": "blocked" if blockers else "pass",
        "promoted_record_ids": [str(record["id"]) for record in records],
        "written_record_ids": [str(record["id"]) for record in records],
        "pending_or_rejected_signal_ids": pending,
        "records": records,
        "blockers": blockers,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
    }


def memory_context_pack(
    session_id: str,
    turn_id: str,
    records: list[Mapping[str, Any]],
) -> dict[str, Any]:
    pack = build_memory_record_context_pack(
        memory_records=records,
        scope_keys=scope(session_id),
        consumer="recommendation_shadow",
        token_budget=180,
    )
    return {**pack, "turn_id": turn_id}


def tool_call(turn_id: str, context_pack: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "turn_id": turn_id,
        "tool": "memory.search",
        "selected_record_ids": list(context_pack.get("selected_record_ids") or []),
    }


def scope(session_id: str) -> dict[str, str]:
    return {
        "user_id": "advanced-product-lab-user",
        "workspace_id": "advanced-product-lab-workspace",
        "project_id": "advanced-product-lab",
        "surface": "chat",
        "session_id": session_id,
    }


def _record(signal: Mapping[str, Any], *, session_id: str) -> dict[str, Any]:
    record_type = str(signal.get("signal_type") or "")
    record = {
        "id": str(signal.get("signal_id") or ""),
        "record_type": record_type,
        "family": "diet_product",
        "status": "confirmed",
        "summary": str(signal.get("summary") or ""),
        "polarity": "negative" if record_type == "negative_preference" else "positive",
        "strength": "block" if record_type == "negative_preference" else "boost",
        "scope_keys": scope(session_id),
        "source_refs": [str(ref) for ref in signal.get("source_object_refs") or []],
        "consumers": _shadow_consumers(signal),
        "history": [f"review:{signal.get('signal_id') or ''}"],
        "subject_keys": _subject_keys(signal),
        "store_name": str(signal.get("store_name") or ""),
        "item_names": [str(item) for item in signal.get("item_names") or []],
        "estimated_kcal": signal.get("estimated_kcal"),
    }
    return {"record": record, "blockers": _record_blockers(record)}


def _record_blockers(record: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key in ("id", "record_type", "summary"):
        if not record.get(key):
            blockers.append(f"{key}.missing")
    if not record.get("source_refs"):
        blockers.append("source_refs.missing")
    return blockers


def _confirmed_review_ids(turn_spec: Mapping[str, Any]) -> set[str]:
    return {
        str(item.get("candidate_id") or "")
        for item in turn_spec.get("post_turn_memory_review_decisions") or []
        if isinstance(item, Mapping)
        and item.get("decision") == "promote"
        and item.get("confirmed") is True
    }


def _signals(turn_spec: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in turn_spec.get("post_turn_memory_signal_events") or []
        if isinstance(item, Mapping)
    ]


def _subject_keys(signal: Mapping[str, Any]) -> list[str]:
    return [
        str(item)
        for item in [
            *list(signal.get("item_names") or []),
            *list(signal.get("blocked_item_patterns") or []),
        ]
        if str(item)
    ]


def _shadow_consumers(signal: Mapping[str, Any]) -> list[str]:
    mapped = {
        "recommendation": "recommendation_shadow",
        "rescue": "rescue_shadow",
        "proactive": "proactive_shadow",
    }
    return [
        mapped[str(item)]
        for item in signal.get("intended_consumers") or []
        if str(item) in mapped
    ] or ["recommendation_shadow"]


__all__ = [
    "memory_context_pack",
    "memory_write",
    "tool_call",
]
