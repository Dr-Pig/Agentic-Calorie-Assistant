from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ...models import LedgerEntryRecord, User
from app.composition.canonical_persistence import (
    ensure_body_plan_skeleton,
    ensure_proactive_trigger_skeleton,
    ensure_proposal_artifact_skeleton,
    ensure_proposal_skeleton,
    recompute_day_budget_ledger,
)


def apply_rescue_overlay_skeleton(
    db: Session,
    *,
    user: User,
    local_date: str,
    delta_kcal: int,
    source_id: int | None = None,
    source_type: str = "rescue_plan",
    budget_kcal: int | None = None,
    metadata: dict[str, object] | None = None,
) -> LedgerEntryRecord:
    entry = LedgerEntryRecord(
        user_id=user.id,
        local_date=local_date,
        entry_type="rescue_overlay",
        source_type=source_type,
        source_id=source_id,
        delta_kcal=delta_kcal,
        metadata_json=dict(metadata or {}),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    recompute_day_budget_ledger(db, user_id=user.id, local_date=local_date, budget_kcal=budget_kcal)
    return entry


def apply_proposal_acceptance_skeleton(
    db: Session,
    *,
    user: User,
    proposal_type: str,
    option_type: str,
    option_label: str,
    estimated_tdee: int = 0,
    daily_budget_kcal: int = 0,
    safety_floor_kcal: int = 0,
) -> dict[str, int | None]:
    proposal = ensure_proposal_skeleton(
        db,
        user=user,
        proposal_type=proposal_type,
        option_type=option_type,
        option_label=option_label,
    )
    proposal.proposal_status = "accepted"
    proposal.accepted_at = datetime.now()
    body_plan = ensure_body_plan_skeleton(
        db,
        user=user,
        estimated_tdee=estimated_tdee,
        daily_budget_kcal=daily_budget_kcal,
        safety_floor_kcal=safety_floor_kcal,
    )
    body_plan.estimated_tdee = estimated_tdee or body_plan.estimated_tdee
    body_plan.daily_budget_kcal = daily_budget_kcal or body_plan.daily_budget_kcal
    body_plan.safety_floor_kcal = safety_floor_kcal or body_plan.safety_floor_kcal
    db.commit()
    db.refresh(proposal)
    db.refresh(body_plan)
    return {
        "proposal_container_id": proposal.id,
        "body_plan_id": body_plan.id,
        "top_option_id": proposal.top_option_id,
    }


def persist_proposal_artifact_skeleton(
    db: Session,
    *,
    user: User,
    proposal_type: str,
    options: list[dict[str, object]],
    metadata: dict[str, object] | None = None,
) -> dict[str, int | None]:
    proposal = ensure_proposal_artifact_skeleton(
        db,
        user=user,
        proposal_type=proposal_type,
        options=options,
        metadata=metadata,
    )
    return {
        "proposal_container_id": proposal.id,
        "top_option_id": proposal.top_option_id,
        "option_count": len(proposal.options),
    }


def apply_proposal_decision_skeleton(
    db: Session,
    *,
    proposal_container_id: int,
    decision: str,
    metadata_patch: dict[str, object] | None = None,
) -> dict[str, object]:
    from ...models import ProposalContainerRecord

    proposal = db.get(ProposalContainerRecord, proposal_container_id)
    if proposal is None:
        raise ValueError(f"proposal_container_id={proposal_container_id} not found")

    if decision not in {"accepted", "rejected", "deferred_pending_reminder", "closed_expired"}:
        raise ValueError(f"unsupported proposal decision: {decision}")

    proposal.proposal_status = decision
    if decision == "accepted":
        proposal.accepted_at = datetime.now()

    merged_metadata = dict(proposal.metadata_json or {})
    merged_metadata.update(metadata_patch or {})
    proposal.metadata_json = merged_metadata
    db.commit()
    db.refresh(proposal)
    return {
        "proposal_container_id": proposal.id,
        "proposal_status": proposal.proposal_status,
        "top_option_id": proposal.top_option_id,
        "metadata": dict(proposal.metadata_json or {}),
    }


def record_proactive_trigger_skeleton(
    db: Session,
    *,
    user: User,
    trigger_type: str,
) -> int:
    trigger = ensure_proactive_trigger_skeleton(db, user=user, trigger_type=trigger_type)
    return trigger.id
