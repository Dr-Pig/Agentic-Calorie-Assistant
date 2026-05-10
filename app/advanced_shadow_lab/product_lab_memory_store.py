from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_lifecycle import (
    CLOSED_STATES,
    correct_memory_record,
    delete_memory_record,
    forget_memory_record,
    history,
    history_event,
)
from app.advanced_shadow_lab.product_lab_memory_records import (
    record_from_event,
    segment_blockers,
)
from app.advanced_shadow_lab.product_lab_memory_surfaces import write_memory_surfaces
from app.advanced_shadow_lab.product_lab_memory_write_artifact import (
    memory_write_artifact,
)
from app.advanced_shadow_lab.product_lab_session_store import session_dir
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


class ProductLabMemoryStore:
    def __init__(self, artifact_root: Path | str) -> None:
        self.artifact_root = Path(artifact_root)

    def write_memory_events(
        self,
        *,
        session_id: str,
        turn_id: str,
        events: list[Mapping[str, Any]],
    ) -> dict[str, Any]:
        blockers = segment_blockers(session_id=session_id, turn_id=turn_id)
        existing = self.list_records(session_id)
        records_by_id = {str(record["record_id"]): record for record in existing}
        written_ids: list[str] = []
        for event in events:
            record, record_blockers = record_from_event(
                event,
                session_id=session_id,
                turn_id=turn_id,
            )
            blockers.extend(record_blockers)
            if record_blockers:
                continue
            previous = records_by_id.get(str(record["record_id"]))
            record["history"] = history(previous) + [
                history_event(
                    "write",
                    turn_id=turn_id,
                    source_object_refs=record.get("source_object_refs") or [],
                )
            ]
            records_by_id[str(record["record_id"])] = record
            written_ids.append(str(record["record_id"]))
        records = sorted(records_by_id.values(), key=lambda item: str(item["record_id"]))
        if not blockers:
            self._persist_records(session_id, records, turn_id=turn_id)
        return memory_write_artifact(
            blockers=blockers,
            written_record_ids=written_ids,
            all_record_ids=[str(record["record_id"]) for record in records],
            surface_paths=self.surface_paths(session_id) if not blockers else {},
        )

    def list_records(self, session_id: str) -> list[dict[str, Any]]:
        path = self._records_path(session_id)
        if not path.exists():
            return []
        payload = read_json_artifact(path)
        return [
            dict(item)
            for item in payload.get("records") or []
            if isinstance(item, Mapping)
        ]

    def read_memory(self, session_id: str, memory_id: str) -> dict[str, Any] | None:
        record = self._record_by_id(session_id, memory_id)
        if record is None or record.get("record_state") in CLOSED_STATES:
            return None
        return record

    def record_history(self, session_id: str, memory_id: str) -> list[dict[str, Any]]:
        record = self._record_by_id(session_id, memory_id)
        return history(record)

    def correct_memory(
        self,
        *,
        session_id: str,
        turn_id: str,
        memory_id: str,
        summary: str,
        source_object_refs: list[str],
        reason: str,
    ) -> dict[str, Any]:
        return correct_memory_record(
            self,
            session_id=session_id,
            turn_id=turn_id,
            memory_id=memory_id,
            summary=summary,
            source_object_refs=source_object_refs,
            reason=reason,
        )

    def delete_memory(
        self,
        *,
        session_id: str,
        turn_id: str,
        memory_id: str,
        reason: str,
    ) -> dict[str, Any]:
        return delete_memory_record(
            self,
            session_id=session_id,
            turn_id=turn_id,
            memory_id=memory_id,
            reason=reason,
        )

    def forget_memory(
        self,
        *,
        session_id: str,
        turn_id: str,
        memory_id: str,
        reason: str,
    ) -> dict[str, Any]:
        return forget_memory_record(
            self,
            session_id=session_id,
            turn_id=turn_id,
            memory_id=memory_id,
            reason=reason,
        )

    def surface_paths(self, session_id: str) -> dict[str, Path]:
        root = self._memory_dir(session_id)
        return {
            "user_md": root / "user.md",
            "memory_md": root / "memory.md",
            "source_md": root / "source.md",
            "sources_jsonl": root / "sources.jsonl",
            "daily_md": root / "daily" / "lab-day.md",
            "review_md": root / "review.md",
            "conversation_archive_jsonl": root / "conversation_archive.jsonl",
        }

    def _memory_dir(self, session_id: str) -> Path:
        return session_dir(
            artifact_root=self.artifact_root,
            session_id=session_id,
        ) / "memory"

    def _records_path(self, session_id: str) -> Path:
        return self._memory_dir(session_id) / "records.json"

    def _record_by_id(self, session_id: str, memory_id: str) -> dict[str, Any] | None:
        for record in self.list_records(session_id):
            if str(record.get("record_id") or "") == str(memory_id):
                return record
        return None

    def _persist_records(
        self,
        session_id: str,
        records: list[Mapping[str, Any]],
        *,
        turn_id: str,
    ) -> None:
        write_json_artifact(self._records_path(session_id), {"records": list(records)})
        write_memory_surfaces(
            self.surface_paths(session_id),
            list(records),
            turn_id=turn_id,
        )

__all__ = ["ProductLabMemoryStore"]
