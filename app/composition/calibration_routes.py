from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.body.application.calibration_model import CalibrationModelInputs
from app.composition.calibration_commit_bridge import (
    StoredCalibrationProposalNotActionable,
    apply_calibration_proposal_commit,
    apply_stored_calibration_proposal_action,
)
from app.composition.calibration_proposal_expiry import expire_stale_calibration_proposals
from app.composition.calibration_proposal_inbox import (
    load_calibration_proposal_history,
    load_open_calibration_proposal_inbox,
)
from app.composition.calibration_preview_service import (
    build_calibration_preview_from_history,
    build_calibration_preview_from_model_inputs,
)
from app.database import get_db, get_or_create_user
from app.shared.domain import ProposalContainer
from app.shared.infra.models import User

router = APIRouter()
public_router = APIRouter()


def _validate_accepted_at(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate or ("T" not in candidate and " " not in candidate):
        raise ValueError("accepted_at must include a date and time")
    try:
        datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError("accepted_at must be an ISO datetime") from exc
    return candidate


class CalibrationProposalPreviewRequest(BaseModel):
    user_id: str
    local_date: str
    current_budget_status: Literal["on_track", "tight", "over_budget", "unknown"] = "unknown"
    rescue_recovery_viability: Literal["viable", "strained", "non_viable", "unknown"] = "unknown"
    recent_similar_proposal_open: bool = False
    persist_proposal: bool = False
    model_inputs: CalibrationModelInputs


class CalibrationProposalPreviewFromHistoryRequest(BaseModel):
    user_id: str
    local_date: str
    window_days: int = Field(default=14, gt=0)
    current_budget_status: Literal["on_track", "tight", "over_budget", "unknown"] = "unknown"
    rescue_recovery_viability: Literal["viable", "strained", "non_viable", "unknown"] = "unknown"
    recent_similar_proposal_open: bool = False
    persist_proposal: bool = False


class CalibrationProposalActionRequest(BaseModel):
    user_id: str
    local_date: str
    proposal_family: str
    effect_payload: dict[str, object]
    action: Literal["accept_calibration_proposal", "defer_calibration_proposal", "reject_calibration_proposal"]
    accepted_at: str | None = None

    @field_validator("accepted_at")
    @classmethod
    def _validate_accepted_at_field(cls, value: str | None) -> str | None:
        return _validate_accepted_at(value)


class StoredCalibrationProposalActionRequest(BaseModel):
    user_id: str
    proposal_container_id: int
    action: Literal["accept_calibration_proposal", "defer_calibration_proposal", "reject_calibration_proposal"]
    accepted_at: str | None = None

    @field_validator("accepted_at")
    @classmethod
    def _validate_accepted_at_field(cls, value: str | None) -> str | None:
        return _validate_accepted_at(value)


class CalibrationProposalExpiryRequest(BaseModel):
    user_id: str
    now_at: str | None = None


def _proposal_inbox_payload(proposal: ProposalContainer) -> dict[str, object]:
    metadata = proposal.metadata if isinstance(proposal.metadata, dict) else {}
    return {
        "proposal_container_id": proposal.proposal_container_id,
        "proposal_type": proposal.proposal_type,
        "proposal_status": proposal.proposal_status,
        "top_option_id": proposal.top_option_id,
        "local_date": metadata.get("local_date"),
        "proposal_family": metadata.get("proposal_family"),
        "created_at": proposal.created_at,
        "accepted_at": proposal.accepted_at,
        "options": [option.model_dump(mode="json") for option in proposal.options],
    }


def _proposal_history_payload(proposal: ProposalContainer) -> dict[str, object]:
    metadata = proposal.metadata if isinstance(proposal.metadata, dict) else {}
    primary_option = next((option for option in proposal.options if option.proposal_option_id == proposal.top_option_id), None)
    if primary_option is None:
        primary_option = next((option for option in proposal.options if option.is_primary), None)
    return {
        "proposal_container_id": proposal.proposal_container_id,
        "proposal_type": proposal.proposal_type,
        "proposal_status": proposal.proposal_status,
        "top_option_id": proposal.top_option_id,
        "local_date": metadata.get("local_date"),
        "proposal_family": metadata.get("proposal_family"),
        "created_at": proposal.created_at,
        "accepted_at": proposal.accepted_at,
        "expired_at": metadata.get("expired_at"),
        "expiry_reason": metadata.get("expiry_reason"),
        "primary_option_type": primary_option.option_type if primary_option is not None else None,
        "primary_option_label": primary_option.option_label if primary_option is not None else None,
        "primary_option_summary": primary_option.option_summary if primary_option is not None else None,
    }


@router.get("/calibration/proposals/open")
@public_router.get("/calibration/proposals/open")
def open_calibration_proposals(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=50),
    db=Depends(get_db),
) -> dict[str, object]:
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        return {
            "user_id": user_id,
            "open_count": 0,
            "proposals": [],
        }
    proposals = load_open_calibration_proposal_inbox(db, user_id=user.id, limit=limit)
    return {
        "user_id": user_id,
        "open_count": len(proposals),
        "proposals": [_proposal_inbox_payload(proposal) for proposal in proposals],
    }


@router.get("/calibration/proposals/history")
@public_router.get("/calibration/proposals/history")
def calibration_proposal_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    db=Depends(get_db),
) -> dict[str, object]:
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        return {
            "user_id": user_id,
            "history_count": 0,
            "proposals": [],
        }
    proposals = load_calibration_proposal_history(db, user_id=user.id, limit=limit)
    return {
        "user_id": user_id,
        "history_count": len(proposals),
        "proposals": [_proposal_history_payload(proposal) for proposal in proposals],
    }


@router.post("/calibration/proposal/preview")
def calibration_proposal_preview(
    request: CalibrationProposalPreviewRequest,
    db=Depends(get_db),
) -> dict[str, object]:
    user = get_or_create_user(db, request.user_id)
    preview = build_calibration_preview_from_model_inputs(
        db,
        user=user,
        local_date=request.local_date,
        model_inputs=request.model_inputs,
        current_budget_status=request.current_budget_status,
        rescue_recovery_viability=request.rescue_recovery_viability,
        recent_similar_proposal_open=request.recent_similar_proposal_open,
        persist_proposal=request.persist_proposal,
    )
    payload: dict[str, object] = {
        "calibration_result": preview.calibration_result,
        "gate_result": preview.gate_result,
        "response": preview.response,
        "diagnostic": preview.diagnostic,
        "proposal_policy_packet": preview.proposal_policy_packet,
        "trace_envelope": preview.trace_envelope,
    }
    if request.persist_proposal:
        payload["proposal_artifact"] = preview.proposal_artifact
    return payload


@router.post("/calibration/proposal/preview-from-history")
@public_router.post("/calibration/proposal/preview-from-history")
def calibration_proposal_preview_from_history(
    request: CalibrationProposalPreviewFromHistoryRequest,
    db=Depends(get_db),
) -> dict[str, object]:
    user = get_or_create_user(db, request.user_id)
    try:
        preview = build_calibration_preview_from_history(
            db,
            user=user,
            local_date=request.local_date,
            window_days=request.window_days,
            current_budget_status=request.current_budget_status,
            rescue_recovery_viability=request.rescue_recovery_viability,
            recent_similar_proposal_open=request.recent_similar_proposal_open,
            persist_proposal=request.persist_proposal,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 409 if detail == "active_body_plan_required_for_calibration_input_assembly" else 422
        raise HTTPException(status_code=status_code, detail=detail) from exc

    payload: dict[str, object] = {
        "calibration_result": preview.calibration_result,
        "gate_result": preview.gate_result,
        "response": preview.response,
        "diagnostic": preview.diagnostic,
        "proposal_policy_packet": preview.proposal_policy_packet,
        "trace_envelope": preview.trace_envelope,
        "input_assembly": preview.input_assembly,
    }
    if request.persist_proposal:
        payload["proposal_artifact"] = preview.proposal_artifact
    return payload


@router.post("/calibration/proposal/action")
def calibration_proposal_action(
    request: CalibrationProposalActionRequest,
    db=Depends(get_db),
) -> dict[str, object]:
    user = get_or_create_user(db, request.user_id)
    decision = {
        "accept_calibration_proposal": "accepted",
        "defer_calibration_proposal": "dismissed",
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


@router.post("/calibration/proposal/stored-action")
@public_router.post("/calibration/proposal/stored-action")
def stored_calibration_proposal_action(
    request: StoredCalibrationProposalActionRequest,
    db=Depends(get_db),
) -> dict[str, object]:
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    decision = {
        "accept_calibration_proposal": "accepted",
        "defer_calibration_proposal": "dismissed",
        "reject_calibration_proposal": "rejected",
    }[request.action]
    try:
        result = apply_stored_calibration_proposal_action(
            db,
            user=user,
            proposal_container_id=request.proposal_container_id,
            decision=decision,  # type: ignore[arg-type]
            accepted_at=datetime.fromisoformat(request.accepted_at) if request.accepted_at else None,
        )
    except StoredCalibrationProposalNotActionable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "proposal_container_id": result.proposal_container_id,
        "proposal_status": result.proposal_status,
        "body_plan_id": result.body_plan_id,
        "effective_from": result.effective_from,
        "current_budget_view": result.current_budget_view.model_dump(mode="json"),
        "active_body_plan_view": result.active_body_plan_view.model_dump(mode="json"),
    }


@router.post("/calibration/proposals/expire-stale")
def expire_stale_calibration_proposals_route(
    request: CalibrationProposalExpiryRequest,
    db=Depends(get_db),
) -> dict[str, object]:
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if user is None:
        return {
            "expired_count": 0,
            "expired_proposal_container_ids": [],
        }
    try:
        result = expire_stale_calibration_proposals(
            db,
            user=user,
            now_at=datetime.fromisoformat(request.now_at) if request.now_at else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "expired_count": result.expired_count,
        "expired_proposal_container_ids": result.expired_proposal_container_ids,
    }


__all__ = ["public_router", "router"]
