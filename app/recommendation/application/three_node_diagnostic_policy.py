from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.three_node_diagnostic_policy"
)


def preflight_blockers(preflight: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if preflight.get("artifact_type") != "recommendation_three_node_live_preflight":
        blockers.append("preflight.unsupported_artifact_type")
    if preflight.get("status") != "pass":
        blockers.append("preflight.status_not_pass")
        blockers.extend(str(item) for item in preflight.get("blockers") or [])
    for flag, value in mapping(preflight.get("activation_flags")).items():
        if value is True:
            blockers.append(f"preflight.activation_flag_true:{flag}")
    return blockers


def node_blockers(node_outputs: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    seen_nodes = {str(row.get("physical_node") or "") for row in node_outputs}
    for required in ("recommendation_planning", "offer_synthesis"):
        if required not in seen_nodes:
            blockers.append(f"{required}.node_not_run")
    for row in node_outputs:
        blockers.extend(str(item) for item in row.get("blockers") or [])
    return blockers


def output_blockers(node: str, output: Mapping[str, Any]) -> list[str]:
    if node == "recommendation_planning":
        return [
            f"recommendation_planning.output.missing:{key}"
            for key in ("recommendation_context_result", "candidate_spec", "non_serve_flags")
            if key not in output
        ]
    return offer_blockers(output)


def offer_blockers(output: Mapping[str, Any]) -> list[str]:
    blockers = [
        f"offer_synthesis.output.missing:{key}"
        for key in ("ranking_result", "recommendation_response_result", "non_serve_flags")
        if key not in output
    ]
    response = mapping(output.get("recommendation_response_result"))
    if response.get("recommendation_served") is True:
        blockers.append("offer_synthesis.output.recommendation_served_not_allowed")
    if response.get("intake_commit_requested") is True:
        blockers.append("offer_synthesis.output.intake_commit_requested_not_allowed")
    if response.get("is_canonical_truth") is True:
        blockers.append("offer_synthesis.output.is_canonical_truth_not_allowed")
    for key, value in mapping(output.get("non_serve_flags")).items():
        if value is True:
            blockers.append(f"offer_synthesis.output.non_serve_flag_true:{key}")
    return blockers


def recommendation_response(output: Mapping[str, Any], guard: Mapping[str, Any]) -> dict[str, Any] | None:
    response = mapping(output.get("recommendation_response_result"))
    candidate_id = str(response.get("candidate_id") or "")
    if candidate_id not in set(str(item) for item in guard.get("allowed_candidate_ids") or []):
        return None
    return {
        "candidate_id": candidate_id,
        "recommendation_served": False,
        "intake_commit_requested": False,
        "is_canonical_truth": False,
    }


def payload_from_preflight(preflight: Mapping[str, Any]) -> dict[str, Any]:
    planning = _node_payload(preflight, "recommendation_planning")
    offer = _node_payload(preflight, "offer_synthesis")
    return {**planning, "candidate_source_fixture": mapping_list(offer.get("allowed_candidate_pool"))}


def offer_output(outputs: list[Mapping[str, Any]]) -> Mapping[str, Any]:
    for row in outputs:
        if row.get("physical_node") == "offer_synthesis":
            return mapping(row.get("output"))
    return {}


def field_by_node(outputs: list[Mapping[str, Any]], field: str) -> dict[str, str]:
    return {str(row.get("physical_node") or ""): str(row.get(field) or "") for row in outputs}


def trace_summary(trace: Mapping[str, Any]) -> dict[str, str]:
    return {"stage": str(trace.get("stage") or ""), "provider": str(trace.get("provider") or "")}


def mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def mapping_list(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _node_payload(preflight: Mapping[str, Any], node: str) -> dict[str, Any]:
    for row in preflight.get("provider_inputs") or []:
        if mapping(row).get("physical_node") == node:
            return mapping(mapping(row).get("payload"))
    return {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "field_by_node",
    "mapping",
    "node_blockers",
    "offer_output",
    "output_blockers",
    "payload_from_preflight",
    "preflight_blockers",
    "recommendation_response",
    "trace_summary",
]
