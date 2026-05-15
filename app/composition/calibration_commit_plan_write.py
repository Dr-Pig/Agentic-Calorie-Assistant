from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.body.application.active_body_plan_read_model import build_active_body_plan_view
from app.body.infrastructure.models import BodyPlanRecord
from app.budget.application.effective_budget_math import summarize_budget_adjustment_layers
from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
from app.composition.canonical_body_support import load_active_body_plan_record
from app.composition.current_budget_read_model import build_current_budget_view
from app.shared.domain import CurrentBudgetView
from app.shared.infra.models import ProposalContainerRecord, User


def build_calibration_commit_current_budget_view(
    db: Session,
    *,
    user_id: int,
    local_date: str,
) -> CurrentBudgetView:
    existing_ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user_id,
            DayBudgetLedgerRecord.local_date == local_date,
        )
    ).scalar_one_or_none()
    view = build_current_budget_view(db, user_id=user_id, local_date=local_date)
    if existing_ledger is not None:
        return view

    active_plan = load_active_body_plan_record(db, user_id=user_id)
    if active_plan is None or int(active_plan.daily_budget_kcal or 0) <= 0:
        return view

    adjustment_entries = db.execute(
        select(LedgerEntryRecord).where(
            LedgerEntryRecord.user_id == user_id,
            LedgerEntryRecord.local_date == local_date,
            LedgerEntryRecord.entry_type != "meal_consumption",
        )
    ).scalars().all()
    budget_kcal = int(active_plan.daily_budget_kcal or 0)
    adjustment_kcal = summarize_budget_adjustment_layers(adjustment_entries).runtime_adjustment_total_kcal
    return view.model_copy(
        update={
            "budget_kcal": budget_kcal,
            "adjustment_kcal": adjustment_kcal,
            "remaining_kcal": budget_kcal - int(view.consumed_kcal or 0) - adjustment_kcal,
        }
    )


def create_new_body_plan_version(
    db: Session,
    *,
    user: User,
    previous_active_plan: BodyPlanRecord | None,
    effect_payload: dict[str, Any],
    accepted_at: datetime,
) -> BodyPlanRecord:
    if previous_active_plan is not None:
        previous_active_plan.plan_status = "superseded"
        previous_active_plan.ended_at = accepted_at

    previous_metadata = dict(previous_active_plan.metadata_json or {}) if previous_active_plan is not None else {}
    plan_source = str(effect_payload.get("plan_source") or "calibration_accept")
    new_daily_budget = int(
        effect_payload.get("new_daily_budget_kcal")
        or (previous_active_plan.daily_budget_kcal if previous_active_plan is not None else 0)
    )
    new_estimated_tdee = int(
        effect_payload.get("new_estimated_tdee_kcal")
        or (previous_active_plan.estimated_tdee if previous_active_plan is not None else 0)
    )
    new_pace = (
        float(effect_payload["new_target_pace_kg_per_week"])
        if effect_payload.get("new_target_pace_kg_per_week") is not None
        else (previous_active_plan.target_pace_kg_per_week if previous_active_plan is not None else None)
    )
    metadata = dict(previous_metadata)
    metadata.update(
        {
            "plan_source": plan_source,
            "recommended_target_kcal": new_daily_budget,
            "calibration_rationale": effect_payload.get("rationale_summary"),
        }
    )

    new_plan = BodyPlanRecord(
        user_id=user.id,
        plan_status="active",
        plan_label=str(effect_payload.get("proposal_family") or "calibration_plan"),
        estimated_tdee=new_estimated_tdee,
        daily_budget_kcal=new_daily_budget,
        safety_floor_kcal=(previous_active_plan.safety_floor_kcal if previous_active_plan is not None else 0),
        target_pace_kg_per_week=new_pace,
        metadata_json=metadata,
        started_at=accepted_at,
        created_at=accepted_at,
    )
    db.add(new_plan)
    db.flush()
    return new_plan


def create_calibration_adjustment_entry_if_requested(
    db: Session,
    *,
    user: User,
    proposal: ProposalContainerRecord,
    proposal_family: str,
    body_plan_id: int,
    effect_payload: dict[str, Any],
    effective_from: str,
) -> LedgerEntryRecord | None:
    calibration_adjustment_delta = effect_payload.get("calibration_adjustment_delta_kcal")
    if calibration_adjustment_delta is None:
        return None
    delta_kcal = int(calibration_adjustment_delta or 0)
    if delta_kcal == 0:
        return None
    entry = LedgerEntryRecord(
        user_id=user.id,
        local_date=effective_from,
        entry_type="calibration_adjustment",
        source_type="proposal_option",
        source_id=proposal.top_option_id,
        delta_kcal=delta_kcal,
        metadata_json={
            "proposal_container_id": proposal.id,
            "proposal_family": proposal_family,
            "body_plan_id": body_plan_id,
            "effective_from": effective_from,
        },
    )
    db.add(entry)
    db.flush()
    return entry


__all__ = [
    "build_active_body_plan_view",
    "build_calibration_commit_current_budget_view",
    "create_calibration_adjustment_entry_if_requested",
    "create_new_body_plan_version",
]
