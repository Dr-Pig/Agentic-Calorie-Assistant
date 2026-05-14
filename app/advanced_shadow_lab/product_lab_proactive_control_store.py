from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_session_store import (
    session_dir,
    unsafe_segment_blocker,
)
from app.shared.infra.json_artifacts import (
    artifact_path_exists,
    read_json_artifact,
    write_json_artifact,
)


class ProductLabProactiveControlStore:
    def __init__(self, artifact_root: Path | str) -> None:
        self._artifact_root = Path(artifact_root)

    def journal_path(self, *, session_id: str) -> Path:
        blocker = unsafe_segment_blocker("session_id", session_id)
        if blocker:
            raise ValueError(blocker)
        return (
            session_dir(artifact_root=self._artifact_root, session_id=session_id)
            / "proactive_control_store.json"
        )

    def read_journal(self, *, session_id: str) -> list[dict[str, Any]]:
        path = self.journal_path(session_id=session_id)
        if not artifact_path_exists(path):
            return []
        artifact = read_json_artifact(path)
        return [
            dict(entry)
            for entry in artifact.get("journal_entries") or []
            if isinstance(entry, Mapping)
        ]

    def write_journal(
        self,
        *,
        session_id: str,
        journal_entries: list[Mapping[str, Any]],
    ) -> dict[str, Any]:
        entries = [dict(entry) for entry in journal_entries]
        path = self.journal_path(session_id=session_id)
        artifact = {
            "artifact_type": "advanced_product_lab_proactive_control_store",
            "artifact_schema_version": "1.0",
            "status": "pass",
            "session_id": session_id,
            "artifact_path": str(path),
            "journal_entry_count": len(entries),
            "journal_entries": entries,
            "lab_isolated": True,
            "mainline_activation_enabled": False,
            "mainline_runtime_connected": False,
            "scheduler_delivery_allowed": False,
            "production_scheduler_delivery_allowed": False,
            "notification_delivery_allowed": False,
            "canonical_product_mutation_allowed": False,
            "durable_product_memory_written": False,
            "raw_user_text_semantic_inference_performed": False,
            **dict(FALSE_FLAGS),
        }
        write_json_artifact(path, artifact)
        return artifact


__all__ = ["ProductLabProactiveControlStore"]
