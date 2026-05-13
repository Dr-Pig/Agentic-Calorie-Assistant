from __future__ import annotations

from typing import Any, Mapping


def append_audit_event_once(
    audit_events: list[dict[str, Any]],
    *,
    event_type: str,
    proposal_id: str,
    occurred_at: Any,
    artifact: Mapping[str, Any],
) -> None:
    if any(
        event["event_type"] == event_type and event["proposal_id"] == proposal_id
        for event in audit_events
    ):
        return
    audit_events.append(
        {
            "event_type": event_type,
            "proposal_id": proposal_id,
            "occurred_at": str(occurred_at or ""),
            "surface": str(_source_audit(artifact).get("surface") or ""),
            "source_event_id": str(_source_audit(artifact).get("source_event_id") or ""),
            "run_id": str(_source_audit(artifact).get("run_id") or ""),
            "summary": f"Rescue proposal {event_type}.",
            "raw_trace_exposed": False,
            "sidecar_diagnostic_exposed": False,
        }
    )


def _source_audit(artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    source = _mapping(_mapping(artifact.get("accepted_projection")).get("source_audit"))
    if source:
        return source
    return _mapping(_mapping(artifact.get("dismissed_projection")).get("source_audit"))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["append_audit_event_once"]
