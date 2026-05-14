from __future__ import annotations

from typing import Any, Mapping

def control_session_fields(
    *,
    journal: list[Mapping[str, Any]],
    proactive_control_store_artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    control_store = dict(proactive_control_store_artifact or {})
    return {
        "final_control_journal_entries": [dict(entry) for entry in journal],
        "proactive_control_store_lab_isolated": (
            control_store.get("lab_isolated") is True
        ),
        "proactive_control_store_path": str(control_store.get("artifact_path") or ""),
    }


__all__ = ["control_session_fields"]
