from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_records import (
    ACCEPTED_REVIEW_STATUSES,
    mapping,
)


def write_memory_surfaces(
    paths: Mapping[str, Path],
    records: list[Mapping[str, Any]],
    *,
    turn_id: str,
) -> None:
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    accepted = [
        record
        for record in records
        if record.get("review_status") in ACCEPTED_REVIEW_STATUSES
    ]
    paths["user_md"].write_text(_profile_markdown(accepted), encoding="utf-8")
    paths["memory_md"].write_text(_memory_markdown(records), encoding="utf-8")
    paths["source_md"].write_text(_source_markdown(records), encoding="utf-8")
    paths["review_md"].write_text(_review_markdown(records), encoding="utf-8")
    paths["daily_md"].write_text(_daily_markdown(records, turn_id=turn_id), encoding="utf-8")
    _write_jsonl(paths["sources_jsonl"], [_source_row(record) for record in records])
    _write_jsonl(
        paths["conversation_archive_jsonl"],
        [_archive_row(record) for record in records],
    )


def _profile_markdown(records: list[Mapping[str, Any]]) -> str:
    lines = ["# User Memory", "", "## Stable Preferences"]
    lines.extend(f"- {record['summary']}" for record in records)
    return "\n".join(lines).rstrip() + "\n"


def _memory_markdown(records: list[Mapping[str, Any]]) -> str:
    lines = ["# Product Lab Memory", ""]
    for record in records:
        lines.append(
            f"- `{record['record_id']}` ({record['memory_type']}): {record['summary']}"
        )
    return "\n".join(lines).rstrip() + "\n"


def _source_markdown(records: list[Mapping[str, Any]]) -> str:
    lines = ["# Memory Sources", ""]
    for record in records:
        refs = ", ".join(str(ref) for ref in record.get("source_object_refs") or [])
        lines.append(f"- `{record['record_id']}`: {refs}")
    return "\n".join(lines).rstrip() + "\n"


def _review_markdown(records: list[Mapping[str, Any]]) -> str:
    lines = ["# Memory Review", ""]
    for record in records:
        lines.append(f"- `{record['record_id']}`: {record['review_status']}")
    return "\n".join(lines).rstrip() + "\n"


def _daily_markdown(records: list[Mapping[str, Any]], *, turn_id: str) -> str:
    lines = ["# Lab Day Memory", "", f"Latest turn: `{turn_id}`", ""]
    lines.extend(f"- `{record['record_id']}`: {record['summary']}" for record in records)
    return "\n".join(lines).rstrip() + "\n"


def _source_row(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record.get("record_id"),
        "memory_type": record.get("memory_type"),
        "review_status": record.get("review_status"),
        "source_object_refs": list(record.get("source_object_refs") or []),
        "scope_keys": dict(mapping(record.get("scope_keys"))),
    }


def _archive_row(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record.get("record_id"),
        "summary": record.get("summary"),
        "source_object_refs": list(record.get("source_object_refs") or []),
    }


def _write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(dict(row), ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


__all__ = ["write_memory_surfaces"]
