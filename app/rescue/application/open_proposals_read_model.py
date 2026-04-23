from __future__ import annotations

from sqlalchemy.orm import Session

from ...shared.domain import ProposalContainer
from ..infrastructure.open_proposals_read_model import load_open_rescue_proposals_view


def build_open_rescue_proposals_view(
    db: Session,
    *,
    user_id: int,
) -> list[ProposalContainer]:
    return load_open_rescue_proposals_view(
        db,
        user_id=user_id,
    )
