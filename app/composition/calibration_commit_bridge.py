from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.body.application.active_body_plan_read_model import build_active_body_plan_view
from app.composition.calibration_commit_effect_policy import (
    PLAN_CHANGING_CALIBRATION_FAMILIES,
    validate_plan_changing_effect_payload,
)
from app.composition.calibration_commit_plan_write import (
    build_calibration_commit_current_budget_view,
    create_calibration_adjustment_entry_if_requested,
    create_new_body_plan_version,
)
from app.composition.calibration_proposal_artifacts import ACTIVE_CALIBRATION_PROPOSAL_STATUSES
from app.composition.canonical_body_support import (
    load_active_body_plan_record,
    recompute_day_budget_ledger,
)
from app.composition.canonical_proposal_support import ensure_proposal_artifact_skeleton
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView
from app.shared.infra.models import ProposalContainerRecord, User

CalibrationCommitDecision = Literal["accepted", "rejected", "dismissed"]


class StoredCalibrationProposalNotActionable(ValueError):
    def __init__(self, status: str) -> None:
        self.status = status or "missing"
        super().__init__(f"stored calibration proposal is not actionable: {self.status}")


@dataclass(frozen=True)
class CalibrationCommitResult:
    proposal_container_id: int
    proposal_status: CalibrationCommitDecision
    body_plan_id: int | None
    effective_from: str
    current_budget_view: CurrentBudgetView
    active_body_plan_view: ActiveBodyPlanView


def _resolve_effective_from(
    *,
    local_date: str,
    accepted_at: datetime,
    immediate: bool,
) -> str:
    if immediate or accepted_at.hour < 11:
        return local_date
    return (datetime.fromisoformat(local_date) + timedelta(days=1)).date().isoformat()


def _load_calibration_proposal_or_raise(
    db: Session,
    *,
    user: User,
    proposal_container_id: int,
) -> ProposalContainerRecord:
    proposal = db.get(ProposalContainerRecord, proposal_container_id)
    if proposal is None or proposal.user_id != user.id or proposal.proposal_type != "calibration":
        raise ValueError("calibration proposal not found")
    return proposal


def _ensure_stored_proposal_actionable(proposal: ProposalContainerRecord) -> None:
    status = str(proposal.proposal_status or "").strip()
    if status not in ACTIVE_CALIBRATION_PROPOSAL_STATUSES:
        raise StoredCalibrationProposalNotActionable(status)


def _transition_active_stored_proposal_or_raise(
    db: Session,
    *,
    user: User,
    proposal: ProposalContainerRecord,
    decision: CalibrationCommitDecision,
    metadata: dict[str, Any],
    accepted_at: datetime | None,
) -> ProposalContainerRecord:
    result = db.execute(
        update(ProposalContainerRecord)
        .where(
            ProposalContainerRecord.id == proposal.id,
            ProposalContainerRecord.user_id == user.id,
            ProposalContainerRecord.proposal_type == "calibration",
            ProposalContainerRecord.proposal_status.in_(ACTIVE_CALIBRATION_PROPOSAL_STATUSES),
        )
        .values(
            proposal_status=decision,
            accepted_at=accepted_at if decision == "accepted" else proposal.accepted_at,
            metadata_json=metadata,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        current_status = db.execute(
            select(ProposalContainerRecord.proposal_status).where(ProposalContainerRecord.id == proposal.id)
        ).scalar_one_or_none()
        raise StoredCalibrationProposalNotActionable(str(current_status or "missing"))
    db.flush()
    db.refresh(proposal)
    return proposal


def _stored_top_option_payload(proposal: ProposalContainerRecord) -> tuple[str, dict[str, Any]]:
    top_option = next((option for option in proposal.options if option.id == proposal.top_option_id), None)
    if top_option is None:
        top_option = next((option for option in proposal.options if option.is_primary), None)
    if top_option is None and proposal.options:
        top_option = sorted(proposal.options, key=lambda option: option.rank_order)[0]
    if top_option is None:
        raise ValueError("calibration proposal has no option to apply")
    return top_option.option_type, dict(top_option.effect_payload_json or {})


def apply_calibration_proposal_commit(
    db: Session,
    *,
    user: User,
    local_date: str,
    proposal_family: str,
    effect_payload: dict[str, Any],
    decision: CalibrationCommitDecision,
    accepted_at: datetime | None = None,
    proposal_container_id: int | None = None,
    require_active_stored_proposal: bool = False,
) -> CalibrationCommitResult:
    resolved_now = accepted_at or datetime.now()
    plan_change_accepted = decision == "accepted" and proposal_family in PLAN_CHANGING_CALIBRATION_FAMILIES
    immediate = not plan_change_accepted
    effective_from = _resolve_effective_from(
        local_date=local_date,
        accepted_at=resolved_now,
        immediate=immediate,
    )
    active_plan = load_active_body_plan_record(db, user_id=user.id) if plan_change_accepted else None
    if decision == "accepted":
        effect_payload = validate_plan_changing_effect_payload(
            proposal_family=proposal_family,
            effect_payload=effect_payload,
            active_plan=active_plan,
        )
    if proposal_container_id is None:
        proposal = ensure_proposal_artifact_skeleton(
            db,
            user=user,
            proposal_type="calibration",
            metadata={
                "proposal_family": proposal_family,
                "effective_from": effective_from,
                "decision": decision,
            },
            options=[
                {
                    "option_type": proposal_family,
                    "option_label": proposal_family,
                    "option_summary": str(effect_payload.get("rationale_summary") or proposal_family),
                    "is_primary": True,
                    "rank_order": 0,
                    "effect_payload_json": dict(effect_payload),
                }
            ],
        )
        proposal.proposal_status = decision
        if decision == "accepted":
            proposal.accepted_at = resolved_now
    else:
        proposal = _load_calibration_proposal_or_raise(
            db,
            user=user,
            proposal_container_id=proposal_container_id,
        )
        metadata = {
            **dict(proposal.metadata_json or {}),
            "proposal_family": proposal_family,
            "effective_from": effective_from,
            "decision": decision,
        }
        if require_active_stored_proposal:
            proposal = _transition_active_stored_proposal_or_raise(
                db,
                user=user,
                proposal=proposal,
                decision=decision,
                metadata=metadata,
                accepted_at=resolved_now,
            )
        else:
            proposal.metadata_json = metadata
            proposal.proposal_status = decision
            if decision == "accepted":
                proposal.accepted_at = resolved_now

    body_plan_id: int | None = None
    if plan_change_accepted:
        new_plan = create_new_body_plan_version(
            db,
            user=user,
            previous_active_plan=active_plan,
            effect_payload={**effect_payload, "proposal_family": proposal_family},
            accepted_at=resolved_now,
        )
        body_plan_id = new_plan.id
        create_calibration_adjustment_entry_if_requested(
            db,
            user=user,
            proposal=proposal,
            proposal_family=proposal_family,
            body_plan_id=new_plan.id,
            effect_payload=effect_payload,
            effective_from=effective_from,
        )
        recompute_day_budget_ledger(
            db,
            user_id=user.id,
            local_date=effective_from,
            budget_kcal=new_plan.daily_budget_kcal,
        )

    db.commit()
    db.refresh(proposal)
    return CalibrationCommitResult(
        proposal_container_id=proposal.id,
        proposal_status=proposal.proposal_status,  # type: ignore[arg-type]
        body_plan_id=body_plan_id,
        effective_from=effective_from,
        current_budget_view=build_calibration_commit_current_budget_view(
            db,
            user_id=user.id,
            local_date=effective_from,
        ),
        active_body_plan_view=build_active_body_plan_view(db, user_id=user.id),
    )


def apply_stored_calibration_proposal_action(
    db: Session,
    *,
    user: User,
    proposal_container_id: int,
    decision: CalibrationCommitDecision,
    accepted_at: datetime | None = None,
) -> CalibrationCommitResult:
    proposal = _load_calibration_proposal_or_raise(
        db,
        user=user,
        proposal_container_id=proposal_container_id,
    )
    _ensure_stored_proposal_actionable(proposal)
    local_date = str((proposal.metadata_json or {}).get("local_date") or "").strip()
    if not local_date:
        raise ValueError("stored calibration proposal is missing local_date")
    proposal_family, effect_payload = _stored_top_option_payload(proposal)
    return apply_calibration_proposal_commit(
        db,
        user=user,
        local_date=local_date,
        proposal_family=proposal_family,
        effect_payload=effect_payload,
        decision=decision,
        accepted_at=accepted_at,
        proposal_container_id=proposal.id,
        require_active_stored_proposal=True,
    )
