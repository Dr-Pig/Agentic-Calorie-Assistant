from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_manager_tool_contract import (
    FINAL_FORBIDDEN_TRUE_FIELDS,
    dormant_activation_fields,
)
from app.shared.contracts.final_response_signal_packet import (
    build_final_response_signal_packet,
)


def build_product_lab_manager_final_response_packet(
    final_response: Mapping[str, Any],
    prior_results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    final_response_signal_packet = build_final_response_signal_packet(
        final_response=final_response,
        prior_results=prior_results,
    )
    return {
        "artifact_type": "advanced_product_lab_manager_final_response_packet",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "response_mode": "lab_chat_first_synthesis",
        "copy": str(final_response.get("copy") or ""),
        "source_tool_call_ids": [
            str(item) for item in final_response.get("source_tool_call_ids") or []
        ],
        "final_response_signal_packet": final_response_signal_packet,
        "tool_results_seen_count": len(prior_results),
        "served_to_lab_user": True,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
        "raw_user_text_semantic_inference_performed": False,
        "raw_transcript_included": False,
        **dormant_activation_fields(),
        "served_to_mainline_user": False,
        "blockers": [],
    }


def product_lab_manager_final_packet_blockers(
    final_packet: Mapping[str, Any] | None,
    *,
    known_call_ids: set[str],
    tool_call_count: int,
) -> list[str]:
    if final_packet is None:
        return ["manager.final_response_missing"]
    blockers = [
        f"final_response.forbidden_true_field:{field}"
        for field in sorted(FINAL_FORBIDDEN_TRUE_FIELDS)
        if final_packet.get(field) is True
    ]
    source_ids = [str(item) for item in final_packet.get("source_tool_call_ids") or []]
    if tool_call_count and not source_ids:
        blockers.append("final_response.source_tool_call_ids_missing")
    blockers.extend(
        f"final_response.unknown_source_tool_call_id:{call_id}"
        for call_id in source_ids
        if call_id not in known_call_ids
    )
    return blockers


__all__ = [
    "build_product_lab_manager_final_response_packet",
    "product_lab_manager_final_packet_blockers",
]
