from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.composition.calibration_proposal_artifacts import ACTIVE_CALIBRATION_PROPOSAL_STATUSES
from app.shared.domain import ProposalContainer, ProposalOption
from app.shared.infra.models import ProposalContainerRecord, ProposalOptionRecord


def _to_domain_option(option: ProposalOptionRecord) -> ProposalOption:
    return ProposalOption(
        proposal_option_id=option.id,
        option_type=option.option_type,
        option_label=option.option_label,
        option_summary=option.option_summary,
        rank_order=option.rank_order,
        is_primary=option.is_primary,
        effect_payload=dict(option.effect_payload_json or {}),
    )


def _load_options(db: Session, *, proposal_container_id: int) -> list[ProposalOption]:
    options = db.execute(
        select(ProposalOptionRecord)
        .where(ProposalOptionRecord.proposal_container_id == proposal_container_id)
        .order_by(ProposalOptionRecord.rank_order.asc(), ProposalOptionRecord.id.asc())
    ).scalars().all()
    return [_to_domain_option(option) for option in options]


def _to_domain_container(db: Session, proposal: ProposalContainerRecord) -> ProposalContainer:
    return ProposalContainer(
        proposal_container_id=proposal.id,
        user_id=proposal.user_id,
        proposal_type=proposal.proposal_type,
        proposal_status=proposal.proposal_status,
        top_option_id=proposal.top_option_id,
        metadata=dict(proposal.metadata_json or {}),
        accepted_at=proposal.accepted_at,
        created_at=proposal.created_at,
        options=_load_options(db, proposal_container_id=proposal.id),
    )


def load_open_calibration_proposal_inbox(
    db: Session,
    *,
    user_id: int,
    limit: int = 20,
) -> list[ProposalContainer]:
    bounded_limit = max(1, min(int(limit), 50))
    proposals = db.execute(
        select(ProposalContainerRecord)
        .where(
            ProposalContainerRecord.user_id == user_id,
            ProposalContainerRecord.proposal_type == "calibration",
            ProposalContainerRecord.proposal_status.in_(ACTIVE_CALIBRATION_PROPOSAL_STATUSES),
        )
        .order_by(ProposalContainerRecord.created_at.desc(), ProposalContainerRecord.id.desc())
        .limit(bounded_limit)
    ).scalars().all()
    return [_to_domain_container(db, proposal) for proposal in proposals]


__all__ = ["load_open_calibration_proposal_inbox"]
