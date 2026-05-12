from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import (
    NON_MUTATION_FLAGS,
    validate_memory_record_contract,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.memory_promotion_validator"
)

PATTERN_MIN_REINFORCEMENT_COUNT = 5


def validate_memory_record_promotion_decision(
    *,
    memory_record: Mapping[str, Any],
    as_of: str,
    feedback_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validate_memory_record_contract(memory_record)
    normalized = validation.get("normalized_record") or {}
    status_before = str(memory_record.get("status") or normalized.get("status") or "pending_review")
    blockers = [
        *validation["blockers"],
        *_claim_blockers(memory_record),
    ]
    if blockers:
        return _decision(
            memory_record,
            decision="blocked",
            reason_codes=[],
            blockers=blockers,
            status_after=status_before,
        )

    record_type = str(normalized.get("record_type") or "")
    if record_type == "pattern_memory":
        return _pattern_decision(normalized, memory_record, feedback_projection)
    if record_type == "temporary_preference":
        return _temporary_decision(normalized, as_of)
    if record_type == "negative_preference":
        return _negative_decision(normalized, memory_record)
    return _decision(
        normalized,
        decision="human_confirmation_required",
        reason_codes=["unsupported_auto_promotion_path"],
        blockers=[],
        status_after=str(normalized.get("status") or "pending_review"),
    )


def _pattern_decision(
    normalized: Mapping[str, Any],
    original: Mapping[str, Any],
    feedback_projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    count = int(original.get("reinforcement_count") or 0)
    if count < PATTERN_MIN_REINFORCEMENT_COUNT:
        return _decision(
            normalized,
            decision="hold_for_more_evidence",
            reason_codes=["pattern_threshold_not_met"],
            blockers=[],
            status_after=str(normalized.get("status") or "pending_review"),
        )
    if not _confirm_projection_matches(normalized, feedback_projection):
        reasons = ["human_confirmation_missing"]
        if feedback_projection and str(feedback_projection.get("target_id") or "") != str(normalized["id"]):
            reasons.append("feedback_target_mismatch")
        return _decision(
            normalized,
            decision="human_confirmation_required",
            reason_codes=reasons,
            blockers=[],
            status_after=str(normalized.get("status") or "pending_review"),
        )
    return _decision(
        normalized,
        decision="confirmable_after_validator",
        reason_codes=["pattern_threshold_met", "feedback_confirmation_valid"],
        blockers=[],
        status_after="confirmed",
    )


def _temporary_decision(normalized: Mapping[str, Any], as_of: str) -> dict[str, Any]:
    validity = normalized.get("validity")
    valid_until = validity.get("valid_until") if isinstance(validity, Mapping) else None
    expired = _is_expired(valid_until, as_of)
    return _decision(
        normalized,
        decision="archive_review_candidate" if expired else "hold_until_expiry_or_confirmation",
        reason_codes=["temporary_preference_expired"] if expired else ["temporary_preference_active"],
        blockers=[],
        status_after="archived" if expired else str(normalized.get("status") or "pending_review"),
    )


def _negative_decision(
    normalized: Mapping[str, Any], original: Mapping[str, Any]
) -> dict[str, Any]:
    conflicts = original.get("conflicts_with")
    if isinstance(conflicts, list) and conflicts:
        return _decision(
            normalized,
            decision="contradiction_review_candidate",
            reason_codes=["confirmed_negative_requires_review"],
            blockers=[],
            status_after=str(normalized.get("status") or "confirmed"),
            auto_demote_allowed=False,
        )
    return _decision(
        normalized,
        decision="keep_confirmed_negative",
        reason_codes=["negative_preference_retained"],
        blockers=[],
        status_after=str(normalized.get("status") or "confirmed"),
        auto_demote_allowed=False,
    )


def _claim_blockers(record: Mapping[str, Any]) -> list[str]:
    if record.get("llm_recommended_promotion") is True or record.get("promotion_allowed_now") is True:
        return ["llm_auto_promotion_claim_blocked"]
    return []


def _confirm_projection_matches(
    record: Mapping[str, Any], projection: Mapping[str, Any] | None
) -> bool:
    if not projection:
        return False
    return (
        projection.get("projection_type") == "memory_confirmation_validator_input"
        and projection.get("may_satisfy_memory_confirmation_gate") is True
        and str(projection.get("target_id") or "") == str(record.get("id") or "")
    )


def _is_expired(valid_until: Any, as_of: str) -> bool:
    if not isinstance(valid_until, str) or not valid_until:
        return False
    return _parse_date_or_datetime(valid_until) < _parse_date_or_datetime(as_of)


def _parse_date_or_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed_date = date.fromisoformat(value)
        return datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _decision(
    record: Mapping[str, Any],
    *,
    decision: str,
    reason_codes: list[str],
    blockers: list[str],
    status_after: str,
    auto_demote_allowed: bool = False,
) -> dict[str, Any]:
    return {
        "artifact_type": "memory_record_promotion_decision",
        "record_id": str(record.get("id") or memory_record_id(record)),
        "record_type": str(record.get("record_type") or ""),
        "decision": decision,
        "reason_codes": reason_codes,
        "blockers": blockers,
        "status_before": str(record.get("status") or "pending_review"),
        "status_after": status_after,
        "thresholds": {"pattern_min_reinforcement_count": PATTERN_MIN_REINFORCEMENT_COUNT},
        "auto_demote_allowed": auto_demote_allowed,
        "confirmed_memory_promoted": False,
        **NON_MUTATION_FLAGS,
    }


def memory_record_id(record: Mapping[str, Any]) -> str:
    return str(record.get("id") or "memory_record")


__all__ = [
    "PATTERN_MIN_REINFORCEMENT_COUNT",
    "SIDECAR_ACTIVATION_CONTRACT",
    "validate_memory_record_promotion_decision",
]
