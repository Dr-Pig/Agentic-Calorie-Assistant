from __future__ import annotations

from typing import Any, Mapping

from app.rescue.application.chat_negotiation_lifecycle_shadow import (
    SUPPORTED_INTENTS,
    build_rescue_chat_negotiation_lifecycle_shadow,
)
from app.rescue.domain.shadow_status import RESCUE_SHADOW_NON_RUNTIME_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.chain_lifecycle_adapter"
)

CHAIN_ARTIFACT = "rescue_shadow_chain_runner_artifact"
OPTION_STAGE = "rescue_option_generation_shadow_packet"
CHAIN_CLAIM_FLAGS = (
    "runtime_effect_allowed",
    "live_llm_invoked",
    "provider_called",
    "proposal_committed",
    "rescue_committed",
    "ledger_entry_created",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "manager_context_injected",
    "proactive_sent",
    "recommendation_served",
)
FALSE_FLAGS = {
    "runtime_effect_allowed": False,
    "user_facing_behavior_changed": False,
    "proposal_committed": False,
    "rescue_committed": False,
    "ledger_entry_created": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "meal_thread_mutated": False,
    "durable_memory_written": False,
    "manager_context_packet_changed": False,
    "manager_context_injected": False,
    "proactive_sent": False,
    "recommendation_served": False,
}


def build_rescue_chain_lifecycle_shadow_packets(
    *,
    rescue_shadow_chain_artifact: Mapping[str, Any],
    interaction_intents: list[str],
) -> dict[str, Any]:
    blockers = [
        *_chain_blockers(rescue_shadow_chain_artifact),
        *_intent_blockers(interaction_intents),
    ]
    option_stage = _option_stage(rescue_shadow_chain_artifact)
    lifecycle_packets = (
        []
        if blockers
        else [
            build_rescue_chat_negotiation_lifecycle_shadow(
                option_generation_shadow_packet=option_stage,
                interaction_intent=intent,
            )
            for intent in interaction_intents
        ]
    )
    blockers.extend(_lifecycle_blockers(lifecycle_packets))
    return _artifact(
        source=rescue_shadow_chain_artifact,
        lifecycle_packets=[] if blockers else lifecycle_packets,
        blockers=blockers,
    )


def _artifact(
    *,
    source: Mapping[str, Any],
    lifecycle_packets: list[dict[str, Any]],
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_chain_lifecycle_adapter_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/rescue",
        "consumer": "future_rescue_proactive_shadow_integration",
        "retirement_trigger": "approved_rescue_runtime_activation_plan",
        "new_report_family_created": False,
        "source_rescue_chain_artifact_type": source.get("artifact_type"),
        "source_stage_used": OPTION_STAGE,
        "interaction_intent_source": "bounded_lab_fixture_not_raw_text",
        "semantic_interaction_owner": "future_llm_or_human_confirmation",
        "stage_trace": _stage_trace(source, lifecycle_packets),
        "lifecycle_packets": lifecycle_packets,
        "lifecycle_summary": _lifecycle_summary(lifecycle_packets),
        "blockers": blockers,
        "non_claims": [
            "not_user_facing_response",
            "not_rescue_commit",
            "not_budget_or_ledger_mutation",
            "not_scheduler_or_notification_delivery",
            "not_raw_text_semantic_router",
        ],
        **dict(FALSE_FLAGS),
        **dict(RESCUE_SHADOW_NON_RUNTIME_FLAGS),
    }


def _chain_blockers(source: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if source.get("artifact_type") != CHAIN_ARTIFACT:
        blockers.append("rescue_shadow_chain_runner_artifact.unsupported_artifact_type")
    if source.get("status") != "pass":
        blockers.append("rescue_shadow_chain_runner_artifact.status_not_pass")
    if not _option_stage(source):
        blockers.append("rescue_shadow_chain_runner_artifact.option_stage_missing")
    for flag in CHAIN_CLAIM_FLAGS:
        if source.get(flag) is True:
            blockers.append(f"rescue_shadow_chain_runner_artifact.{flag}")
    return blockers


def _intent_blockers(interaction_intents: list[str]) -> list[str]:
    return [
        f"interaction_intent.unsupported:{intent}"
        for intent in interaction_intents
        if intent not in SUPPORTED_INTENTS
    ]


def _lifecycle_blockers(packets: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"rescue_chat_negotiation_lifecycle_shadow_packet.status_{packet.get('status')}"
        for packet in packets
        if packet.get("status") != "pass"
    ]


def _option_stage(source: Mapping[str, Any]) -> Mapping[str, Any]:
    for stage in source.get("stage_artifacts") or []:
        if isinstance(stage, Mapping) and stage.get("artifact_type") == OPTION_STAGE:
            return stage
    return {}


def _stage_trace(
    source: Mapping[str, Any],
    packets: list[Mapping[str, Any]],
) -> list[dict[str, str]]:
    return [
        {
            "stage": str(source.get("artifact_type") or ""),
            "status": str(source.get("status") or ""),
        },
        *[
            {
                "stage": str(packet.get("artifact_type") or ""),
                "status": str(packet.get("status") or ""),
                "interaction_intent": str(packet.get("interaction_intent") or ""),
            }
            for packet in packets
        ],
    ]


def _lifecycle_summary(packets: list[Mapping[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for packet in packets:
        state = str(packet.get("lifecycle_state") or "")
        if state:
            summary[state] = summary.get(state, 0) + 1
    return summary


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_chain_lifecycle_shadow_packets",
]
