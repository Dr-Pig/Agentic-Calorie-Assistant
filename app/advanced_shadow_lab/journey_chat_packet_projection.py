from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAG_NAMES
from app.advanced_shadow_lab.journey_chat_packet_summary import (
    summarize_journey_chat_packets,
)
from app.advanced_shadow_lab.ux_acceptance_coverage import REQUIRED_UX_JOURNEY_IDS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.journey_chat_packet_projection"
)
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)


def build_journey_chat_packets(
    journey_terminal_evidence: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _rows(journey_terminal_evidence)
    packets = [_packet(row) for row in _ordered_rows(rows) if _row_status(row) == "pass"]
    return packets, summarize_journey_chat_packets(
        journey_chat_packets=packets,
        journey_terminal_evidence=rows,
    )


def _packet(row: Mapping[str, Any]) -> dict[str, Any]:
    journey_id = str(row.get("journey_id") or "")
    output = _mapping(row.get("ux_terminal_output"))
    return {
        "packet_id": f"journey:{journey_id}:{output.get('output_kind') or 'unknown'}",
        "journey_id": journey_id,
        "journey_name": str(row.get("journey_name") or ""),
        "surface": "chat",
        "chat_first": True,
        "packet_kind": "lab_only_journey_terminal_projection",
        "workflow_family": str(output.get("workflow_family") or ""),
        "output_kind": str(output.get("output_kind") or ""),
        "control_contract": dict(_mapping(output.get("control_contract"))),
        "source_terminal_evidence_id": journey_id,
        "source_artifact_refs": list(row.get("terminal_artifact_refs") or []),
        "product_contract_refs": list(row.get("product_contract_refs") or []),
        "required_trace_fields": list(row.get("required_trace_fields") or []),
        "semantic_truth_owner": "journey_terminal_evidence",
        "semantic_decision_inferred_by_runner": False,
        "served_to_user": False,
        "delivery_attempted": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
        **dict(FALSE_FLAGS),
    }


def _ordered_rows(rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    by_id = {str(item.get("journey_id") or ""): item for item in rows}
    return [_mapping(by_id.get(journey_id)) for journey_id in REQUIRED_UX_JOURNEY_IDS]


def _row_status(row: Mapping[str, Any]) -> str:
    return str(row.get("status") or "blocked")


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_journey_chat_packets"]
