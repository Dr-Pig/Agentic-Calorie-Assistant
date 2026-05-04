from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView

from .calibration_model import CalibrationModelInputs, CalibrationModelResult, build_calibration_model
from .calibration_proposal_gate import (
    ALL_OPTION_FAMILIES,
    BodyPlanStatus,
    CalibrationProposalGateInputs,
    CalibrationProposalGateResult,
    CurrentBudgetStatus,
    RecoveryViability,
    build_calibration_proposal_gate,
)
from .calibration_proposal_response import (
    CalibrationProposalResponseResult,
    build_calibration_proposal_response,
)

PLAN_CHANGING_OPTION_FAMILIES = frozenset(
    {
        "budget_adjustment",
        "pace_adjustment",
        "plan_reset",
    }
)


@dataclass(frozen=True)
class BodyCalibrationDiagnosticRequest:
    model_inputs: CalibrationModelInputs
    current_budget_view: CurrentBudgetView
    active_body_plan_view: ActiveBodyPlanView
    current_budget_status: CurrentBudgetStatus = "unknown"
    rescue_recovery_viability: RecoveryViability = "unknown"
    recent_similar_proposal_open: bool = False
    proposal_cooldown_active: bool = False
    proposal_cooldown_reason: str | None = None


@dataclass(frozen=True)
class BodyCalibrationDiagnosticResult:
    calibration_result: CalibrationModelResult
    gate_result: CalibrationProposalGateResult
    response: CalibrationProposalResponseResult
    proposal_policy_packet: dict[str, Any]
    trace_envelope: dict[str, Any]


def _active_body_plan_status(view: ActiveBodyPlanView) -> BodyPlanStatus:
    if view.body_plan_id is None:
        return "inactive"
    if view.plan_status == "active":
        return "active"
    if view.plan_status == "inactive":
        return "inactive"
    return "unknown"


def _top_option_family(response: CalibrationProposalResponseResult) -> str | None:
    if response.top_option is not None and response.top_option.option_type:
        return response.top_option.option_type
    return response.proposal_family


def _allowed_families_for_policy(
    *,
    gate_result: CalibrationProposalGateResult,
    top_option_family: str | None,
) -> list[str]:
    if gate_result.allowed_option_families:
        return list(gate_result.allowed_option_families)
    if top_option_family in {"logging_quality_first", "monitor_only"}:
        return [top_option_family]
    return []


def _blocked_families_for_policy(allowed_option_families: list[str]) -> list[str]:
    allowed = set(allowed_option_families)
    return [family for family in ALL_OPTION_FAMILIES if family not in allowed]


def _build_proposal_policy_packet(
    *,
    gate_result: CalibrationProposalGateResult,
    response: CalibrationProposalResponseResult,
) -> dict[str, Any]:
    top_option_family = _top_option_family(response)
    proposal_family = response.proposal_family or top_option_family
    allowed_option_families = _allowed_families_for_policy(
        gate_result=gate_result,
        top_option_family=top_option_family,
    )
    plan_change_required = proposal_family in PLAN_CHANGING_OPTION_FAMILIES
    return {
        "decision_mode": "deterministic",
        "top_option_family": top_option_family,
        "proposal_family": proposal_family,
        "allowed_option_families": allowed_option_families,
        "blocked_option_families": _blocked_families_for_policy(allowed_option_families),
        "plan_change_required": plan_change_required,
        "requires_accept_before_plan_mutation": plan_change_required,
        "plan_mutation_authorized": False,
        "ledger_mutation_authorized": False,
        "active_plan_mutation_allowed_now": False,
        "llm_role": "explain_only",
    }


def _build_trace_envelope() -> dict[str, Any]:
    return {
        "decision_mode": "deterministic",
        "llm_role": "explain_only",
        "live_tool_calling": False,
        "automatic_calibration_enabled": False,
        "rescue_enabled": False,
        "recommendation_enabled": False,
        "proactive_enabled": False,
    }


def build_body_calibration_diagnostic(
    request: BodyCalibrationDiagnosticRequest,
) -> BodyCalibrationDiagnosticResult:
    calibration_result = build_calibration_model(request.model_inputs)
    gate_result = build_calibration_proposal_gate(
        CalibrationProposalGateInputs(
            calibration_result=calibration_result,
            current_budget_status=request.current_budget_status,
            active_body_plan_status=_active_body_plan_status(request.active_body_plan_view),
            rescue_recovery_viability=request.rescue_recovery_viability,
            recent_similar_proposal_open=request.recent_similar_proposal_open,
            proposal_cooldown_active=request.proposal_cooldown_active,
            proposal_cooldown_reason=request.proposal_cooldown_reason,
        )
    )
    response = build_calibration_proposal_response(
        calibration_result=calibration_result,
        gate_result=gate_result,
        current_budget_view=request.current_budget_view,
        active_body_plan_view=request.active_body_plan_view,
    )
    return BodyCalibrationDiagnosticResult(
        calibration_result=calibration_result,
        gate_result=gate_result,
        response=response,
        proposal_policy_packet=_build_proposal_policy_packet(
            gate_result=gate_result,
            response=response,
        ),
        trace_envelope=_build_trace_envelope(),
    )


async def process_body_calibration_request(*, request: Any) -> Any:
    if isinstance(request, BodyCalibrationDiagnosticRequest):
        return build_body_calibration_diagnostic(request)
    raise NotImplementedError("Unsupported body calibration request shape.")
