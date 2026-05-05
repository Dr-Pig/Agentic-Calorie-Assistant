from __future__ import annotations

from typing import Any

READY_STATUS = "pl_ce_artifact_refresh_ready_for_human_review"


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_pl_ce_artifact_refresh_evidence(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("status") != READY_STATUS:
        blockers.append("pl_ce_artifact_refresh_status_not_ready")
    if payload.get("browser_execution_required") is not True:
        blockers.append("pl_ce_artifact_refresh_required_browser_missing")
    completed = _int_or_none(payload.get("completed_step_count"))
    required = _int_or_none(payload.get("required_step_count"))
    if completed is None:
        blockers.append("pl_ce_artifact_refresh_completed_step_count_invalid")
    if required is None:
        blockers.append("pl_ce_artifact_refresh_required_step_count_invalid")
    if completed is not None and required is not None and completed != required:
        blockers.append("pl_ce_artifact_refresh_incomplete")
    if payload.get("blockers"):
        blockers.append("pl_ce_artifact_refresh_blocked")
    return blockers


def is_pl_ce_artifact_refresh_ready(payload: dict[str, Any]) -> bool:
    return not validate_pl_ce_artifact_refresh_evidence(payload)


__all__ = [
    "READY_STATUS",
    "is_pl_ce_artifact_refresh_ready",
    "validate_pl_ce_artifact_refresh_evidence",
]
