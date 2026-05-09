from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.five_node_shadow_runner import run_recommendation_five_node_lab_runner
from app.recommendation.application.five_node_summary_bridge import build_summary_quality_report_from_five_node_lab_artifact
from app.rescue.application.shadow_chain_runner import run_rescue_shadow_chain
from app.rescue.application.shadow_summary_context import build_rescue_shadow_summary_context_projection
from app.runtime.application.proactive_no_send_interaction_model import apply_no_send_candidate_interaction
from app.runtime.application.proactive_no_send_nudge_bridge import build_no_send_nudge_candidate_bridge
from app.runtime.application.proactive_no_send_review_sink import build_no_send_review_sink
from app.runtime.application.proactive_recommendation_prompt_bridge import build_recommendation_prompt_no_send_review
from app.runtime.application.proactive_rescue_nudge_bridge import build_rescue_nudge_no_send_review
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.e2e_fixture_chain"
)

STAGE_ORDER = ["recommendation_five_node_lab_runner_artifact", "recommendation_shadow_summary_consumer_quality_report", "recommendation_prompt_no_send_review", "rescue_shadow_summary_context_projection", "rescue_shadow_chain_runner_artifact", "rescue_nudge_no_send_review", "proactive_no_send_nudge_candidate_bridge", "proactive_no_send_review_sink_artifact"]
FALSE_FLAG_NAMES = (
    "runtime_effect_allowed", "mainline_runtime_connected", "mainline_route_or_api_mount_allowed",
    "production_scheduler_delivery_allowed", "production_db_migration_allowed",
    "canonical_product_mutation_allowed", "delivery_attempted", "proactive_sent",
    "scheduler_enabled", "live_delivery_allowed", "push_or_line_delivery_connected",
    "manager_context_packet_changed", "manager_context_injected", "recommendation_served",
    "rescue_committed", "proposal_committed", "durable_product_memory_written",
    "durable_memory_written", "mutation_changed", "user_facing_behavior_changed",
    "live_provider_used", "product_readiness_claimed",
)
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)
CLAIM_FLAGS = FALSE_FLAG_NAMES + (
    "day_budget_mutated", "body_plan_mutated", "meal_thread_mutated", "intake_committed",
    "ledger_entry_created",
)
NON_CLAIMS = [
    "not_runtime_activation_evidence", "not_product_readiness_evidence", "not_user_facing_activation",
    "not_canonical_mutation_authority", "not_scheduler_delivery", "not_durable_outbox",
]
ACCEPTED_STAGE_STATUSES = {"recommendation_prompt_no_send_review": {"candidate_for_human_review"}, "rescue_nudge_no_send_review": {"context_available"}}


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
    five_node = run_recommendation_five_node_lab_runner(recommendation_payload)
    recommendation_report = build_summary_quality_report_from_five_node_lab_artifact(
        memory_summary_projection=memory_summary_projection,
        five_node_artifact=five_node,
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
        five_node,
        recommendation_report,
        _named_stage("recommendation_prompt_no_send_review", recommendation_review),
        rescue_projection,
        rescue_chain,
        _named_stage("rescue_nudge_no_send_review", rescue_review),
        bridge,
    ]
    blockers = _stage_blockers(stages)
    sink = (
        _not_run_sink()
        if blockers
        else build_no_send_review_sink(
            no_send_candidates=list(bridge.get("candidates") or []),
            interaction_artifacts=_interactions(
                list(bridge.get("candidates") or []),
                list(interaction_plan or []),
            ),
        )
    )
    all_stages = [*stages, sink]
    all_blockers = [*blockers, *_stage_blockers([sink])]
    return {
        "artifact_type": "advanced_shadow_e2e_fixture_chain_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if all_blockers else "pass",
        "owner": "app/advanced_shadow_lab",
        "consumer": "future_advanced_shadow_lab_dogfood_or_live_diagnostic",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "stage_order": list(STAGE_ORDER),
        "stage_trace": _stage_trace(all_stages),
        "stage_artifacts": all_stages,
        "terminal_review_sink": sink,
        "blockers": all_blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _interactions(
    candidates: list[Mapping[str, Any]],
    interaction_plan: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        apply_no_send_candidate_interaction(
            no_send_candidate=candidate,
            action=str(step.get("action") or "dismiss"),  # type: ignore[arg-type]
            dismiss_reason=_string_or_none(step.get("dismiss_reason")),
            snooze_minutes=step.get("snooze_minutes")
            if isinstance(step.get("snooze_minutes"), int)
            else None,
            undo_token=_string_or_none(step.get("undo_token")),
        )
        for candidate, step in zip(candidates, interaction_plan)
    ]


def _stage_blockers(stages: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for stage in stages:
        stage_type = str(stage.get("artifact_type") or "unknown_stage")
        status = str(stage.get("status") or "blocked")
        if not _stage_status_ok(stage_type, status):
            blockers.append(f"{stage_type}.status_{status}")
            blockers.extend(
                f"{stage_type}.{blocker}"
                for blocker in list(stage.get("blockers") or [])
            )
        blockers.extend(_claim_blockers(stage_type, stage))
    return blockers


def _stage_status_ok(stage_type: str, status: str) -> bool:
    return status == "pass" or status in ACCEPTED_STAGE_STATUSES.get(stage_type, set())


def _claim_blockers(stage_type: str, stage: Mapping[str, Any]) -> list[str]:
    blockers = [f"{stage_type}.{flag}" for flag in CLAIM_FLAGS if stage.get(flag) is True]
    activation = stage.get("activation_flags")
    if isinstance(activation, Mapping):
        blockers.extend(
            f"{stage_type}.activation_flags.{flag}"
            for flag in CLAIM_FLAGS
            if activation.get(flag) is True
        )
    return blockers


def _stage_trace(stages: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "artifact_type": str(stage.get("artifact_type") or "unknown_stage"),
            "status": str(stage.get("status") or "blocked"),
        }
        for stage in stages
    ]


def _named_stage(artifact_type: str, stage: Mapping[str, Any]) -> dict[str, Any]:
    return {"artifact_type": artifact_type, **dict(stage)}


def _not_run_sink() -> dict[str, Any]:
    return {"artifact_type": "proactive_no_send_review_sink_artifact", "status": "not_run",
            "record_count": 0, "records": [], "blockers": ["upstream_stage_blocked"],
            **dict(FALSE_FLAGS)}


def _string_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_advanced_shadow_e2e_fixture_chain"]
