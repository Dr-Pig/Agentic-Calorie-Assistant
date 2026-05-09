from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.memory.application.runtime_lab_store_paths import (
    candidate_path,
    require_scope,
    scope_dir,
    scope_manifest,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_store"
)


class RuntimeLabMemoryStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def write_candidate(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id:
            raise ValueError("missing_candidate_id")
        scope_keys = require_scope(_mapping(candidate.get("scope_keys")))
        path = candidate_path(self.root, scope_keys, candidate_id)
        existing = _read_existing(path)
        version = int(existing.get("version") or 0) + 1
        history = [*existing.get("history", []), _history_event(version, candidate)]
        record = {
            "record_type": "runtime_lab_memory_candidate_record",
            "candidate_id": candidate_id,
            "version": version,
            "deleted": False,
            "scope_keys": scope_keys,
            "candidate": dict(candidate),
            "review_status": str(candidate.get("review_status") or "pending"),
            "retention_posture": str(
                candidate.get("retention_posture") or "runtime_lab_shadow_only"
            ),
            "source_object_refs": list(candidate.get("source_object_refs", [])),
            "history": history,
            "lab_isolated": True,
            "canonical_db_changed": False,
            "durable_product_memory_written": False,
            "manager_context_packet_changed": False,
        }
        write_json_artifact(path, record)
        return record

    def read_candidate(
        self,
        candidate_id: str,
        scope_keys: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        path = candidate_path(self.root, scope_keys, candidate_id)
        if not path.exists():
            return None
        record = read_json_artifact(path)
        if record.get("deleted") is True:
            return None
        return record

    def list_candidates(self, scope_keys: Mapping[str, Any]) -> list[dict[str, Any]]:
        directory = scope_dir(self.root, scope_keys)
        if not directory.exists():
            return []
        records = []
        for path in sorted(directory.glob("*.json")):
            record = read_json_artifact(path)
            if record.get("deleted") is not True:
                records.append(record)
        return records

    def candidate_history(
        self,
        candidate_id: str,
        scope_keys: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        path = candidate_path(self.root, scope_keys, candidate_id)
        if not path.exists():
            return []
        return list(read_json_artifact(path).get("history", []))

    def forget_candidate(
        self,
        candidate_id: str,
        scope_keys: Mapping[str, Any],
        *,
        reason: str,
    ) -> dict[str, Any]:
        resolved_scope = require_scope(scope_keys)
        path = candidate_path(self.root, resolved_scope, candidate_id)
        existing = _read_existing(path)
        version = int(existing.get("version") or 0) + 1
        history = [
            *existing.get("history", []),
            {
                "version": version,
                "action": "forget",
                "review_status": "deleted",
                "source_object_refs": [],
                "reason": reason,
            },
        ]
        tombstone = {
            "record_type": "runtime_lab_memory_candidate_tombstone",
            "candidate_id": candidate_id,
            "version": version,
            "deleted": True,
            "delete_reason": reason,
            "scope_keys": resolved_scope,
            "candidate": None,
            "history": history,
            "lab_isolated": True,
            "canonical_db_changed": False,
            "durable_product_memory_written": False,
            "manager_context_packet_changed": False,
        }
        write_json_artifact(path, tombstone)
        return tombstone

    def store_manifest(self, scope_keys: Mapping[str, Any]) -> dict[str, Any]:
        resolved_scope = scope_manifest(scope_keys)
        return {
            "store_root": str(self.root),
            "scope_keys": resolved_scope,
            "scope_dir": str(scope_dir(self.root, resolved_scope)),
            "lab_isolated": True,
            "canonical_db_changed": False,
        }


def _read_existing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json_artifact(path)


def _history_event(version: int, candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": version,
        "action": "write",
        "review_status": str(candidate.get("review_status") or "pending"),
        "source_object_refs": list(candidate.get("source_object_refs", [])),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


__all__ = ["RuntimeLabMemoryStore", "SIDECAR_ACTIVATION_CONTRACT"]
