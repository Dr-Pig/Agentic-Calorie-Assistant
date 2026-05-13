from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab import product_lab_planned_event_rescue as planned_event
from app.advanced_shadow_lab.product_lab_calibration import run_product_lab_calibration
from app.advanced_shadow_lab.product_lab_exercise import run_product_lab_exercise_budget
from app.advanced_shadow_lab.product_lab_planned_event_guidance import (
    run_product_lab_planned_event_guidance,
)
from app.advanced_shadow_lab.product_lab_no_plan_degraded import (
    inactive_proactive_artifact,
    inactive_recommendation_artifact,
    inactive_rescue_artifact,
    run_product_lab_no_plan_degraded,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from app.advanced_shadow_lab.product_lab_recommendation import run_product_lab_recommendation
from app.advanced_shadow_lab.product_lab_recommendation_rescue_posture import (
    build_recommendation_rescue_posture_bridge,
)
from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue
from app.advanced_shadow_lab.product_lab_weekly_insight import (
    run_product_lab_weekly_insight,
)


def run_product_lab_product_artifacts(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
    prior_action_state: Mapping[str, Any] | None = None,
    prior_control_journal: list[Mapping[str, Any]] | None = None,
    manager_selected_reusable_meal_artifact: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    no_plan_enabled = turn.get("no_plan_degraded_enabled") is True
    no_plan = run_product_lab_no_plan_degraded(
        fixture_inputs=fixture_inputs,
        enabled=no_plan_enabled,
    )
    recommendation_rescue_bridge = build_recommendation_rescue_posture_bridge(
        fixture_inputs=fixture_inputs,
    )
    recommendation_inputs = _recommendation_fixture_inputs(
        fixture_inputs,
        recommendation_rescue_bridge,
    )
    recommendation = (
        inactive_recommendation_artifact()
        if no_plan_enabled
        else run_product_lab_recommendation(
            turn=turn,
            fixture_inputs=recommendation_inputs,
            memory_context_pack=memory_context_pack,
            reusable_meal_context_pack=manager_selected_reusable_meal_artifact or {},
        )
    )
    rescue = (
        inactive_rescue_artifact()
        if no_plan_enabled
        else run_product_lab_rescue(
            fixture_inputs=runtime_inputs,
            recommendation_artifact=recommendation,
        )
    )
    calibration = run_product_lab_calibration(
        fixture_inputs=runtime_inputs,
        enabled=turn.get("calibration_enabled") is True and not no_plan_enabled,
    )
    planned_rescue = planned_event.run_product_lab_planned_event_rescue(
        fixture_inputs=runtime_inputs,
        enabled=turn.get("planned_event_rescue_enabled") is True and not no_plan_enabled,
    )
    planned_guidance = run_product_lab_planned_event_guidance(
        fixture_inputs=runtime_inputs,
        enabled=turn.get("planned_event_guidance_enabled") is True and not no_plan_enabled,
    )
    exercise = run_product_lab_exercise_budget(
        fixture_inputs=runtime_inputs,
        enabled=turn.get("exercise_budget_enabled") is True and not no_plan_enabled,
    )
    weekly_insight = run_product_lab_weekly_insight(
        fixture_inputs=runtime_inputs,
        enabled=turn.get("weekly_insight_enabled") is True and not no_plan_enabled,
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
            weekly_insight_artifact=weekly_insight,
            action_state=prior_action_state,
            prior_control_journal=list(prior_control_journal or []),
        )
    )
    return {
        "recommendation": recommendation,
        "recommendation_rescue_posture_bridge": recommendation_rescue_bridge,
        "rescue": rescue,
        "calibration": calibration,
        "no_plan_degraded": no_plan,
        "planned_event_guidance": planned_guidance,
        "planned_event_rescue": planned_rescue,
        "exercise_budget": exercise,
        "weekly_insight": weekly_insight,
        "proactive": proactive,
    }


def product_lab_product_artifact_blockers(
    artifacts: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    for key in [
        "recommendation",
        "rescue",
        "calibration",
        "no_plan_degraded",
        "planned_event_guidance",
        "proactive",
    ]:
        blockers.extend(_blockers(key, artifacts.get(key, {})))
    bridge = artifacts.get("recommendation_rescue_posture_bridge", {})
    if bridge.get("status") == "blocked":
        blockers.extend(_blockers("recommendation_rescue_posture_bridge", bridge))
    weekly = artifacts.get("weekly_insight", {})
    if weekly.get("status") == "blocked":
        blockers.extend(_blockers("weekly_insight", weekly))
    return blockers


def _blockers(name: str, artifact: Mapping[str, Any]) -> list[str]:
    return [f"product_{name}.{blocker}" for blocker in artifact.get("blockers") or []]


def _recommendation_fixture_inputs(
    fixture_inputs: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> Mapping[str, Any]:
    value = bridge.get("recommendation_fixture_inputs")
    return value if isinstance(value, Mapping) else fixture_inputs


__all__ = [
    "product_lab_product_artifact_blockers",
    "run_product_lab_product_artifacts",
]
