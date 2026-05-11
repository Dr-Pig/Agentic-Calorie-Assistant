from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.composition.current_budget_answer import (
    build_remaining_budget_answer_contract_from_views,
)
from app.composition.phase_a_boundary_projection import build_budget_boundary_projection
from app.shared.contracts.sidecar_activation import offline_sidecar_contract
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_no_plan_degraded"
)
ARTIFACT_TYPE = "advanced_product_lab_no_plan_degraded_artifact"


def run_product_lab_no_plan_degraded(
    *,
    fixture_inputs: Mapping[str, Any],
    enabled: bool = False,
) -> dict[str, Any]:
    if not enabled:
        return _not_applicable()
    current_budget = CurrentBudgetView.model_validate(
        _mapping(fixture_inputs.get("no_plan_current_budget_view"))
    )
    active_plan = ActiveBodyPlanView.model_validate(
        _mapping(fixture_inputs.get("no_plan_active_body_plan_view"))
    )
    answer = build_remaining_budget_answer_contract_from_views(
        current_budget=current_budget,
        active_plan=active_plan,
    )
    projection = build_budget_boundary_projection(
        remaining_budget=answer,
        active_body_plan_present=False,
    )
    blockers = _blockers(answer=answer, projection=projection)
    intake = _intake_packet(fixture_inputs)
    budget = _budget_query_packet(answer)
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "remaining_budget_contract": asdict(answer),
        "budget_boundary_projection": projection.model_dump(mode="json"),
        "intake_logging_allowed_without_plan": True,
        "intake_packet": intake,
        "budget_query_packet": budget,
        "today_ui_mirror": _today_ui_mirror(),
        "advanced_trigger_policy": _advanced_trigger_policy(),
        "body_plan_created": False,
        "day_budget_ledger_created": False,
        "meal_thread_mutated": False,
        "canonical_product_mutation_allowed": False,
        "served_to_mainline_user": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "suppress_other_product_packets": True,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def inactive_rescue_artifact() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_rescue_runtime_artifact",
        "artifact_schema_version": "1.0",
        "status": "not_applicable",
        "proposal_presented_to_lab": False,
        "blockers": [],
        **dict(FALSE_FLAGS),
    }


def inactive_recommendation_artifact() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_runtime_artifact",
        "artifact_schema_version": "1.0",
        "status": "not_applicable",
        "offer_synthesis": {},
        "pending_intake_handoff_packet": {},
        "recommendation_served_to_lab": False,
        "proactive_recommendation_candidate_allowed": False,
        "blockers": [],
        **dict(FALSE_FLAGS),
    }


def inactive_proactive_artifact(turn: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_proactive_runtime_artifact",
        "artifact_schema_version": "1.0",
        "status": "not_applicable",
        "session_id": str(turn.get("session_id") or ""),
        "turn_id": str(turn.get("turn_id") or ""),
        "candidate_count": 0,
        "candidates": [],
        "omission_traces": [{"omission_reason": "no_active_body_plan"}],
        "scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "blockers": [],
    }


def _intake_packet(fixture_inputs: Mapping[str, Any]) -> dict[str, Any]:
    fixture = _mapping(fixture_inputs.get("no_plan_intake_fixture"))
    return {
        "meal_title": str(fixture.get("meal_title") or ""),
        "estimated_kcal": _int(fixture.get("estimated_kcal")),
        "intake_logged_in_lab": True,
        "remaining_budget_visible": False,
        "daily_target_visible": False,
        "source_refs": [str(ref) for ref in fixture.get("source_refs") or []],
    }


def _budget_query_packet(answer: Any) -> dict[str, Any]:
    return {
        "status": answer.status,
        "daily_target_kcal": answer.daily_target_kcal,
        "remaining_kcal": answer.remaining_kcal,
        "concrete_remaining_kcal_allowed": False,
        "onboarding_cta": {
            "action": "start_onboarding",
            "surface": "chat",
            "mutation_requested": False,
        },
    }


def _today_ui_mirror() -> dict[str, Any]:
    return {
        "surface": "today",
        "no_active_body_plan": True,
        "daily_target_visible": False,
        "remaining_budget_visible": False,
        "daily_target_kcal": None,
        "remaining_kcal": None,
        "onboarding_entry_visible": True,
    }


def _advanced_trigger_policy() -> dict[str, bool]:
    return {
        "recommendation_allowed": False,
        "rescue_allowed": False,
        "calibration_allowed": False,
        "proactive_allowed": False,
    }


def _blockers(*, answer: Any, projection: Any) -> list[str]:
    decision = projection.fallback_honesty_decision
    blockers: list[str] = []
    if answer.status != "onboarding_required":
        blockers.append(f"remaining_budget.status_{answer.status}")
    if decision.budget_answer_mode != "degraded":
        blockers.append(f"budget_answer_mode.{decision.budget_answer_mode}")
    if decision.concrete_remaining_kcal_allowed:
        blockers.append("concrete_remaining_kcal_allowed")
    if not decision.onboarding_guidance_allowed:
        blockers.append("onboarding_guidance_not_allowed")
    return blockers


def _not_applicable() -> dict[str, Any]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "not_applicable",
        "blockers": [],
        **dict(FALSE_FLAGS),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "inactive_proactive_artifact",
    "inactive_recommendation_artifact",
    "inactive_rescue_artifact",
    "run_product_lab_no_plan_degraded",
]
