from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import NON_MUTATION_FLAGS
from app.memory.application.runtime_lab_store_paths import require_scope
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.memory_source_lookup_policy"
)

EVIDENCE_TOOL_PATHS = {"review", "debug", "why_memory"}


def lookup_memory_sources(
    *,
    source_entries: list[Mapping[str, Any]],
    scope_keys: Mapping[str, Any],
    source_refs: list[str],
    tool_path: str,
    max_evidence_chars: int = 160,
    semantic_query: str | None = None,
) -> dict[str, Any]:
    request_blockers = _request_blockers(scope_keys, source_refs, semantic_query)
    if request_blockers:
        return _artifact(
            status="blocked",
            blockers=request_blockers,
            results=[],
            omission_trace=[],
            tool_path=tool_path,
        )

    resolved_scope = require_scope(scope_keys)
    selected_refs = {str(ref) for ref in source_refs if str(ref)}
    evidence_allowed = tool_path in EVIDENCE_TOOL_PATHS
    blockers: list[str] = []
    results: list[dict[str, Any]] = []
    omissions: list[dict[str, str]] = []

    for entry in source_entries:
        source_ref = str(entry.get("source_ref") or "")
        if source_ref not in selected_refs:
            continue
        if not _scope_matches(entry, resolved_scope):
            omissions.append(_omission(source_ref, "scope_mismatch"))
            continue
        if entry.get("prompt_material_risk") is True:
            blockers.append(f"{source_ref}.prompt_material_risk")
            continue
        results.append(_result(entry, evidence_allowed, max_evidence_chars))

    if blockers:
        return _artifact(
            status="blocked",
            blockers=blockers,
            results=[],
            omission_trace=omissions,
            tool_path=tool_path,
        )
    return _artifact(
        status="pass",
        blockers=[],
        results=results,
        omission_trace=omissions,
        tool_path=tool_path,
    )


def _request_blockers(
    scope_keys: Mapping[str, Any],
    source_refs: list[str],
    semantic_query: str | None,
) -> list[str]:
    blockers: list[str] = []
    try:
        require_scope(scope_keys)
    except ValueError as exc:
        blockers.append(str(exc))
    if not [ref for ref in source_refs if str(ref)]:
        blockers.append("source_ref_filter_required")
        if semantic_query:
            blockers.append("semantic_query_not_allowed_without_source_refs")
    return blockers


def _scope_matches(entry: Mapping[str, Any], scope_keys: Mapping[str, str]) -> bool:
    entry_scope = entry.get("scope_keys")
    if not isinstance(entry_scope, Mapping):
        return False
    return all(str(entry_scope.get(key) or "") == value for key, value in scope_keys.items())


def _result(
    entry: Mapping[str, Any], evidence_allowed: bool, max_evidence_chars: int
) -> dict[str, Any]:
    source_ref = str(entry.get("source_ref") or "")
    return {
        "source_ref": source_ref,
        "record_id": str(entry.get("record_id") or ""),
        "source_kind": str(entry.get("source_kind") or ""),
        "metadata": _metadata(entry.get("metadata")),
        "bounded_evidence_span": (
            _bounded_evidence_span(entry, max_evidence_chars)
            if evidence_allowed
            else None
        ),
    }


def _bounded_evidence_span(
    entry: Mapping[str, Any], max_evidence_chars: int
) -> dict[str, Any]:
    raw_text = str(entry.get("evidence_text") or "")
    limit = max(0, max_evidence_chars)
    return {
        "start": 0,
        "end": min(len(raw_text), limit),
        "text": raw_text[:limit],
        "truncated": len(raw_text) > limit,
    }


def _metadata(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _omission(source_ref: str, reason: str) -> dict[str, str]:
    return {"source_ref": source_ref, "reason": reason}


def _artifact(
    *,
    status: str,
    blockers: list[str],
    results: list[dict[str, Any]],
    omission_trace: list[dict[str, str]],
    tool_path: str,
) -> dict[str, Any]:
    evidence_read = tool_path in EVIDENCE_TOOL_PATHS and bool(results)
    return {
        "artifact_type": "memory_source_lookup_policy_evaluation",
        "status": status,
        "blockers": blockers,
        "results": results,
        "omission_trace": omission_trace,
        "lookup_path": _lookup_path(tool_path),
        "bounded_evidence_read": evidence_read,
        "full_raw_transcript_allowed": False,
        "prompt_material_allowed": False,
        "general_rag_pool_used": False,
        **NON_MUTATION_FLAGS,
    }


def _lookup_path(tool_path: str) -> list[str]:
    path = ["source_ref_filter", "metadata_filter"]
    if tool_path in EVIDENCE_TOOL_PATHS:
        path.append("bounded_evidence_span")
    return path


__all__ = [
    "EVIDENCE_TOOL_PATHS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "lookup_memory_sources",
]
