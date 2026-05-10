from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_context import (
    build_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_memory_recall import conversation_recall_search
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.product_lab_session_store import unsafe_segment_blocker


SUPPORTED_TOOLS = {
    "memory.search",
    "memory.get",
    "conversation_recall.search",
}


def execute_product_lab_memory_tool_call(
    *,
    store: ProductLabMemoryStore,
    session_id: str,
    turn_id: str,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = _scope_blockers(session_id=session_id, turn_id=turn_id)
    if tool_name not in SUPPORTED_TOOLS:
        blockers.append(f"tool.unsupported:{tool_name}")
    if blockers:
        return _artifact(tool_name=tool_name, status="blocked", blockers=blockers)
    if tool_name == "memory.search":
        return _search(store, session_id, turn_id, arguments)
    if tool_name == "memory.get":
        return _get(store, session_id, turn_id, arguments)
    return _recall(store, session_id, arguments)


def _search(
    store: ProductLabMemoryStore,
    session_id: str,
    turn_id: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    pack = build_product_lab_memory_context_pack(
        store=store,
        session_id=session_id,
        turn_id=turn_id,
        consumers=[str(item) for item in arguments.get("consumers") or []],
        token_budget=int(arguments.get("token_budget") or 120),
    )
    return _artifact(
        tool_name="memory.search",
        status=str(pack.get("status") or "blocked"),
        selected_record_ids=list(pack.get("selected_record_ids") or []),
        context_pack=pack,
        blockers=list(pack.get("blockers") or []),
    )


def _get(
    store: ProductLabMemoryStore,
    session_id: str,
    turn_id: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    memory_id = str(arguments.get("memory_id") or "")
    id_blocker = unsafe_segment_blocker("memory_id", memory_id)
    record = None if id_blocker else store.read_memory(session_id, memory_id)
    blockers = [id_blocker] if id_blocker else []
    if record is None and not blockers:
        blockers.append("memory_id.not_found")
    return _artifact(
        tool_name="memory.get",
        status="blocked" if blockers else "pass",
        record=_public_record(record or {}, turn_id=turn_id),
        blockers=[str(blocker) for blocker in blockers if blocker],
    )


def _recall(
    store: ProductLabMemoryStore,
    session_id: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    recall = conversation_recall_search(
        store=store,
        session_id=session_id,
        query=str(arguments.get("query") or ""),
        limit=int(arguments.get("limit") or 5),
    )
    return _artifact(
        tool_name="conversation_recall.search",
        status=str(recall.get("status") or "blocked"),
        hits=list(recall.get("hits") or []),
        blockers=list(recall.get("blockers") or []),
    )


def _public_record(record: Mapping[str, Any], *, turn_id: str) -> dict[str, Any]:
    return {
        "record_id": str(record.get("record_id") or ""),
        "memory_type": str(record.get("memory_type") or ""),
        "summary": str(record.get("summary") or ""),
        "review_status": str(record.get("review_status") or ""),
        "record_state": str(record.get("record_state") or "active_lab"),
        "source_object_refs": [str(ref) for ref in record.get("source_object_refs") or []],
        "turn_id": turn_id,
        "raw_transcript_included": False,
    }


def _artifact(tool_name: str, status: str, blockers: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_memory_tool_call_artifact",
        "status": status,
        "tool_name": tool_name,
        **extra,
        "raw_transcript_included": False,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
    }


def _scope_blockers(*, session_id: str, turn_id: str) -> list[str]:
    blockers: list[str] = []
    for name, value in (("session_id", session_id), ("turn_id", turn_id)):
        if not value or unsafe_segment_blocker(name, value):
            blockers.append(f"{name}.missing_or_unsafe")
    return blockers


__all__ = ["SUPPORTED_TOOLS", "execute_product_lab_memory_tool_call"]
