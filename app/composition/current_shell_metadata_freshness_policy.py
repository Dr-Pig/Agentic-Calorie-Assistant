from __future__ import annotations

from datetime import datetime
from typing import Any

from app.composition import current_shell_compatibility_ids as cs_ids
from app.composition.current_shell_metadata_freshness_constants import (
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_STATUSES,
    OVERCLAIM_FLAGS,
    REQUIRED_PL_CE_METADATA_ARTIFACTS,
)
from app.composition.current_shell_metadata_freshness_group_blockers import (
    _current_gap_count,
    _group_specific_blockers as _group_specific_payload_blockers,
)
from app.composition.current_shell_metadata_freshness_rows import _age_hours
from app.composition.current_shell_metadata_freshness_rows import metadata_row


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "y", "claimed", "enabled"}
    return False


def _is_missing_payload(payload: dict[str, Any]) -> bool:
    if not payload:
        return True
    return (
        payload.get("status") == "missing"
        or payload.get("artifact_type") == "missing_pl_ce_metadata_freshness_input"
    )


def _is_invalid_read_payload(payload: dict[str, Any]) -> bool:
    return payload.get("artifact_type") == "invalid_pl_ce_metadata_freshness_input"


def _metadata_row(
    group_id: str,
    payload: dict[str, Any],
    *,
    now: datetime,
    max_age_hours: int,
) -> dict[str, Any]:
    return metadata_row(
        group_id,
        payload,
        now=now,
        max_age_hours=max_age_hours,
        present=not _is_missing_payload(payload),
    )


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _is_missing_payload(payload):
        return [f"{group_id}.missing"]
    if _is_invalid_read_payload(payload):
        return [f"{group_id}.invalid_artifact_file"]
    expected_type = EXPECTED_ARTIFACT_TYPES[group_id]
    legacy_types = (
        cs_ids.LEGACY_LOCAL_REVIEW_ARTIFACT_TYPES
        if group_id == "pl_ce_local_review_decision_pack"
        else cs_ids.LEGACY_LOCAL_MVP_ARTIFACT_TYPES
        if group_id == "pl_ce_local_mvp_candidate_bundle"
        else ()
    )
    if not cs_ids.matches_alias(payload.get("artifact_type"), expected_type, *legacy_types):
        blockers.append(f"{group_id}.unexpected_artifact_type")
    if not payload.get("artifact_schema_version"):
        blockers.append(f"{group_id}.missing_artifact_schema_version")
    if not payload.get("generated_at_utc"):
        blockers.append(f"{group_id}.missing_generated_at_utc")
    expected_status = EXPECTED_STATUSES[group_id]
    legacy_statuses = (
        cs_ids.LEGACY_LOCAL_REVIEW_READY_STATUSES
        if group_id == "pl_ce_local_review_decision_pack"
        else cs_ids.LEGACY_LOCAL_MVP_READY_STATUSES
        if group_id == "pl_ce_local_mvp_candidate_bundle"
        else ()
    )
    if not cs_ids.matches_alias(payload.get("status"), expected_status, *legacy_statuses):
        blockers.append(f"{group_id}.unexpected_status")
    return blockers


def _freshness_blockers(
    group_id: str,
    payload: dict[str, Any],
    *,
    now: datetime,
    max_age_hours: int,
) -> list[str]:
    if _is_missing_payload(payload) or _is_invalid_read_payload(payload):
        return []
    age = _age_hours(payload.get("generated_at_utc"), now=now)
    if age is None:
        return [f"{group_id}.invalid_generated_at_utc"]
    if age < 0:
        return [f"{group_id}.future_generated_at_utc"]
    if age > max_age_hours:
        return [f"{group_id}.stale_metadata"]
    return []


def _overclaim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{group_id}.{flag}"
        for flag in OVERCLAIM_FLAGS
        if _claim_is_true(payload.get(flag))
    ]


def _group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    if _is_missing_payload(payload) or _is_invalid_read_payload(payload):
        return []
    return _group_specific_payload_blockers(group_id, payload)
