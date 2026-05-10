from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAG_NAMES
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.llm_node_input")
INPUT_TYPE = "advanced_shadow_llm_node_input_artifact"
SCHEMA_ID = "advanced_shadow_llm_node_diagnostic_v1"
SCENARIO_ID = "memory_guided_recommendation_chat_offer"
CLAIM_SCOPE = "advanced_shadow_llm_node_diagnostic_only"
FALSE_FLAGS = {
    **dict.fromkeys(FALSE_FLAG_NAMES, False),
    "runtime_connected": False,
    "runtime_truth_changed": False,
    "production_selected": False,
}


def build_recommendation_offer_synthesis_node_input(vertical_proof: Mapping[str, Any]) -> dict[str, Any]:
    blockers = _vertical_blockers(vertical_proof)
    journey_proof = _stage(vertical_proof, "advanced_shadow_chat_first_journey_proof_artifact")
    scenario = _scenario(journey_proof, SCENARIO_ID)
    if not scenario:
        blockers.append("chat_first_journey_proof.scenario_missing")
    selected_id = str((scenario.get("lineage_candidate_ids") or [""])[0]) if scenario else ""
    provider_payload = {
        "node_id": "recommendation_offer_synthesis_chat_first_probe",
        "node_role": "offer_synthesis",
        "selected_candidate_id": selected_id,
        "recommendation_source_refs": list(scenario.get("recommendation_source_refs") or []),
        "terminal_packet_refs": list(scenario.get("terminal_packet_refs") or []),
        "constraints": {
            "claim_scope_required": CLAIM_SCOPE,
            "user_facing_output_allowed": False,
            "delivery_or_notification_allowed": False,
            "mutation_or_commit_allowed": False,
        },
    }
    return {
        "artifact_type": INPUT_TYPE,
        "status": "pass" if not blockers else "blocked",
        "node_id": provider_payload["node_id"],
        "node_role": provider_payload["node_role"],
        "structured_output_schema_id": SCHEMA_ID,
        "source_artifact_refs": [
            "advanced_shadow_lab_vertical_proof_artifact",
            "advanced_shadow_chat_first_journey_proof_artifact",
        ],
        "provider_payload": provider_payload if not blockers else {},
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def _vertical_blockers(vertical: Mapping[str, Any]) -> list[str]:
    blockers = []
    if vertical.get("artifact_type") != "advanced_shadow_lab_vertical_proof_artifact":
        blockers.append("vertical_proof.unsupported_artifact_type")
    if vertical.get("status") != "pass":
        blockers.append("vertical_proof.status_not_pass")
    return blockers


def _stage(artifact: Mapping[str, Any], artifact_type: str) -> Mapping[str, Any]:
    return next(
        (
            _mapping(stage)
            for stage in artifact.get("stage_artifacts") or []
            if _mapping(stage).get("artifact_type") == artifact_type
        ),
        {},
    )


def _scenario(journey_proof: Mapping[str, Any], scenario_id: str) -> Mapping[str, Any]:
    return next(
        (
            _mapping(row)
            for row in journey_proof.get("scenario_rows") or []
            if _mapping(row).get("scenario_id") == scenario_id
        ),
        {},
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_recommendation_offer_synthesis_node_input"]
