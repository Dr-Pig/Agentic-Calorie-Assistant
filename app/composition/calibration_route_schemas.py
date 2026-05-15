from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.body.application.calibration_model import CalibrationModelInputs


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
