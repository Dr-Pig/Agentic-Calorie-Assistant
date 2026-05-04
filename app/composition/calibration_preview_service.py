from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.body.application import (
    BodyCalibrationDiagnosticRequest,
    build_active_body_plan_view,
    build_body_calibration_diagnostic,
)
from app.body.application.calibration_model import CalibrationModelInputs
from app.body.application.calibration_proposal_gate import CurrentBudgetStatus, RecoveryViability
from app.composition.calibration_input_assembler import CalibrationInputAssemblyResult
from app.composition.calibration_proposal_artifacts import (
    assert_calibration_proposal_persistence_clean_session,
    has_active_calibration_proposal,
    persist_calibration_proposal_artifact,
)
from app.composition.current_budget_read_model import build_current_budget_view
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView
from app.shared.infra.models import User


@dataclass(frozen=True)
class CalibrationPreviewResult:
    calibration_result: dict[str, Any]
    gate_result: dict[str, Any]
    response: dict[str, Any]
    diagnostic: dict[str, Any]
    proposal_policy_packet: dict[str, Any]
    trace_envelope: dict[str, Any]
    input_assembly: dict[str, Any] | None
    proposal_artifact: dict[str, Any] | None
    current_budget_view: CurrentBudgetView
    active_body_plan_view: ActiveBodyPlanView


def _diagnostic_payload(diagnostic: Any) -> dict[str, Any]:
    return asdict(diagnostic)


def _payload_from_diagnostic(
    *,
    diagnostic: Any,
    current_budget_view: CurrentBudgetView,
    active_body_plan_view: ActiveBodyPlanView,
    input_assembly: CalibrationInputAssemblyResult | None,
    proposal_artifact: dict[str, Any] | None,
) -> CalibrationPreviewResult:
    diagnostic_payload = _diagnostic_payload(diagnostic)
    return CalibrationPreviewResult(
        calibration_result=diagnostic_payload["calibration_result"],
        gate_result=diagnostic_payload["gate_result"],
        response=diagnostic_payload["response"],
        diagnostic=diagnostic_payload,
        proposal_policy_packet=diagnostic.proposal_policy_packet,
        trace_envelope=diagnostic.trace_envelope,
        input_assembly=(
            {
                "model_inputs": asdict(input_assembly.model_inputs),
                "trace": input_assembly.trace,
            }
            if input_assembly is not None
            else None
        ),
        proposal_artifact=proposal_artifact,
        current_budget_view=current_budget_view,
        active_body_plan_view=active_body_plan_view,
    )


def _current_budget_status_from_view(current_budget: CurrentBudgetView) -> CurrentBudgetStatus:
    if int(current_budget.budget_kcal or 0) <= 0:
        return "unknown"
    remaining = int(current_budget.remaining_kcal or 0)
    if remaining < 0:
        return "over_budget"
    if remaining <= max(100, int(current_budget.budget_kcal or 0) // 10):
        return "tight"
    return "on_track"


def build_calibration_preview_from_model_inputs(
    db: Session,
    *,
    user: User,
    local_date: str,
    model_inputs: CalibrationModelInputs,
    current_budget_status: CurrentBudgetStatus = "unknown",
    rescue_recovery_viability: RecoveryViability = "unknown",
    recent_similar_proposal_open: bool = False,
    persist_proposal: bool = False,
) -> CalibrationPreviewResult:
    if persist_proposal:
        assert_calibration_proposal_persistence_clean_session(db)
    recent_open = recent_similar_proposal_open or has_active_calibration_proposal(db, user_id=int(user.id))
    current_budget = build_current_budget_view(db, user_id=int(user.id), local_date=local_date)
    active_plan = build_active_body_plan_view(db, user_id=int(user.id))
    diagnostic = build_body_calibration_diagnostic(
        BodyCalibrationDiagnosticRequest(
            model_inputs=model_inputs,
            current_budget_status=current_budget_status,
            rescue_recovery_viability=rescue_recovery_viability,
            recent_similar_proposal_open=recent_open,
            current_budget_view=current_budget,
            active_body_plan_view=active_plan,
        )
    )
    proposal_artifact = (
        persist_calibration_proposal_artifact(
            db,
            user=user,
            local_date=local_date,
            diagnostic=diagnostic,
        )
        if persist_proposal and diagnostic.response.surfaced and not recent_open
        else None
    )
    return _payload_from_diagnostic(
        diagnostic=diagnostic,
        current_budget_view=current_budget,
        active_body_plan_view=active_plan,
        input_assembly=None,
        proposal_artifact=proposal_artifact,
    )


def build_calibration_preview_from_history(
    db: Session,
    *,
    user: User,
    local_date: str,
    window_days: int = 14,
    current_budget_status: CurrentBudgetStatus | Literal["derive_from_budget"] = "derive_from_budget",
    rescue_recovery_viability: RecoveryViability = "unknown",
    recent_similar_proposal_open: bool = False,
    persist_proposal: bool = False,
) -> CalibrationPreviewResult:
    if persist_proposal:
        assert_calibration_proposal_persistence_clean_session(db)
    from app.composition.calibration_input_assembler import assemble_calibration_model_inputs_from_history

    assembly = assemble_calibration_model_inputs_from_history(
        db,
        user_id=int(user.id),
        local_date=local_date,
        window_days=window_days,
    )
    current_budget = build_current_budget_view(db, user_id=int(user.id), local_date=local_date)
    active_plan = build_active_body_plan_view(db, user_id=int(user.id))
    resolved_budget_status = (
        _current_budget_status_from_view(current_budget)
        if current_budget_status == "derive_from_budget"
        else current_budget_status
    )
    recent_open = recent_similar_proposal_open or has_active_calibration_proposal(db, user_id=int(user.id))
    diagnostic = build_body_calibration_diagnostic(
        BodyCalibrationDiagnosticRequest(
            model_inputs=assembly.model_inputs,
            current_budget_status=resolved_budget_status,
            rescue_recovery_viability=rescue_recovery_viability,
            recent_similar_proposal_open=recent_open,
            current_budget_view=current_budget,
            active_body_plan_view=active_plan,
        )
    )
    proposal_artifact = (
        persist_calibration_proposal_artifact(
            db,
            user=user,
            local_date=local_date,
            diagnostic=diagnostic,
        )
        if persist_proposal and diagnostic.response.surfaced and not recent_open
        else None
    )
    return _payload_from_diagnostic(
        diagnostic=diagnostic,
        current_budget_view=current_budget,
        active_body_plan_view=active_plan,
        input_assembly=assembly,
        proposal_artifact=proposal_artifact,
    )


__all__ = [
    "CalibrationPreviewResult",
    "build_calibration_preview_from_history",
    "build_calibration_preview_from_model_inputs",
]
