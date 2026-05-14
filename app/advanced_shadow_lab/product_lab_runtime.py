from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain import (
    run_advanced_shadow_e2e_fixture_chain,
)
from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_chat_surface import (
    build_advanced_product_lab_chat_surface,
)
from app.advanced_shadow_lab.product_lab_proactive_dashboard_mirror import (
    build_product_lab_proactive_dashboard_mirror,
)
from app.advanced_shadow_lab.product_lab_control_state import (
    build_product_lab_control_state,
)
from app.advanced_shadow_lab.product_lab_memory import (
    empty_product_lab_memory_context_pack,
    fixture_inputs_with_lab_memory_context,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.product_lab_runtime_manager_artifacts import (
    build_runtime_manager_artifacts,
)
from app.advanced_shadow_lab.product_lab_runtime_product_artifacts import (
    product_lab_product_artifact_blockers,
    run_product_lab_product_artifacts,
)
from app.advanced_shadow_lab.product_lab_turn_packets import chat_packet_blockers, chat_packets, lab_chat_response_packet
from app.advanced_shadow_lab.product_lab_turn_policy import (
    CAPABILITIES_EXERCISED,
    base_turn,
    blocked_turn,
    control_models,
    interaction_plan,
    lab_now_minute,
    mapping,
    observed_material_signals,
    stage_blockers,
    turn_blockers,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract

SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.product_lab_runtime")
def run_advanced_product_lab_turn(
    *,
    lab_mode: str,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    lab_memory_context_pack: Mapping[str, Any] | None = None,
    prior_control_journal: list[Mapping[str, Any]] | None = None,
    control_events: list[Mapping[str, Any]] | None = None,
    manager_script: list[Mapping[str, Any]] | None = None,
    manager_tool_store: ProductLabMemoryStore | None = None,
    prior_action_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = turn_blockers(lab_mode=lab_mode, turn=turn)
    if blockers:
        return blocked_turn(turn=turn, lab_mode=lab_mode, blockers=blockers)

    memory_context_pack = dict(lab_memory_context_pack or empty_product_lab_memory_context_pack(
        session_id=str(turn.get("session_id") or ""), turn_id=str(turn.get("turn_id") or "")
    ))
    runtime_inputs = fixture_inputs_with_lab_memory_context(fixture_inputs, memory_context_pack)
    manager_artifacts = build_runtime_manager_artifacts(
        lab_mode=lab_mode,
        turn=turn,
        runtime_inputs=runtime_inputs,
        manager_script=manager_script,
        manager_tool_store=manager_tool_store,
    )
    chain = run_advanced_shadow_e2e_fixture_chain(
        memory_summary_projection=mapping(fixture_inputs, "memory_summary_projection"),
        recommendation_payload=mapping(fixture_inputs, "recommendation_payload"),
        derived_memory_views=mapping(runtime_inputs, "derived_memory_views"),
        current_budget_view=mapping(runtime_inputs, "current_budget_view"),
        active_body_plan_view=mapping(runtime_inputs, "active_body_plan_view"),
        open_proposals_view=mapping(runtime_inputs, "open_proposals_view"),
        proposal_candidate_output=mapping(runtime_inputs, "proposal_candidate_output"),
        user_control_models=control_models(fixture_inputs),
        interaction_plan=interaction_plan(fixture_inputs),
    )
    chain_blockers = [f"e2e_chain.{blocker}" for blocker in chain.get("blockers") or []]
    product_artifacts = run_product_lab_product_artifacts(
        turn=turn,
        fixture_inputs=fixture_inputs,
        runtime_inputs=runtime_inputs,
        memory_context_pack=memory_context_pack,
        prior_action_state=prior_action_state,
        prior_control_journal=list(prior_control_journal or []),
        manager_selected_reusable_meal_artifact=manager_artifacts.get(
            "manager_selected_reusable_meal_artifact"
        ),
    )
    product_recommendation = product_artifacts["recommendation"]
    product_recommendation_rescue_bridge = product_artifacts[
        "recommendation_rescue_posture_bridge"
    ]
    product_rescue = product_artifacts["rescue"]
    product_calibration = product_artifacts["calibration"]
    product_no_plan_degraded = product_artifacts["no_plan_degraded"]
    product_planned_event_guidance = product_artifacts["planned_event_guidance"]
    product_planned_event_rescue = product_artifacts["planned_event_rescue"]
    product_exercise_budget = product_artifacts["exercise_budget"]
    product_weekly_insight = product_artifacts["weekly_insight"]
    product_proactive = product_artifacts["proactive"]
    control_state = build_product_lab_control_state(
        session_id=str(turn.get("session_id") or ""),
        turn_id=str(turn.get("turn_id") or ""),
        lab_now_minute=lab_now_minute(turn),
        observed_material_signals=observed_material_signals(turn),
        candidates=chat_packets(chain),
        prior_control_journal=list(prior_control_journal or []),
        control_events=list(control_events or []),
    )
    chat_packet = lab_chat_response_packet(
        chain,
        control_state,
        memory_context_pack=memory_context_pack,
        product_recommendation=product_recommendation,
        product_rescue=product_rescue,
        product_calibration=product_calibration,
        product_no_plan_degraded=product_no_plan_degraded,
        product_planned_event_guidance=product_planned_event_guidance,
        product_planned_event_rescue=product_planned_event_rescue,
        product_exercise_budget=product_exercise_budget,
        product_weekly_insight=product_weekly_insight,
        product_proactive=product_proactive,
    )
    lab_chat_surface = build_advanced_product_lab_chat_surface(session_id=str(turn.get("session_id") or ""), turn_id=str(turn.get("turn_id") or ""), lab_chat_response_packet=chat_packet)
    proactive_dashboard_mirror = build_product_lab_proactive_dashboard_mirror(
        product_proactive=product_proactive,
        lab_chat_surface=lab_chat_surface,
    )
    all_blockers = [
        *chain_blockers,
        *product_lab_product_artifact_blockers(product_artifacts),
        *[
            f"manager_tool_loop.{blocker}"
            for blocker in manager_artifacts["manager_tool_loop_blockers"]
        ],
        *stage_blockers("control_state", control_state),
        *chat_packet_blockers(chat_packet),
        *stage_blockers("lab_chat_surface", lab_chat_surface),
        *stage_blockers("product_lab_proactive_dashboard_mirror", proactive_dashboard_mirror),
    ]
    return {
        **base_turn(turn=turn, lab_mode=lab_mode),
        "status": "blocked" if all_blockers else "pass",
        "full_product_lab_runtime_enabled": True,
        "lab_user_facing_behavior_changed": not bool(all_blockers),
        "product_capabilities_exercised": [] if all_blockers else [
            *CAPABILITIES_EXERCISED,
            *(["calibration"] if product_calibration.get("proposal_presented_to_lab") is True else []),
            *(["no_plan_degraded"] if product_no_plan_degraded.get("status") == "pass" else []),
            *(["planned_event_guidance"] if product_planned_event_guidance.get("status") == "pass" else []),
            *(["exercise_budget"] if product_exercise_budget.get("status") == "pass" else []),
            *(["weekly_insight"] if product_weekly_insight.get("lab_chat_delivery_allowed") is True else []),
        ],
        "lab_memory_context_pack": memory_context_pack,
        "memory_tools_enabled": memory_context_pack.get("memory_tools_enabled") is True,
        "memory_context_injected": memory_context_pack.get("memory_context_injected") is True,
        "lab_manager_context_injected": memory_context_pack.get("lab_manager_context_injected") is True,
        "product_lab_recommendation_artifact": product_recommendation,
        "product_lab_recommendation_rescue_posture_bridge_artifact": (
            product_recommendation_rescue_bridge
        ),
        "product_lab_rescue_artifact": product_rescue,
        "product_lab_calibration_artifact": product_calibration,
        "product_lab_no_plan_degraded_artifact": product_no_plan_degraded,
        "product_lab_planned_event_guidance_artifact": product_planned_event_guidance,
        "product_lab_planned_event_rescue_artifact": product_planned_event_rescue,
        "product_lab_exercise_budget_artifact": product_exercise_budget,
        "product_lab_weekly_insight_artifact": product_weekly_insight,
        "product_lab_proactive_artifact": product_proactive,
        **{
            key: value
            for key, value in manager_artifacts.items()
            if key != "manager_tool_loop_blockers"
        },
        "e2e_chain_artifact": chain,
        "control_state": control_state,
        "lab_chat_response_packet": chat_packet,
        "lab_chat_surface": lab_chat_surface,
        "product_lab_proactive_dashboard_mirror": proactive_dashboard_mirror,
        "blockers": all_blockers,
        **dict(FALSE_FLAGS),
    }


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_advanced_product_lab_turn"]
