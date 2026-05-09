from __future__ import annotations

from typing import Any, Mapping

from app.rescue.application.no_commit_viability import (
    build_rescue_no_commit_viability_shadow_packet,
)
from app.rescue.application.option_generation_shadow import (
    build_rescue_option_generation_shadow_packet,
)
from app.rescue.application.proposal_shaping_fake_runner import (
    run_rescue_proposal_shaping_fake,
)
from app.rescue.application.proposal_shaping_input_shadow import (
    build_rescue_proposal_shaping_input_shadow_packet,
)
from app.rescue.application.shadow_summary_context import (
    build_rescue_shadow_summary_context_projection,
)
from app.rescue.domain.shadow_status import RESCUE_SHADOW_NON_RUNTIME_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.shadow_chain_runner"
)
STAGE_ORDER = [
    "rescue_shadow_summary_context_projection",
    "rescue_no_commit_viability_shadow_packet",
    "rescue_option_generation_shadow_packet",
    "rescue_proposal_shaping_input_shadow_packet",
    "rescue_proposal_shaping_fake_runner_artifact",
]
FORBIDDEN_TRUE_FLAGS = (
    "runtime_effect_allowed",
    "live_llm_invoked",
    "provider_called",
    "rescue_committed",
    "proposal_committed",
    "ledger_entry_created",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "manager_context_injected",
    "proactive_sent",
    "recommendation_served",
)


def run_rescue_shadow_chain(
    *,
    memory_summary_projection: Mapping[str, Any],
    derived_memory_views: Mapping[str, Any],
    current_budget_view: Mapping[str, Any],
    active_body_plan_view: Mapping[str, Any],
    open_proposals_view: Mapping[str, Any],
    proposal_candidate_output: Mapping[str, Any],
    budget_context: Mapping[str, Any] | None = None,
    body_plan_context: Mapping[str, Any] | None = None,
    rescue_history_context: Mapping[str, Any] | None = None,
    suppression_context: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    context = build_rescue_shadow_summary_context_projection(
        memory_summary_projection=memory_summary_projection,
        derived_memory_views=derived_memory_views,
    )
    stages.append(context)
    if _stage_blockers(stages):
        return _artifact(stages)

    viability = build_rescue_no_commit_viability_shadow_packet(
        rescue_context_projection=context,
        current_budget_view=current_budget_view,
        active_body_plan_view=active_body_plan_view,
        open_proposals_view=open_proposals_view,
    )
    stages.append(viability)
    if _stage_blockers(stages):
        return _artifact(stages)

    option = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=viability,
    )
    stages.append(option)
    if _stage_blockers(stages):
        return _artifact(stages)

    shaping_input = build_rescue_proposal_shaping_input_shadow_packet(
        option_generation_shadow_packet=option,
        budget_context=budget_context,
        body_plan_context=body_plan_context,
        rescue_history_context=rescue_history_context,
        suppression_context=suppression_context,
    )
    stages.append(shaping_input)
    if _stage_blockers(stages):
        return _artifact(stages)

    fake_runner = run_rescue_proposal_shaping_fake(
        proposal_shaping_input_shadow_packet=shaping_input,
        candidate_output=proposal_candidate_output,
    )
    stages.append(fake_runner)
    return _artifact(stages)


def _artifact(stages: list[Mapping[str, Any]]) -> dict[str, Any]:
    blockers = _stage_blockers(stages)
    return {
        "artifact_type": "rescue_shadow_chain_runner_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "runner_role": "chain_integrity_only",
        "owner": "app/rescue",
        "consumer": "future_rescue_proactive_shadow_integration",
        "retirement_trigger": "approved_rescue_runtime_activation_plan",
        "stage_order": list(STAGE_ORDER),
        "stage_trace": _stage_trace(stages),
        "final_validation_status": _final_validation_status(stages, blockers),
        "blockers": blockers,
        "proposal_card": None,
        "primary_actions": [],
        "runtime_effect_allowed": False,
        "live_llm_invoked": False,
        "provider_called": False,
        "recommendation_posture_updated": False,
        "ledger_entry_created": False,
        **dict(RESCUE_SHADOW_NON_RUNTIME_FLAGS),
    }


def _stage_blockers(stages: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for stage in stages:
        stage_name = str(stage.get("artifact_type") or "unknown_stage")
        status = str(stage.get("status") or "blocked")
        if status != "pass":
            blockers.append(f"{stage_name}.status_{status}")
            blockers.extend(
                f"{stage_name}.{blocker}"
                for blocker in list(stage.get("blockers") or [])
            )
        for flag in FORBIDDEN_TRUE_FLAGS:
            if stage.get(flag) is True:
                blockers.append(f"{stage_name}.{flag}")
    return blockers


def _stage_trace(stages: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "stage": str(stage.get("artifact_type") or "unknown_stage"),
            "status": str(stage.get("status") or "blocked"),
        }
        for stage in stages
    ]


def _final_validation_status(
    stages: list[Mapping[str, Any]],
    blockers: list[str],
) -> str:
    if len(stages) < len(STAGE_ORDER):
        return "not_run"
    if blockers:
        return str(stages[-1].get("status") or "blocked")
    return "pass"


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "run_rescue_shadow_chain",
]
