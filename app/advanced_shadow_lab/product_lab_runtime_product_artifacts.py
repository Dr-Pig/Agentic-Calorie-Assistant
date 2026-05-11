from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab import product_lab_planned_event_rescue as planned_event
from app.advanced_shadow_lab.product_lab_calibration import run_product_lab_calibration
from app.advanced_shadow_lab.product_lab_no_plan_degraded import (
    inactive_proactive_artifact,
    inactive_recommendation_artifact,
    inactive_rescue_artifact,
    run_product_lab_no_plan_degraded,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from app.advanced_shadow_lab.product_lab_recommendation import run_product_lab_recommendation
from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue


def run_product_lab_product_artifacts(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
    prior_action_state: Mapping[str, Any] | None = None,
    prior_control_journal: list[Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    no_plan_enabled = turn.get("no_plan_degraded_enabled") is True
    no_plan = run_product_lab_no_plan_degraded(
        fixture_inputs=fixture_inputs,
        enabled=no_plan_enabled,
    )
    recommendation = (
        inactive_recommendation_artifact()
        if no_plan_enabled
        else run_product_lab_recommendation(
            turn=turn,
            fixture_inputs=fixture_inputs,
            memory_context_pack=memory_context_pack,
        )
    )
    rescue = (
        inactive_rescue_artifact()
        if no_plan_enabled
        else run_product_lab_rescue(fixture_inputs=runtime_inputs)
    )
    calibration = run_product_lab_calibration(
        fixture_inputs=runtime_inputs,
        enabled=turn.get("calibration_enabled") is True and not no_plan_enabled,
    )
    planned_rescue = planned_event.run_product_lab_planned_event_rescue(
        fixture_inputs=runtime_inputs,
        enabled=turn.get("planned_event_rescue_enabled") is True and not no_plan_enabled,
    )
    proactive = (
        inactive_proactive_artifact(turn)
        if no_plan_enabled
        else run_product_lab_proactive(
            turn=turn,
            fixture_inputs=runtime_inputs,
            memory_context_pack=memory_context_pack,
            recommendation_artifact=recommendation,
            rescue_artifact=rescue,
            action_state=prior_action_state,
            prior_control_journal=list(prior_control_journal or []),
        )
    )
    return {
        "recommendation": recommendation,
        "rescue": rescue,
        "calibration": calibration,
        "no_plan_degraded": no_plan,
        "planned_event_rescue": planned_rescue,
        "proactive": proactive,
    }


__all__ = ["run_product_lab_product_artifacts"]
