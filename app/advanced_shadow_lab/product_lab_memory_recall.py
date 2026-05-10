from __future__ import annotations

import json
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore


def conversation_recall_search(
    *,
    store: ProductLabMemoryStore,
    session_id: str,
    query: str,
    limit: int,
) -> dict[str, Any]:
    rows = _archive_rows(store, session_id)
    query_terms = _terms(query)
    hits = [
        _hit(row, query_terms)
        for row in rows
        if _matches(row, query_terms)
    ][: max(limit, 0)]
    return {
        "artifact_type": "advanced_product_lab_conversation_recall",
        "status": "pass",
        "tool": "conversation_recall.search",
        "session_id": session_id,
        "query": query,
        "hits": hits,
        "raw_transcript_included": False,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
    }


def _archive_rows(
    store: ProductLabMemoryStore,
    session_id: str,
) -> list[Mapping[str, Any]]:
    path = store.surface_paths(session_id)["conversation_archive_jsonl"]
    if not path.exists():
        return []
    rows: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, Mapping):
            rows.append(payload)
    return rows


def _terms(value: str) -> list[str]:
    return [term.lower() for term in str(value).split() if term.strip()]


def _matches(row: Mapping[str, Any], terms: list[str]) -> bool:
    if not terms:
        return False
    haystack = " ".join(
        [
            str(row.get("record_id") or ""),
            str(row.get("summary") or ""),
            " ".join(str(ref) for ref in row.get("source_object_refs") or []),
        ]
    ).lower()
    return all(term in haystack for term in terms)


def _hit(row: Mapping[str, Any], terms: list[str]) -> dict[str, Any]:
    return {
        "record_id": str(row.get("record_id") or ""),
        "summary": str(row.get("summary") or ""),
        "source_object_refs": [str(ref) for ref in row.get("source_object_refs") or []],
        "matched_terms": list(terms),
        "raw_transcript_included": False,
    }


__all__ = ["conversation_recall_search"]
