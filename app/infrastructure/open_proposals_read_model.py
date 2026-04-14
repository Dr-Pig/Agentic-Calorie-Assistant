from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..domain import ProposalContainer, ProposalOption
from ..models import ProposalContainerRecord


def load_open_rescue_proposals_view(
    db: Session,
    *,
    user_id: int,
) -> list[ProposalContainer]:
    proposal_rows = (
        db.execute(
            select(ProposalContainerRecord)
            .options(selectinload(ProposalContainerRecord.options))
            .where(
                ProposalContainerRecord.user_id == user_id,
                ProposalContainerRecord.proposal_type == "rescue",
                ProposalContainerRecord.proposal_status == "open",
            )
            .order_by(ProposalContainerRecord.created_at.desc(), ProposalContainerRecord.id.desc())
        )
        .scalars()
        .all()
    )

    proposals: list[ProposalContainer] = []
    for record in proposal_rows:
        options = [
            ProposalOption(
                proposal_option_id=option.id,
                option_type=option.option_type,
                option_label=option.option_label,
                option_summary=option.option_summary,
                rank_order=option.rank_order,
                is_primary=option.is_primary,
                effect_payload=dict(option.effect_payload_json or {}),
            )
            for option in sorted(record.options, key=lambda item: (item.rank_order, item.id))
        ]
        proposals.append(
            ProposalContainer(
                proposal_container_id=record.id,
                user_id=record.user_id,
                proposal_type=record.proposal_type,
                proposal_status=record.proposal_status,
                top_option_id=record.top_option_id,
                metadata=dict(record.metadata_json or {}),
                accepted_at=record.accepted_at,
                created_at=record.created_at,
                options=options,
            )
        )
    return proposals
