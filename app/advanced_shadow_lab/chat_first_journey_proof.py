from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.chat_first_journey_rows import (
    SCENARIO_IDS,
    build_chat_first_journey_rows,
    scenario_row_blockers,
)
from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAG_NAMES
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.chat_first_journey_proof"
)
ARTIFACT_TYPE = "advanced_shadow_chat_first_journey_proof_artifact"
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)
CLAIM_FIELDS = (
    *FALSE_FLAG_NAMES,
    "runtime_connected",
    "served_to_user",
    "canonical_mutation_requested",
)


def build_chat_first_journey_proof(
    *,
    context_pack: Mapping[str, Any],
    memory_projection: Mapping[str, Any],
    fixture_chain: Mapping[str, Any],
    terminal_sink: Mapping[str, Any],
    chat_packet: Mapping[str, Any],
) -> dict[str, Any]:
    sources = {
        "shadow_memory_context_pack": context_pack,
        "runtime_lab_memory_consumer_summary_projection": memory_projection,
        "advanced_shadow_e2e_fixture_chain_artifact": fixture_chain,
        "proactive_no_send_review_sink_artifact": terminal_sink,
        "advanced_shadow_chat_ux_packet_artifact": chat_packet,
    }
    rows = build_chat_first_journey_rows(
        context_pack=context_pack,
        memory_projection=memory_projection,
        fixture_chain=fixture_chain,
        terminal_sink=terminal_sink,
        chat_packet=chat_packet,
    )
    blockers = [*_source_blockers(sources), *scenario_row_blockers(rows)]
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "owner": "app/advanced_shadow_lab/chat_first_journey_proof.py",
        "consumer": "advanced_shadow_lab_vertical_proof_artifact.stage_artifacts",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "artifact_classification": "merge_safe",
        "new_report_family_created": False,
        "scenario_ids": list(SCENARIO_IDS),
        "scenario_count": len(rows),
        "scenario_rows": rows if not blockers else [],
        "source_artifact_types": list(sources),
        "lineage_status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "runtime_connected": False,
        "served_to_user": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
        "non_claims": [
            "not_runtime_activation_evidence",
            "not_product_readiness_evidence",
            "not_user_facing_activation",
            "not_canonical_mutation_authority",
            "not_scheduler_delivery",
            "not_durable_control_state",
            "not_live_provider_activation",
        ],
        **dict(FALSE_FLAGS),
    }


def _source_blockers(sources: Mapping[str, Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for expected_type, source in sources.items():
        actual_type = str(source.get("artifact_type") or "")
        status = str(source.get("status") or "")
        if actual_type != expected_type:
            blockers.append(
                f"{expected_type}.unsupported_artifact_type:{actual_type or 'missing'}"
            )
        if status != "pass":
            blockers.append(f"{expected_type}.status_{status or 'missing'}")
        blockers.extend(_claim_blockers(expected_type, source))
    return blockers


def _claim_blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    blockers = [f"{prefix}.{field}" for field in CLAIM_FIELDS if artifact.get(field) is True]
    activation = artifact.get("activation_flags")
    if isinstance(activation, Mapping):
        blockers.extend(
            f"{prefix}.activation_flags.{field}"
            for field in CLAIM_FIELDS
            if activation.get(field) is True
        )
    return blockers


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_chat_first_journey_proof"]
