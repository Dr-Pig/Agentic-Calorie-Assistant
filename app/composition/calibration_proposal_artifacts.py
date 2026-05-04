from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.body.application.body_calibration_service import BodyCalibrationDiagnosticResult
from app.composition.canonical_proposal_support import ensure_proposal_artifact_skeleton
from app.shared.domain import ProposalOption
from app.shared.infra.models import ProposalContainerRecord, User

ACTIVE_CALIBRATION_PROPOSAL_STATUSES = frozenset({"open", "presented", "negotiating"})


def assert_calibration_proposal_persistence_clean_session(db: Session) -> None:
    dirty_objects = [item for collection in (db.new, db.dirty, db.deleted) for item in collection]
    if dirty_objects:
        raise ValueError("calibration_proposal_persistence_requires_clean_session")


def _option_payload(option: ProposalOption, *, is_primary: bool) -> dict[str, Any]:
    return {
        "option_type": option.option_type,
        "option_label": option.option_label,
        "option_summary": option.option_summary,
        "rank_order": option.rank_order,
        "is_primary": is_primary,
        "effect_payload_json": dict(option.effect_payload or {}),
    }


def _artifact_payload(proposal: ProposalContainerRecord) -> dict[str, Any]:
    return {
        "proposal_container_id": proposal.id,
        "proposal_status": proposal.proposal_status,
        "proposal_type": proposal.proposal_type,
        "top_option_id": proposal.top_option_id,
    }


def persist_calibration_proposal_artifact(
    db: Session,
    *,
    user: User,
    local_date: str,
    diagnostic: BodyCalibrationDiagnosticResult,
) -> dict[str, Any] | None:
    assert_calibration_proposal_persistence_clean_session(db)

    response = diagnostic.response
    if not response.surfaced or response.top_option is None:
        return None

    options = [_option_payload(response.top_option, is_primary=True)]
    options.extend(_option_payload(option, is_primary=False) for option in response.backup_options)
    proposal = ensure_proposal_artifact_skeleton(
        db,
        user=user,
        proposal_type="calibration",
        metadata={
            "local_date": local_date,
            "proposal_family": response.proposal_family,
            "proposal_policy_packet": diagnostic.proposal_policy_packet,
            "trace_envelope": diagnostic.trace_envelope,
            "calibration_result": asdict(diagnostic.calibration_result),
            "gate_result": asdict(diagnostic.gate_result),
        },
        options=options,
    )
    return _artifact_payload(proposal)


def has_active_calibration_proposal(
    db: Session,
    *,
    user_id: int,
) -> bool:
    proposal_id = db.execute(
        select(ProposalContainerRecord.id).where(
            ProposalContainerRecord.user_id == user_id,
            ProposalContainerRecord.proposal_type == "calibration",
            ProposalContainerRecord.proposal_status.in_(ACTIVE_CALIBRATION_PROPOSAL_STATUSES),
        )
    ).scalar_one_or_none()
    return proposal_id is not None


__all__ = [
    "ACTIVE_CALIBRATION_PROPOSAL_STATUSES",
    "assert_calibration_proposal_persistence_clean_session",
    "has_active_calibration_proposal",
    "persist_calibration_proposal_artifact",
]
