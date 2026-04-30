from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.composition.canonical_persistence import (
    ensure_proposal_artifact_skeleton,
    load_active_body_plan_record,
    recompute_day_budget_ledger,
)
from app.body.application.active_body_plan_read_model import build_active_body_plan_view
from app.body.infrastructure.models import BodyPlanRecord
from app.composition.current_budget_read_model import build_current_budget_view
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView
from app.shared.infra.models import User

CalibrationCommitDecision = Literal["accepted", "rejected", "deferred_pending_reminder"]


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


def _create_new_body_plan_version(
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
        safety_floor_kcal=(
            previous_active_plan.safety_floor_kcal if previous_active_plan is not None else 0
        ),
        target_pace_kg_per_week=new_pace,
        metadata_json=metadata,
        started_at=accepted_at,
        created_at=accepted_at,
    )
    db.add(new_plan)
    db.flush()
    return new_plan


def apply_calibration_proposal_commit(
    db: Session,
    *,
    user: User,
    local_date: str,
    proposal_family: str,
    effect_payload: dict[str, Any],
    decision: CalibrationCommitDecision,
    accepted_at: datetime | None = None,
) -> CalibrationCommitResult:
    resolved_now = accepted_at or datetime.now()
    immediate = proposal_family in {"logging_quality_first", "monitor_only"}
    effective_from = _resolve_effective_from(
        local_date=local_date,
        accepted_at=resolved_now,
        immediate=immediate,
    )
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

    body_plan_id: int | None = None
    if decision == "accepted" and proposal_family not in {"logging_quality_first", "monitor_only"}:
        active_plan = load_active_body_plan_record(db, user_id=user.id)
        new_plan = _create_new_body_plan_version(
            db,
            user=user,
            previous_active_plan=active_plan,
            effect_payload={**effect_payload, "proposal_family": proposal_family},
            accepted_at=resolved_now,
        )
        body_plan_id = new_plan.id
        recompute_day_budget_ledger(
            db,
            user_id=user.id,
            local_date=effective_from,
            budget_kcal=new_plan.daily_budget_kcal,
        )
    else:
        recompute_day_budget_ledger(
            db,
            user_id=user.id,
            local_date=effective_from,
        )

    db.commit()
    db.refresh(proposal)
    return CalibrationCommitResult(
        proposal_container_id=proposal.id,
        proposal_status=proposal.proposal_status,  # type: ignore[arg-type]
        body_plan_id=body_plan_id,
        effective_from=effective_from,
        current_budget_view=build_current_budget_view(db, user_id=user.id, local_date=effective_from),
        active_body_plan_view=build_active_body_plan_view(db, user_id=user.id),
    )
