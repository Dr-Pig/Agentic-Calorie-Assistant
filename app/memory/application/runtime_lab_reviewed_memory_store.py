from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from app.memory.application.runtime_lab_store_paths import (
    require_scope,
    scope_dir,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_reviewed_memory_store"
)

CLAIM_FLAGS = (
    "runtime_effect_allowed",
    "durable_memory_written",
    "durable_product_memory_written",
    "canonical_mutation_changed",
    "manager_context_injected",
    "manager_context_packet_changed",
)


class RuntimeLabReviewedMemoryStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def write_review_loop_state(self, artifact: Mapping[str, Any]) -> dict[str, Any]:
        records = [item for item in artifact.get("lab_memory_records") or [] if isinstance(item, Mapping)]
        written = [self.write_record({**record, "store_write_order": index}) for index, record in enumerate(records)]
        return {
            "artifact_type": "runtime_lab_reviewed_memory_store_write",
            "status": "pass",
            "stored_record_count": sum(1 for record in written if not record["deleted"]),
            "tombstone_record_count": sum(1 for record in written if record["record_state"] == "deleted_shadow"),
            "record_ids": [record["memory_record_id"] for record in written],
            "lab_isolated": True,
            "canonical_db_changed": False,
            "durable_product_memory_written": False,
            "manager_context_packet_changed": False,
        }

    def write_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        self._reject_claim_drift(record)
        memory_record_id = str(record.get("memory_record_id") or "")
        if not memory_record_id:
            raise ValueError("missing_memory_record_id")
        scope_keys = require_scope(_mapping(record.get("scope_keys")))
        path = _record_path(self.root, scope_keys, memory_record_id)
        existing = _read_existing(path)
        version = int(existing.get("store_version") or 0) + 1
        history = [
            *existing.get("history", []),
            _history_event(version, "write", record),
        ]
        stored = {
            "record_type": "runtime_lab_reviewed_memory_record",
            "memory_record_id": memory_record_id,
            "store_version": version,
            "deleted": False,
            "source_candidate_id": str(record.get("source_candidate_id") or ""),
            "source_action_id": str(record.get("source_action_id") or ""),
            "record_state": str(record.get("record_state") or ""),
            "review_revision": record.get("revision"),
            "store_write_order": record.get("store_write_order", existing.get("store_write_order", 0)),
            "memory_text": record.get("memory_text"),
            "candidate_type": str(record.get("candidate_type") or ""),
            "scope_keys": scope_keys,
            "intended_consumers": list(record.get("intended_consumers") or []),
            "active_in_lab_context": bool(record.get("active_in_lab_context")),
            "can_be_runtime_loaded": False,
            "runtime_effect_allowed": False,
            "durable_memory_written": False,
            "durable_product_memory_written": False,
            "canonical_mutation_changed": False,
            "manager_context_injected": False,
            "manager_context_packet_changed": False,
            "audit_provenance_retained": bool(record.get("audit_provenance_retained")),
            "provenance": dict(_mapping(record.get("provenance"))),
            "audit_log": list(record.get("audit_log") or []),
            "history": history,
            "lab_isolated": True,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_artifact(path, stored)
        return stored

    def read_record(self, memory_record_id: str, scope_keys: Mapping[str, Any]) -> dict[str, Any] | None:
        path = _record_path(self.root, scope_keys, memory_record_id)
        if not path.exists():
            return None
        record = read_json_artifact(path)
        return None if record.get("deleted") is True else record

    def list_records(self, scope_keys: Mapping[str, Any]) -> list[dict[str, Any]]:
        directory = _reviewed_dir(self.root, scope_keys)
        if not directory.exists():
            return []
        return [
            record
            for record in sorted(
                (read_json_artifact(path) for path in directory.glob("*.json")),
                key=lambda item: (int(item.get("store_write_order") or 0), str(item.get("source_candidate_id") or "")),
            )
            if record.get("deleted") is not True
        ]

    def record_history(self, memory_record_id: str, scope_keys: Mapping[str, Any]) -> list[dict[str, Any]]:
        path = _record_path(self.root, scope_keys, memory_record_id)
        if not path.exists():
            return []
        return list(read_json_artifact(path).get("history", []))

    def forget_record(
        self,
        memory_record_id: str,
        scope_keys: Mapping[str, Any],
        *,
        reason: str,
    ) -> dict[str, Any]:
        resolved_scope = require_scope(scope_keys)
        path = _record_path(self.root, resolved_scope, memory_record_id)
        existing = _read_existing(path)
        version = int(existing.get("store_version") or 0) + 1
        history = [
            *existing.get("history", []),
            {
                "store_version": version,
                "action": "forget",
                "record_state": "deleted_shadow",
                "review_revision": None,
                "reason": reason,
            },
        ]
        tombstone = {
            "record_type": "runtime_lab_reviewed_memory_tombstone",
            "memory_record_id": memory_record_id,
            "store_version": version,
            "deleted": True,
            "record_state": "deleted_shadow",
            "memory_text": None,
            "scope_keys": resolved_scope,
            "history": history,
            "lab_isolated": True,
            "canonical_db_changed": False,
            "durable_product_memory_written": False,
            "manager_context_packet_changed": False,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_artifact(path, tombstone)
        return tombstone

    @staticmethod
    def _reject_claim_drift(record: Mapping[str, Any]) -> None:
        for flag in CLAIM_FLAGS:
            if record.get(flag) is True:
                raise ValueError(f"activation_flag_not_allowed:{flag}")


def _record_path(root: Path, scope_keys: Mapping[str, Any], memory_record_id: str) -> Path:
    return _reviewed_dir(root, scope_keys) / f"{_safe_id(memory_record_id)}.json"


def _reviewed_dir(root: Path, scope_keys: Mapping[str, Any]) -> Path:
    return scope_dir(root, scope_keys) / "reviewed_memory"


def _history_event(version: int, action: str, record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "store_version": version,
        "action": action,
        "record_state": str(record.get("record_state") or ""),
        "review_revision": record.get("revision"),
        "source_action_id": str(record.get("source_action_id") or ""),
    }


def _read_existing(path: Path) -> dict[str, Any]:
    return read_json_artifact(path) if path.exists() else {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_id(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in value)
    if len(safe) <= 32:
        return safe
    digest = sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{safe[:20]}-{digest}"


__all__ = ["RuntimeLabReviewedMemoryStore", "SIDECAR_ACTIVATION_CONTRACT"]
