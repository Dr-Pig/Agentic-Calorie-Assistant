from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence

from .food_evidence_packet_builder import is_compact_food_evidence_packet


def build_tool_evidence_result(
    *,
    tool_name: str,
    tool_call_id: str,
    evidence_packets: Sequence[dict[str, Any]],
    index_adapter: dict[str, Any] | None = None,
    trace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packets = [deepcopy(packet) for packet in evidence_packets]
    _raise_if_non_compact(packets)

    return {
        "result_type": "tool_evidence_result_v1",
        "tool_name": tool_name,
        "tool_call_id": tool_call_id,
        "result_boundary": "read_only_evidence_packet_result",
        "runtime_mutation_allowed": False,
        "runtime_truth_changed": False,
        "manager_context_changed": False,
        "read_model_only": True,
        "source_implementation_visible": False,
        "evidence_packets": packets,
        "trace": {
            **(dict(trace_context or {})),
            "packet_count": len(packets),
            "compact_packet_pass_count": len(packets),
            "raw_source_rows_included": False,
            "candidate_only_records_included": False,
            "full_fooddb_included": False,
            "source_implementation_manager_visible": False,
        },
        "manager_may_use_for": [
            "grounded_food_evidence",
            "followup_or_uncertainty_decision",
            "disambiguation",
        ],
        "manager_must_not_use_for": [
            "runtime_mutation",
            "creating_fooddb_truth",
            "inventing_source",
            "inferring_source_implementation",
        ],
    }


def _raise_if_non_compact(packets: Sequence[dict[str, Any]]) -> None:
    for index, packet in enumerate(packets):
        if not _has_required_packet_shape(packet):
            packet_id = str(packet.get("packet_id") or packet.get("case_id") or index)
            raise ValueError(f"malformed_evidence_packet:{packet_id}")
        if not is_compact_food_evidence_packet(packet):
            packet_id = str(packet.get("packet_id") or packet.get("case_id") or index)
            raise ValueError(f"non_compact_evidence_packet:{packet_id}")


def _has_required_packet_shape(packet: dict[str, Any]) -> bool:
    packet_type = str(packet.get("packet_type") or "").strip()
    packet_id = str(packet.get("packet_id") or packet.get("case_id") or "").strip()
    evidence_items = packet.get("evidence_items")
    required_fields = (
        "raw_user_input",
        "retrieval_scope",
        "retrieval_boundary",
        "runtime_mutation_allowed",
        "truth_selection_forbidden",
        "raw_source_rows_included",
        "candidate_only_records_included",
        "full_fooddb_included",
        "manager_may_use_for",
        "manager_must_not_use_for",
    )
    has_required_fields = all(key in packet for key in required_fields)
    return (
        packet_type in {"food_evidence_recall_packet_v1", "fooddb_manager_evidence_packet_v1"}
        and bool(packet_id)
        and isinstance(evidence_items, list)
        and has_required_fields
        and packet.get("runtime_mutation_allowed") is False
        and packet.get("truth_selection_forbidden") is True
    )


__all__ = ["build_tool_evidence_result"]
