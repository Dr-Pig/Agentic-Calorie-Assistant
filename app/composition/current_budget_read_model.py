from __future__ import annotations

from sqlalchemy.orm import Session

from app.composition.current_budget_loader import load_current_budget_view
from app.shared.domain import CurrentBudgetView


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
