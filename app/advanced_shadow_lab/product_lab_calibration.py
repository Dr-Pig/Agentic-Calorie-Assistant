from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.body.application.body_calibration_service import (
    BodyCalibrationDiagnosticRequest,
    build_body_calibration_diagnostic,
)
from app.body.application.calibration_model import CalibrationModelInputs
from app.shared.contracts.sidecar_activation import offline_sidecar_contract
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_calibration"
)
ARTIFACT_TYPE = "advanced_product_lab_calibration_runtime_artifact"
PRIMARY_ACTIONS = ["accept_calibration_proposal", "dismiss_calibration_proposal"]
ACTIVATION_FLAGS = {
    "served_to_mainline_user": False,
    "canonical_product_mutation_allowed": False,
    "durable_product_memory_written": False,
    "production_scheduler_delivery_allowed": False,
    "manager_context_packet_changed": False,
}


def run_product_lab_calibration(
    *,
    fixture_inputs: Mapping[str, Any],
    enabled: bool = False,
) -> dict[str, Any]:
    if not enabled:
        return _artifact(status="not_applicable", lab_changed=False)
    diagnostic = build_body_calibration_diagnostic(
        BodyCalibrationDiagnosticRequest(
            model_inputs=_model_inputs(fixture_inputs),
            current_budget_view=_current_budget(fixture_inputs),
            active_body_plan_view=_active_plan(fixture_inputs),
            current_budget_status=str(fixture_inputs.get("calibration_current_budget_status") or "on_track"),
            rescue_recovery_viability=str(fixture_inputs.get("calibration_rescue_recovery_viability") or "unknown"),
            recent_similar_proposal_open=fixture_inputs.get("calibration_recent_similar_proposal_open") is True,
        )
    )
    response = diagnostic.response
    if not response.surfaced or response.top_option is None:
        return _artifact(
            status="pass",
            lab_changed=False,
            diagnostic=diagnostic,
            omission_reason=f"calibration_posture_{diagnostic.calibration_result.calibration_posture}",
        )
    card = _proposal_card(diagnostic=diagnostic, fixture_inputs=fixture_inputs)
    return _artifact(
        status="pass",
        lab_changed=True,
        diagnostic=diagnostic,
        proposal_card=card,
        primary_actions=PRIMARY_ACTIONS,
    )


def _artifact(
    *,
    status: str,
    lab_changed: bool,
    diagnostic: Any | None = None,
    proposal_card: Mapping[str, Any] | None = None,
    primary_actions: list[str] | None = None,
    omission_reason: str = "",
) -> dict[str, Any]:
    card = dict(proposal_card or {})
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "proposal_presented_to_lab": bool(card),
        "proposal_family": str(card.get("proposal_family") or ""),
        "calibration_confidence": _confidence(diagnostic),
        "proposal_card": card,
        "primary_actions": list(primary_actions or []),
        "omission_reason": omission_reason,
        "activation_flags": {
            "lab_user_facing_behavior_changed": lab_changed,
            **dict(ACTIVATION_FLAGS),
        },
        "chat_first": True,
        "source_diagnostic": _diagnostic_payload(diagnostic),
        "blockers": [],
        "suppress_other_product_packets": bool(card),
        **dict(ACTIVATION_FLAGS),
        **dict(FALSE_FLAGS),
    }


def _proposal_card(
    *,
    diagnostic: Any,
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    response = diagnostic.response
    option = response.top_option
    effect = dict(option.effect_payload)
    active = _active_plan(fixture_inputs)
    previous = int(active.daily_budget_kcal or active.recommended_target_kcal or 0)
    proposed = int(effect.get("new_daily_budget_kcal") or previous)
    return {
        "card_kind": "calibration_proposal_lab",
        "default_surface": "chat",
        "proposal_family": str(response.proposal_family or option.option_type),
        "headline": "Calibration suggests a daily target update.",
        "summary": response.reply_text,
        "trend_evidence": _trend_evidence(_model_inputs(fixture_inputs)),
        "previous_daily_budget_kcal": previous,
        "proposed_daily_budget_kcal": proposed,
        "daily_budget_delta_kcal": int(effect.get("delta_kcal") or proposed - previous),
        "expected_effect_summary": str(effect.get("expected_effect_summary") or ""),
        "guardrail_summary": str(effect.get("guardrail_summary") or ""),
        "effect_payload": effect,
        "primary_actions": list(PRIMARY_ACTIONS),
        "lab_body_plan_preview": {
            **active.model_dump(),
            "daily_budget_kcal": proposed,
            "recommended_target_kcal": proposed,
            "plan_source": "calibration_lab_accept_preview",
        },
        "source_refs": ["calibration_diagnostic:body_trend"],
    }


def _model_inputs(source: Mapping[str, Any]) -> CalibrationModelInputs:
    value = _mapping(source.get("calibration_model_inputs"))
    return CalibrationModelInputs(**value)


def _current_budget(source: Mapping[str, Any]) -> CurrentBudgetView:
    return CurrentBudgetView.model_validate(
        _mapping(source.get("calibration_current_budget_view"))
    )


def _active_plan(source: Mapping[str, Any]) -> ActiveBodyPlanView:
    return ActiveBodyPlanView.model_validate(
        _mapping(source.get("calibration_active_body_plan_view"))
    )


def _trend_evidence(inputs: CalibrationModelInputs) -> dict[str, Any]:
    return {
        "observation_window_days": inputs.observation_window_days,
        "body_observation_count": inputs.body_observation_count,
        "intake_coverage": inputs.intake_coverage,
        "operating_expenditure_shift_kcal": inputs.operating_expenditure_shift_kcal,
    }


def _diagnostic_payload(diagnostic: Any | None) -> dict[str, Any]:
    return {} if diagnostic is None else asdict(diagnostic)


def _confidence(diagnostic: Any | None) -> str:
    if diagnostic is None:
        return ""
    return str(diagnostic.calibration_result.calibration_confidence)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_product_lab_calibration"]
