from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import (
    NON_MUTATION_FLAGS,
    validate_memory_record_contract,
)
from app.memory.application.memory_feedback_projection import (
    project_feedback_event_to_shadow_controls,
)
from app.memory.application.memory_source_lookup_policy import lookup_memory_sources
from app.memory.application.memory_tool_facade_records import (
    find_public_record,
    scope_blockers,
    searchable_records,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.memory_tool_facade"
)

SUPPORTED_MEMORY_TOOLS = {
    "memory.search",
    "memory.get",
    "memory.source_lookup",
    "memory.propose",
    "memory.review",
}


def execute_memory_tool_call(
    *,
    tool_name: str,
    arguments: Mapping[str, Any],
    memory_records: list[Mapping[str, Any]],
    source_entries: list[Mapping[str, Any]] | None = None,
    feedback_targets: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if tool_name not in SUPPORTED_MEMORY_TOOLS:
        return _artifact(tool_name, "blocked", [f"tool.unsupported:{tool_name}"])
    if tool_name == "memory.search":
        return _search(arguments, memory_records)
    if tool_name == "memory.get":
        return _get(arguments, memory_records)
    if tool_name == "memory.source_lookup":
        return _source_lookup(arguments, source_entries or [])
    if tool_name == "memory.propose":
        return _propose(arguments)
    return _review(arguments, feedback_targets or [])


def _search(arguments: Mapping[str, Any], records: list[Mapping[str, Any]]) -> dict[str, Any]:
    blockers = scope_blockers(_mapping(arguments.get("scope_keys")))
    if blockers:
        return _artifact("memory.search", "blocked", blockers)
    scope_keys = _mapping(arguments.get("scope_keys"))
    consumer = str(arguments.get("consumer") or "")
    limit = int(arguments.get("limit") or 5)
    public = searchable_records(records, scope_keys, consumer, limit)
    return _artifact(
        "memory.search",
        "pass",
        [],
        selected_record_ids=[record["id"] for record in public],
        records=public,
    )


def _get(arguments: Mapping[str, Any], records: list[Mapping[str, Any]]) -> dict[str, Any]:
    blockers = scope_blockers(_mapping(arguments.get("scope_keys")))
    if blockers:
        return _artifact("memory.get", "blocked", blockers)
    scope_keys = _mapping(arguments.get("scope_keys"))
    memory_id = str(arguments.get("memory_id") or "")
    source_ref = str(arguments.get("source_ref") or "")
    record = find_public_record(records, scope_keys, memory_id, source_ref)
    if record is None:
        return _artifact("memory.get", "blocked", ["memory.not_found"])
    return _artifact("memory.get", "pass", [], record=record)


def _source_lookup(
    arguments: Mapping[str, Any], source_entries: list[Mapping[str, Any]]
) -> dict[str, Any]:
    result = lookup_memory_sources(
        source_entries=source_entries,
        scope_keys=_mapping(arguments.get("scope_keys")),
        source_refs=[str(ref) for ref in arguments.get("source_refs", []) if ref],
        tool_path=str(arguments.get("tool_path") or "manager_default"),
        max_evidence_chars=int(arguments.get("max_evidence_chars") or 160),
        semantic_query=arguments.get("semantic_query"),
    )
    return _artifact(
        "memory.source_lookup",
        str(result.get("status") or "blocked"),
        list(result.get("blockers") or []),
        tool_result=result,
    )


def _propose(arguments: Mapping[str, Any]) -> dict[str, Any]:
    record = _mapping(arguments.get("memory_record"))
    validation = validate_memory_record_contract(record)
    if validation["blockers"]:
        return _artifact("memory.propose", "blocked", list(validation["blockers"]))
    candidate = validation["normalized_record"]
    return _artifact(
        "memory.propose",
        "pass",
        [],
        candidate=candidate,
        candidate_review_required=True,
        confirmed_memory_promoted=False,
    )


def _review(
    arguments: Mapping[str, Any], feedback_targets: list[Mapping[str, Any]]
) -> dict[str, Any]:
    result = project_feedback_event_to_shadow_controls(
        feedback_event=_mapping(arguments.get("feedback_event")),
        targets=feedback_targets,
    )
    return _artifact(
        "memory.review",
        str(result.get("status") or "blocked"),
        list(result.get("blockers") or []),
        tool_result=result,
    )


def _artifact(
    tool_name: str, status: str, blockers: list[str], **extra: Any
) -> dict[str, Any]:
    return {
        "artifact_type": "memory_tool_facade_call",
        "tool_name": tool_name,
        "status": status,
        "blockers": blockers,
        "raw_transcript_included": False,
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        **extra,
        **NON_MUTATION_FLAGS,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "SUPPORTED_MEMORY_TOOLS",
    "execute_memory_tool_call",
]
