from __future__ import annotations

from typing import Any, Mapping


def build_manager_selected_rescue_artifact(
    manager_tool_loop_artifact: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(manager_tool_loop_artifact, Mapping):
        return None
    for result in manager_tool_loop_artifact.get("tool_result_trace") or []:
        if not isinstance(result, Mapping):
            continue
        if str(result.get("tool_name") or "") != "rescue.run":
            continue
        artifact = _mapping(result.get("result_artifact"))
        if not artifact:
            return None
        return {
            "artifact_type": "advanced_product_lab_manager_selected_rescue_artifact",
            "artifact_schema_version": "1.0",
            "status": str(artifact.get("status") or "blocked"),
            "source_call_id": str(result.get("call_id") or ""),
            "proposal_presented_to_lab": artifact.get("proposal_presented_to_lab") is True,
            "primary_actions": [str(item) for item in artifact.get("primary_actions") or []],
            "negotiation_affordances": [
                str(item) for item in artifact.get("negotiation_affordances") or []
            ],
            "pending_rescue_commit_packet": dict(
                _mapping(artifact.get("pending_rescue_commit_packet"))
            ),
            "raw_transcript_included": False,
            "blockers": [str(blocker) for blocker in artifact.get("blockers") or []],
        }
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_manager_selected_rescue_artifact"]
