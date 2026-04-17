from __future__ import annotations

from sqlalchemy.orm import Session

from ..domain import ActiveBodyPlanView
from ..infrastructure.active_body_plan_read_model import load_active_body_plan_view


def build_active_body_plan_view(
    db: Session,
    *,
    user_id: int,
) -> ActiveBodyPlanView:
    return load_active_body_plan_view(
        db,
        user_id=user_id,
    )
