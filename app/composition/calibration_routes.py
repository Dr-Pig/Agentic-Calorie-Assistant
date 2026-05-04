from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.body.application import (
    BodyCalibrationDiagnosticRequest,
    build_active_body_plan_view,
    build_body_calibration_diagnostic,
)
from app.body.application.calibration_model import CalibrationModelInputs
from app.composition.calibration_commit_bridge import apply_calibration_proposal_commit
from app.composition.current_budget_read_model import build_current_budget_view
from app.database import get_db, get_or_create_user

router = APIRouter()


class CalibrationProposalPreviewRequest(BaseModel):
    user_id: str
    local_date: str
    current_budget_status: Literal["on_track", "tight", "over_budget", "unknown"] = "unknown"
    rescue_recovery_viability: Literal["viable", "strained", "non_viable", "unknown"] = "unknown"
    recent_similar_proposal_open: bool = False
    model_inputs: CalibrationModelInputs


class CalibrationProposalActionRequest(BaseModel):
    user_id: str
    local_date: str
    proposal_family: str
    effect_payload: dict[str, object]
    action: Literal["accept_calibration_proposal", "defer_calibration_proposal", "reject_calibration_proposal"]
    accepted_at: str | None = None


@router.post("/calibration/proposal/preview")
def calibration_proposal_preview(
    request: CalibrationProposalPreviewRequest,
    db=Depends(get_db),
) -> dict[str, object]:
    user = get_or_create_user(db, request.user_id)
    current_budget_view = build_current_budget_view(db, user_id=user.id, local_date=request.local_date)
    active_body_plan_view = build_active_body_plan_view(db, user_id=user.id)
    diagnostic = build_body_calibration_diagnostic(
        BodyCalibrationDiagnosticRequest(
            model_inputs=request.model_inputs,
            current_budget_status=request.current_budget_status,
            rescue_recovery_viability=request.rescue_recovery_viability,
            recent_similar_proposal_open=request.recent_similar_proposal_open,
            current_budget_view=current_budget_view,
            active_body_plan_view=active_body_plan_view,
        )
    )
    diagnostic_payload = asdict(diagnostic)
    return {
        "calibration_result": diagnostic_payload["calibration_result"],
        "gate_result": diagnostic_payload["gate_result"],
        "response": diagnostic_payload["response"],
        "diagnostic": diagnostic_payload,
        "proposal_policy_packet": diagnostic.proposal_policy_packet,
        "trace_envelope": diagnostic.trace_envelope,
    }


@router.post("/calibration/proposal/action")
def calibration_proposal_action(
    request: CalibrationProposalActionRequest,
    db=Depends(get_db),
) -> dict[str, object]:
    user = get_or_create_user(db, request.user_id)
    decision = {
        "accept_calibration_proposal": "accepted",
        "defer_calibration_proposal": "deferred_pending_reminder",
        "reject_calibration_proposal": "rejected",
    }[request.action]
    result = apply_calibration_proposal_commit(
        db,
        user=user,
        local_date=request.local_date,
        proposal_family=request.proposal_family,
        effect_payload=dict(request.effect_payload),
        decision=decision,  # type: ignore[arg-type]
        accepted_at=datetime.fromisoformat(request.accepted_at) if request.accepted_at else None,
    )
    return {
        "proposal_container_id": result.proposal_container_id,
        "proposal_status": result.proposal_status,
        "body_plan_id": result.body_plan_id,
        "effective_from": result.effective_from,
        "current_budget_view": result.current_budget_view.model_dump(mode="json"),
        "active_body_plan_view": result.active_body_plan_view.model_dump(mode="json"),
    }
