from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.body.application.active_body_plan_read_model import build_active_body_plan_view
from app.body.infrastructure.models import BodyPlanRecord
from app.budget.application.effective_budget_math import (
    summarize_budget_adjustment_layers,
)
from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
from app.composition.calibration_proposal_artifacts import (
    ACTIVE_CALIBRATION_PROPOSAL_STATUSES,
)
from app.composition.canonical_body_support import (
    load_active_body_plan_record,
    recompute_day_budget_ledger,
)
from app.composition.canonical_proposal_support import ensure_proposal_artifact_skeleton
from app.composition.current_budget_read_model import build_current_budget_view
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView
from app.shared.infra.models import ProposalContainerRecord, User

CalibrationCommitDecision = Literal["accepted", "rejected", "dismissed"]
PLAN_CHANGING_CALIBRATION_FAMILIES = frozenset(
    {
        "budget_adjustment",
        "pace_adjustment",
        "plan_reset",
    }
)
MIN_DAILY_BUDGET_KCAL = 800
MAX_DAILY_BUDGET_KCAL = 5000
MIN_ESTIMATED_TDEE_KCAL = 800
MAX_ESTIMATED_TDEE_KCAL = 6000
MAX_TARGET_PACE_KG_PER_WEEK = 2.0


class StoredCalibrationProposalNotActionable(ValueError):
    def __init__(self, status: str) -> None:
        self.status = status or "missing"
        super().__init__(f"stored calibration proposal is not actionable: {self.status}")


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


def _coerce_required_int(payload: dict[str, Any], field_name: str) -> int:
    if field_name not in payload or payload.get(field_name) is None:
        raise ValueError(f"{field_name} is required for accepted plan-changing calibration proposal")
    value = payload[field_name]
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"{field_name} must be an integer")
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _coerce_optional_int(payload: dict[str, Any], field_name: str) -> int | None:
    if field_name not in payload or payload.get(field_name) is None:
        return None
    value = payload[field_name]
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"{field_name} must be an integer")
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _coerce_optional_float(payload: dict[str, Any], field_name: str) -> float | None:
    if field_name not in payload or payload.get(field_name) is None:
        return None
    value = payload[field_name]
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc


def _validate_plan_changing_effect_payload(
    *,
    proposal_family: str,
    effect_payload: dict[str, Any],
    active_plan: BodyPlanRecord | None,
) -> dict[str, Any]:
    if proposal_family not in PLAN_CHANGING_CALIBRATION_FAMILIES:
        if effect_payload.get("plan_change_required") is True:
            raise ValueError(f"unknown plan-changing calibration proposal_family {proposal_family!r}")
        return effect_payload

    new_daily_budget = _coerce_required_int(effect_payload, "new_daily_budget_kcal")
    safety_floor = int(active_plan.safety_floor_kcal or 0) if active_plan is not None else 0
    if new_daily_budget < safety_floor:
        raise ValueError("new_daily_budget_kcal must not be below active plan safety_floor_kcal")
    if not MIN_DAILY_BUDGET_KCAL <= new_daily_budget <= MAX_DAILY_BUDGET_KCAL:
        raise ValueError(
            f"new_daily_budget_kcal must be between {MIN_DAILY_BUDGET_KCAL} and {MAX_DAILY_BUDGET_KCAL}"
        )

    if "new_estimated_tdee_kcal" in effect_payload and effect_payload.get("new_estimated_tdee_kcal") is not None:
        new_estimated_tdee = _coerce_required_int(effect_payload, "new_estimated_tdee_kcal")
    else:
        if active_plan is None:
            raise ValueError("new_estimated_tdee_kcal is required when no active plan TDEE can be inherited")
        new_estimated_tdee = int(active_plan.estimated_tdee or 0)
    if not MIN_ESTIMATED_TDEE_KCAL <= new_estimated_tdee <= MAX_ESTIMATED_TDEE_KCAL:
        raise ValueError(
            f"new_estimated_tdee_kcal must be between {MIN_ESTIMATED_TDEE_KCAL} and {MAX_ESTIMATED_TDEE_KCAL}"
        )

    normalized = dict(effect_payload)
    normalized["new_daily_budget_kcal"] = new_daily_budget
    normalized["new_estimated_tdee_kcal"] = new_estimated_tdee
    calibration_adjustment_delta = _coerce_optional_int(normalized, "calibration_adjustment_delta_kcal")
    if calibration_adjustment_delta is not None:
        candidate_effective_budget = new_daily_budget + calibration_adjustment_delta
        if candidate_effective_budget < safety_floor:
            raise ValueError(
                "calibration_adjustment_delta_kcal must not push effective budget below active plan safety_floor_kcal"
            )
        normalized["calibration_adjustment_delta_kcal"] = calibration_adjustment_delta
    if proposal_family in {"pace_adjustment", "plan_reset"}:
        new_pace = _coerce_optional_float(normalized, "new_target_pace_kg_per_week")
        if new_pace is not None:
            if new_pace <= 0 or new_pace > MAX_TARGET_PACE_KG_PER_WEEK:
                raise ValueError(
                    f"new_target_pace_kg_per_week must be positive and <= {MAX_TARGET_PACE_KG_PER_WEEK}"
                )
            normalized["new_target_pace_kg_per_week"] = new_pace
    return normalized


def _build_calibration_commit_current_budget_view(
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


def _create_calibration_adjustment_entry_if_requested(
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


def _load_calibration_proposal_or_raise(
    db: Session,
    *,
    user: User,
    proposal_container_id: int,
) -> ProposalContainerRecord:
    proposal = db.get(ProposalContainerRecord, proposal_container_id)
    if proposal is None or proposal.user_id != user.id or proposal.proposal_type != "calibration":
        raise ValueError("calibration proposal not found")
    return proposal


def _ensure_stored_proposal_actionable(proposal: ProposalContainerRecord) -> None:
    status = str(proposal.proposal_status or "").strip()
    if status not in ACTIVE_CALIBRATION_PROPOSAL_STATUSES:
        raise StoredCalibrationProposalNotActionable(status)


def _transition_active_stored_proposal_or_raise(
    db: Session,
    *,
    user: User,
    proposal: ProposalContainerRecord,
    decision: CalibrationCommitDecision,
    metadata: dict[str, Any],
    accepted_at: datetime | None,
) -> ProposalContainerRecord:
    result = db.execute(
        update(ProposalContainerRecord)
        .where(
            ProposalContainerRecord.id == proposal.id,
            ProposalContainerRecord.user_id == user.id,
            ProposalContainerRecord.proposal_type == "calibration",
            ProposalContainerRecord.proposal_status.in_(ACTIVE_CALIBRATION_PROPOSAL_STATUSES),
        )
        .values(
            proposal_status=decision,
            accepted_at=accepted_at if decision == "accepted" else proposal.accepted_at,
            metadata_json=metadata,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        current_status = db.execute(
            select(ProposalContainerRecord.proposal_status).where(ProposalContainerRecord.id == proposal.id)
        ).scalar_one_or_none()
        raise StoredCalibrationProposalNotActionable(str(current_status or "missing"))
    db.flush()
    db.refresh(proposal)
    return proposal


def _stored_top_option_payload(proposal: ProposalContainerRecord) -> tuple[str, dict[str, Any]]:
    top_option = next((option for option in proposal.options if option.id == proposal.top_option_id), None)
    if top_option is None:
        top_option = next((option for option in proposal.options if option.is_primary), None)
    if top_option is None and proposal.options:
        top_option = sorted(proposal.options, key=lambda option: option.rank_order)[0]
    if top_option is None:
        raise ValueError("calibration proposal has no option to apply")
    return top_option.option_type, dict(top_option.effect_payload_json or {})


def apply_calibration_proposal_commit(
    db: Session,
    *,
    user: User,
    local_date: str,
    proposal_family: str,
    effect_payload: dict[str, Any],
    decision: CalibrationCommitDecision,
    accepted_at: datetime | None = None,
    proposal_container_id: int | None = None,
    require_active_stored_proposal: bool = False,
) -> CalibrationCommitResult:
    resolved_now = accepted_at or datetime.now()
    plan_change_accepted = decision == "accepted" and proposal_family in PLAN_CHANGING_CALIBRATION_FAMILIES
    immediate = not plan_change_accepted
    effective_from = _resolve_effective_from(
        local_date=local_date,
        accepted_at=resolved_now,
        immediate=immediate,
    )
    active_plan = load_active_body_plan_record(db, user_id=user.id) if plan_change_accepted else None
    if decision == "accepted":
        effect_payload = _validate_plan_changing_effect_payload(
            proposal_family=proposal_family,
            effect_payload=effect_payload,
            active_plan=active_plan,
        )
    if proposal_container_id is None:
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
    else:
        proposal = _load_calibration_proposal_or_raise(
            db,
            user=user,
            proposal_container_id=proposal_container_id,
        )
        metadata = {
            **dict(proposal.metadata_json or {}),
            "proposal_family": proposal_family,
            "effective_from": effective_from,
            "decision": decision,
        }
        if require_active_stored_proposal:
            proposal = _transition_active_stored_proposal_or_raise(
                db,
                user=user,
                proposal=proposal,
                decision=decision,
                metadata=metadata,
                accepted_at=resolved_now,
            )
        else:
            proposal.metadata_json = metadata
            proposal.proposal_status = decision
            if decision == "accepted":
                proposal.accepted_at = resolved_now

    body_plan_id: int | None = None
    if plan_change_accepted:
        new_plan = _create_new_body_plan_version(
            db,
            user=user,
            previous_active_plan=active_plan,
            effect_payload={**effect_payload, "proposal_family": proposal_family},
            accepted_at=resolved_now,
        )
        body_plan_id = new_plan.id
        _create_calibration_adjustment_entry_if_requested(
            db,
            user=user,
            proposal=proposal,
            proposal_family=proposal_family,
            body_plan_id=new_plan.id,
            effect_payload=effect_payload,
            effective_from=effective_from,
        )
        recompute_day_budget_ledger(
            db,
            user_id=user.id,
            local_date=effective_from,
            budget_kcal=new_plan.daily_budget_kcal,
        )

    db.commit()
    db.refresh(proposal)
    return CalibrationCommitResult(
        proposal_container_id=proposal.id,
        proposal_status=proposal.proposal_status,  # type: ignore[arg-type]
        body_plan_id=body_plan_id,
        effective_from=effective_from,
        current_budget_view=_build_calibration_commit_current_budget_view(
            db,
            user_id=user.id,
            local_date=effective_from,
        ),
        active_body_plan_view=build_active_body_plan_view(db, user_id=user.id),
    )


def apply_stored_calibration_proposal_action(
    db: Session,
    *,
    user: User,
    proposal_container_id: int,
    decision: CalibrationCommitDecision,
    accepted_at: datetime | None = None,
) -> CalibrationCommitResult:
    proposal = _load_calibration_proposal_or_raise(
        db,
        user=user,
        proposal_container_id=proposal_container_id,
    )
    _ensure_stored_proposal_actionable(proposal)
    local_date = str((proposal.metadata_json or {}).get("local_date") or "").strip()
    if not local_date:
        raise ValueError("stored calibration proposal is missing local_date")
    proposal_family, effect_payload = _stored_top_option_payload(proposal)
    return apply_calibration_proposal_commit(
        db,
        user=user,
        local_date=local_date,
        proposal_family=proposal_family,
        effect_payload=effect_payload,
        decision=decision,
        accepted_at=accepted_at,
        proposal_container_id=proposal.id,
        require_active_stored_proposal=True,
    )
