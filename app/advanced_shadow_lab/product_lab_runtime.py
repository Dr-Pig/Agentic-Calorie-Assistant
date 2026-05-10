from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain import (
    run_advanced_shadow_e2e_fixture_chain,
)
from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_chat_surface import (
    build_advanced_product_lab_chat_surface,
)
from app.advanced_shadow_lab.product_lab_control_state import (
    build_product_lab_control_state,
)
from app.advanced_shadow_lab.product_lab_memory import (
    empty_product_lab_memory_context_pack,
    fixture_inputs_with_lab_memory_context,
)
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue
from app.advanced_shadow_lab.product_lab_turn_packets import (
    chat_packet_blockers,
    chat_packets,
    lab_chat_response_packet,
)
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


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_runtime"
)


def run_advanced_product_lab_turn(
    *,
    lab_mode: str,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    lab_memory_context_pack: Mapping[str, Any] | None = None,
    prior_control_journal: list[Mapping[str, Any]] | None = None,
    control_events: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    blockers = turn_blockers(lab_mode=lab_mode, turn=turn)
    if blockers:
        return blocked_turn(turn=turn, lab_mode=lab_mode, blockers=blockers)

    memory_context_pack = dict(
        lab_memory_context_pack
        or empty_product_lab_memory_context_pack(
            session_id=str(turn.get("session_id") or ""),
            turn_id=str(turn.get("turn_id") or ""),
        )
    )
    runtime_inputs = fixture_inputs_with_lab_memory_context(
        fixture_inputs,
        memory_context_pack,
    )
    chain = run_advanced_shadow_e2e_fixture_chain(
        memory_summary_projection=mapping(runtime_inputs, "memory_summary_projection"),
        recommendation_payload=mapping(runtime_inputs, "recommendation_payload"),
        derived_memory_views=mapping(runtime_inputs, "derived_memory_views"),
        current_budget_view=mapping(runtime_inputs, "current_budget_view"),
        active_body_plan_view=mapping(runtime_inputs, "active_body_plan_view"),
        open_proposals_view=mapping(runtime_inputs, "open_proposals_view"),
        proposal_candidate_output=mapping(runtime_inputs, "proposal_candidate_output"),
        user_control_models=control_models(fixture_inputs),
        interaction_plan=interaction_plan(fixture_inputs),
    )
    chain_blockers = [f"e2e_chain.{blocker}" for blocker in chain.get("blockers") or []]
    product_recommendation = run_product_lab_recommendation(
        turn=turn,
        fixture_inputs=runtime_inputs,
        memory_context_pack=memory_context_pack,
    )
    product_rescue = run_product_lab_rescue(fixture_inputs=runtime_inputs)
    product_proactive = run_product_lab_proactive(
        turn=turn,
        fixture_inputs=runtime_inputs,
        memory_context_pack=memory_context_pack,
        recommendation_artifact=product_recommendation,
        rescue_artifact=product_rescue,
    )
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
        product_proactive=product_proactive,
    )
    lab_chat_surface = build_advanced_product_lab_chat_surface(
        session_id=str(turn.get("session_id") or ""),
        turn_id=str(turn.get("turn_id") or ""),
        lab_chat_response_packet=chat_packet,
    )
    all_blockers = [
        *chain_blockers,
        *[
            f"product_recommendation.{blocker}"
            for blocker in product_recommendation.get("blockers") or []
        ],
        *[
            f"product_rescue.{blocker}"
            for blocker in product_rescue.get("blockers") or []
        ],
        *[
            f"product_proactive.{blocker}"
            for blocker in product_proactive.get("blockers") or []
        ],
        *stage_blockers("control_state", control_state),
        *chat_packet_blockers(chat_packet),
        *stage_blockers("lab_chat_surface", lab_chat_surface),
    ]
    return {
        **base_turn(turn=turn, lab_mode=lab_mode),
        "status": "blocked" if all_blockers else "pass",
        "full_product_lab_runtime_enabled": True,
        "lab_user_facing_behavior_changed": not bool(all_blockers),
        "product_capabilities_exercised": []
        if all_blockers
        else list(CAPABILITIES_EXERCISED),
        "lab_memory_context_pack": memory_context_pack,
        "memory_tools_enabled": memory_context_pack.get("memory_tools_enabled") is True,
        "memory_context_injected": memory_context_pack.get("memory_context_injected") is True,
        "lab_manager_context_injected": memory_context_pack.get("lab_manager_context_injected") is True,
        "product_lab_recommendation_artifact": product_recommendation,
        "product_lab_rescue_artifact": product_rescue,
        "product_lab_proactive_artifact": product_proactive,
        "e2e_chain_artifact": chain,
        "control_state": control_state,
        "lab_chat_response_packet": chat_packet,
        "lab_chat_surface": lab_chat_surface,
        "blockers": all_blockers,
        **dict(FALSE_FLAGS),
    }


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_advanced_product_lab_turn"]
