from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.body.application.exercise_estimator import estimate_exercise_kcal
from app.body.contracts.exercise_event import ExerciseEstimateInput


_REQUIRED_CASE_IDS = (
    "weight_observation_chat_preview",
    "body_fat_answer_only_boundary",
    "exercise_met_estimate_preview",
    "exercise_user_asserted_preview",
    "effective_budget_what_if_projection",
)
_SEMANTIC_OWNER = "future_llm_extraction_after_activation"
_DETERMINISTIC_ROLE = "validate_contract_boundaries_and_preview_math"
_FALSE_FIELDS = (
    "runtime_connected",
    "runtime_truth_changed",
    "mutation_changed",
    "observation_write_authorized",
    "active_body_plan_mutation_allowed",
    "body_plan_mutated",
    "day_budget_ledger_mutated",
    "exercise_event_persisted",
    "ledger_entry_created",
    "ledger_write_authorized",
    "current_budget_view_refreshed",
)
_MUTATION_BLOCK_FIELDS = tuple(
    field
    for field in _FALSE_FIELDS
    if field.endswith(("connected", "changed", "authorized", "allowed", "mutated", "persisted", "created", "refreshed"))
)


def _base_case(
    *,
    case_id: str,
    workflow_family: str,
    normalized_handoff: str,
    disposition: str = "not_applicable",
    extraction_decision_mode: str = "llm_required_after_activation",
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "workflow_family": workflow_family,
        "normalized_handoff": normalized_handoff,
        "disposition": disposition,
        "extraction_decision_mode": extraction_decision_mode,
        "semantic_owner": _SEMANTIC_OWNER,
        "deterministic_role": _DETERMINISTIC_ROLE,
        "projection_only": False,
        "calibration_handoff_required_if_plan_change": False,
        "current_budget_view_source_read_only": False,
        **dict.fromkeys(_FALSE_FIELDS, False),
    }


def _exercise_case(
    *,
    case_id: str,
    estimate_input: ExerciseEstimateInput,
) -> dict[str, Any]:
    estimate = estimate_exercise_kcal(estimate_input)
    return _base_case(
        case_id=case_id,
        workflow_family="exercise",
        normalized_handoff="exercise_estimate_candidate",
    ) | {
        "calculation_basis": estimate.estimation_basis,
        "estimated_kcal": estimate.estimated_kcal,
        "deterministic_formula_used": bool(estimate.trace.get("deterministic_formula_used")),
    }


def _cases() -> list[dict[str, Any]]:
    return [
        _base_case(
            case_id="weight_observation_chat_preview",
            workflow_family="body_observation",
            normalized_handoff="observation_create_candidate",
        )
        | {"calibration_handoff_required_if_plan_change": True},
        _base_case(
            case_id="body_fat_answer_only_boundary",
            workflow_family="general_chat",
            normalized_handoff="answer_only_read_model_boundary",
            disposition="answer_only",
            extraction_decision_mode="not_applicable",
        ),
        _exercise_case(
            case_id="exercise_met_estimate_preview",
            estimate_input=ExerciseEstimateInput(
                exercise_type="walking",
                duration_minutes=60,
                body_weight_kg=70,
                estimation_basis="met_formula",
            ),
        ),
        _exercise_case(
            case_id="exercise_user_asserted_preview",
            estimate_input=ExerciseEstimateInput(
                exercise_type="strength_training",
                duration_minutes=45,
                estimation_basis="user_asserted",
                user_asserted_kcal=320,
            ),
        ),
        _base_case(
            case_id="effective_budget_what_if_projection",
            workflow_family="budget_preview",
            normalized_handoff="read_only_effective_budget_projection",
            extraction_decision_mode="not_applicable",
        )
        | {
            "projection_only": True,
            "current_budget_view_source_read_only": True,
            "base_budget_kcal": 1800,
            "consumed_kcal": 900,
            "exercise_bonus_preview_kcal": 250,
            "projected_effective_budget_kcal": 2050,
            "projected_remaining_kcal": 1150,
        },
    ]


def _validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if [str(case.get("case_id") or "") for case in cases] != list(_REQUIRED_CASE_IDS):
        blockers.append("required_case_order_mismatch")
    for case in cases:
        case_id = str(case.get("case_id") or "unknown")
        for field in _MUTATION_BLOCK_FIELDS:
            if case.get(field) is not False:
                blockers.append(f"{case_id}.{field}")
        if case.get("semantic_owner") != _SEMANTIC_OWNER:
            blockers.append(f"{case_id}.semantic_owner_drift")
        if case.get("deterministic_role") != _DETERMINISTIC_ROLE:
            blockers.append(f"{case_id}.deterministic_role_drift")
    return blockers


def build_body_budget_preview_contract_artifact() -> dict[str, Any]:
    cases = _cases()
    blockers = _validate_cases(cases)
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_body_budget_preview_contract",
        "status": "pass" if not blockers else "fail",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "owner": "app/body",
        "consumer": "future body/exercise/effective-budget activation slices",
        "retirement_trigger": "approved body_exercise_budget_writeback_activation_plan",
        "claim_scope": "no_runtime_body_budget_preview_contract_fixture",
        "local_only": True,
        "diagnostic_only": True,
        "fixture_only": True,
        **dict.fromkeys(_FALSE_FIELDS, False),
        "best_practice_evidence": {
            "required": False,
            "rationale": "fixture-only no-runtime contract; existing deterministic estimator is reused without writeback",
        },
        "blockers": blockers,
        "summary": {
            "case_count": len(cases),
            "exercise_preview_case_count": sum(1 for case in cases if case["workflow_family"] == "exercise"),
            "projection_case_count": sum(1 for case in cases if case["projection_only"]),
        },
        "cases": cases,
    }


__all__ = ["build_body_budget_preview_contract_artifact"]
