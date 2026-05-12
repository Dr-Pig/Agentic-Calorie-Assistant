from __future__ import annotations

import json
from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import (
    NON_MUTATION_FLAGS,
    validate_memory_record_contract,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.memory_surface_projection"
)

SURFACE_PATHS = [
    "user.md",
    "memory.md",
    "source.md",
    "sources.jsonl",
    "review.md",
]


def build_memory_surface_projection(
    *, memory_records: list[Mapping[str, Any]]
) -> dict[str, Any]:
    blockers = _record_blockers(memory_records)
    if blockers:
        return _artifact(status="blocked", blockers=blockers, surfaces={})

    records = [
        validate_memory_record_contract(record)["normalized_record"]
        for record in memory_records
    ]
    surfaces = {
        "user_md": _user_md(records),
        "memory_md": _memory_md(records),
        "source_md": _source_md(records),
        "sources_jsonl": _sources_jsonl(records),
        "review_md": _review_md(records),
    }
    return _artifact(status="pass", blockers=[], surfaces=surfaces)


def _record_blockers(records: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for record in records:
        record_id = str(record.get("id") or "memory_record")
        validation = validate_memory_record_contract(record)
        blockers.extend(f"{record_id}.{item}" for item in validation["blockers"])
    return blockers


def _user_md(records: list[Mapping[str, Any]]) -> str:
    confirmed = [record for record in records if record.get("status") == "confirmed"]
    positive = [record for record in confirmed if record.get("polarity") == "positive"]
    negative = [record for record in confirmed if record.get("polarity") == "negative"]
    lines = ["# User Memory", "", "## Stable Preferences"]
    lines.extend(_surface_line(record) for record in positive)
    lines.extend(["", "## Avoid / Downrank"])
    lines.extend(_surface_line(record) for record in negative)
    return _finish(lines)


def _memory_md(records: list[Mapping[str, Any]]) -> str:
    lines = ["# Memory Summary", ""]
    lines.extend(_surface_line(record) for record in records)
    return _finish(lines)


def _source_md(records: list[Mapping[str, Any]]) -> str:
    lines = ["# Memory Sources", ""]
    for record in records:
        refs = ", ".join(str(ref) for ref in record.get("source_refs", []))
        lines.append(f"- `{record['id']}`: {refs}")
    return _finish(lines)


def _review_md(records: list[Mapping[str, Any]]) -> str:
    lines = ["# Memory Review", ""]
    review_records = [record for record in records if record.get("status") != "confirmed"]
    if not review_records:
        lines.append("- No pending review items.")
    else:
        lines.extend(
            f"- `{record['id']}` ({record['status']}): {record['summary']}"
            for record in review_records
        )
    return _finish(lines)


def _sources_jsonl(records: list[Mapping[str, Any]]) -> str:
    rows: list[str] = []
    for record in records:
        for source_ref in record.get("source_refs", []):
            rows.append(json.dumps(_source_row(record, str(source_ref)), ensure_ascii=False))
    return "".join(f"{row}\n" for row in rows)


def _source_row(record: Mapping[str, Any], source_ref: str) -> dict[str, Any]:
    return {
        "source_ref": source_ref,
        "record_id": record.get("id"),
        "record_type": record.get("record_type"),
        "scope_keys": dict(_mapping(record.get("scope_keys"))),
        "metadata": {
            "family": record.get("family"),
            "status": record.get("status"),
            "polarity": record.get("polarity"),
            "strength": record.get("strength"),
            "validity": record.get("validity"),
        },
    }


def _surface_line(record: Mapping[str, Any]) -> str:
    return (
        f"- `{record['id']}` [{record['record_type']}/"
        f"{record['polarity']}/{record['strength']}]: {record['summary']}"
    )


def _finish(lines: list[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"


def _artifact(
    *, status: str, blockers: list[str], surfaces: dict[str, str]
) -> dict[str, Any]:
    return {
        "artifact_type": "memory_surface_projection",
        "status": status,
        "blockers": blockers,
        "surfaces": surfaces,
        "surface_paths_declared": list(SURFACE_PATHS),
        "raw_source_dump_included": False,
        "memory_md_is_runtime_truth": False,
        **NON_MUTATION_FLAGS,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "SURFACE_PATHS",
    "build_memory_surface_projection",
]
