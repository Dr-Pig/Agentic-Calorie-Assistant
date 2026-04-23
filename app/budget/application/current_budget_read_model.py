from __future__ import annotations

from sqlalchemy.orm import Session

from ...shared.domain import CurrentBudgetView
from ..infrastructure.current_budget_read_model import load_current_budget_view


def build_current_budget_view(
    db: Session,
    *,
    user_id: int,
    local_date: str,
) -> CurrentBudgetView:
    return load_current_budget_view(
        db,
        user_id=user_id,
        local_date=local_date,
    )
