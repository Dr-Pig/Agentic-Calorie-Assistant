from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.composition.manual_daily_target_service import (
    ManualDailyTargetInput,
    ManualDailyTargetResult,
    set_manual_daily_target,
)
from app.shared.infra.models import User


def _target_from_mapping(mapping: dict[str, Any]) -> int | None:
    for key in ("daily_target_kcal", "target_kcal", "manual_daily_target_kcal"):
        value = mapping.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return None


def manual_daily_target_from_manager_decision(manager_decision: Any) -> int | None:
    """Read an explicit target from Manager structured output, never raw text."""

    answer_contract = dict(getattr(manager_decision, "answer_contract", {}) or {})
    semantic_decision = dict(getattr(manager_decision, "semantic_decision", {}) or {})
    target_attachment = dict(getattr(manager_decision, "target_attachment", {}) or {})
    for mapping in (answer_contract, semantic_decision, target_attachment):
        target = _target_from_mapping(mapping)
        if target is not None:
            return target
    return None


def apply_manual_daily_target_from_chat(
    db: Session,
    *,
    user: User,
    manager_decision: Any,
    local_date: str,
) -> ManualDailyTargetResult:
    daily_target_kcal = manual_daily_target_from_manager_decision(manager_decision)
    if daily_target_kcal is None:
        raise ValueError("manual_daily_target_kcal_required")
    return set_manual_daily_target(
        db,
        user=user,
        inputs=ManualDailyTargetInput(
            daily_target_kcal=daily_target_kcal,
            local_date=local_date,
            source="user_chat",
        ),
    )


def manual_daily_target_trace_payload(result: ManualDailyTargetResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "user_id": result.user_id,
        "local_date": result.local_date,
        "previous_daily_target_kcal": result.previous_daily_target_kcal,
        "target_delta_kcal": result.target_delta_kcal,
        "active_body_plan": result.active_body_plan_view.model_dump(mode="json"),
        "current_budget": result.current_budget_view.model_dump(mode="json"),
        "live_llm_invoked": result.live_llm_invoked,
        "product_readiness_claimed": result.product_readiness_claimed,
        "private_self_use_approved": result.private_self_use_approved,
        "production_selected": result.production_selected,
    }
