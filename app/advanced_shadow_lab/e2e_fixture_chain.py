from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.three_node_shadow_contract import (
    run_recommendation_three_node_shadow,
)
from app.recommendation.application.three_node_summary_bridge import (
    build_summary_quality_report_from_three_node_shadow_artifact,
)
from app.rescue.application.shadow_chain_runner import run_rescue_shadow_chain
from app.rescue.application.shadow_summary_context import build_rescue_shadow_summary_context_projection
from app.advanced_shadow_lab.e2e_fixture_chain_policy import (
    FALSE_FLAGS,
    NON_CLAIMS,
    STAGE_ORDER,
    build_interactions,
    named_stage,
    not_run_sink,
    stage_blockers,
    stage_trace,
)
from app.advanced_shadow_lab.chat_ux_packet import build_advanced_shadow_chat_ux_packet
from app.runtime.application.proactive_no_send_nudge_bridge import build_no_send_nudge_candidate_bridge
from app.runtime.application.proactive_no_send_review_sink import build_no_send_review_sink
from app.runtime.application.proactive_recommendation_prompt_bridge import build_recommendation_prompt_no_send_review
from app.runtime.application.proactive_rescue_nudge_bridge import build_rescue_nudge_no_send_review
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.e2e_fixture_chain"
)

def run_advanced_shadow_e2e_fixture_chain(
    *,
    memory_summary_projection: Mapping[str, Any],
    recommendation_payload: Mapping[str, Any],
    derived_memory_views: Mapping[str, Any],
    current_budget_view: Mapping[str, Any],
    active_body_plan_view: Mapping[str, Any],
    open_proposals_view: Mapping[str, Any],
    proposal_candidate_output: Mapping[str, Any],
    user_control_models: Mapping[str, Mapping[str, Any]],
    interaction_plan: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    recommendation = run_recommendation_three_node_shadow(recommendation_payload)
    recommendation_report = build_summary_quality_report_from_three_node_shadow_artifact(
        memory_summary_projection=memory_summary_projection,
        three_node_artifact=recommendation,
        source_payload=recommendation_payload,
    )
    recommendation_review = build_recommendation_prompt_no_send_review(
        recommendation_report
    )
    rescue_projection = build_rescue_shadow_summary_context_projection(
        memory_summary_projection=memory_summary_projection,
        derived_memory_views=derived_memory_views,
    )
    rescue_chain = run_rescue_shadow_chain(
        memory_summary_projection=memory_summary_projection,
        derived_memory_views=derived_memory_views,
        current_budget_view=current_budget_view,
        active_body_plan_view=active_body_plan_view,
        open_proposals_view=open_proposals_view,
        proposal_candidate_output=proposal_candidate_output,
    )
    rescue_review = build_rescue_nudge_no_send_review(rescue_projection)
    bridge = build_no_send_nudge_candidate_bridge(
        recommendation_prompt_review=recommendation_review,
        rescue_nudge_review=rescue_review,
        user_control_models=user_control_models,
    )
    stages = [
        recommendation,
        recommendation_report,
        named_stage("recommendation_prompt_no_send_review", recommendation_review),
        rescue_projection,
        rescue_chain,
        named_stage("rescue_nudge_no_send_review", rescue_review),
        bridge,
    ]
    blockers = stage_blockers(stages)
    sink = (
        not_run_sink()
        if blockers
        else build_no_send_review_sink(
            no_send_candidates=list(bridge.get("candidates") or []),
            interaction_artifacts=build_interactions(
                list(bridge.get("candidates") or []),
                list(interaction_plan or []),
            ),
        )
    )
    all_stages = [*stages, sink]
    all_blockers = [*blockers, *stage_blockers([sink])]
    artifact = {
        "artifact_type": "advanced_shadow_e2e_fixture_chain_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if all_blockers else "pass",
        "owner": "app/advanced_shadow_lab",
        "consumer": "future_advanced_shadow_lab_dogfood_or_live_diagnostic",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "stage_order": list(STAGE_ORDER),
        "stage_trace": stage_trace(all_stages),
        "stage_artifacts": all_stages,
        "terminal_review_sink": sink,
        "blockers": all_blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }
    artifact["chat_ux_packet"] = build_advanced_shadow_chat_ux_packet(
        fixture_chain_artifact=artifact
    )
    return artifact


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_advanced_shadow_e2e_fixture_chain"]
