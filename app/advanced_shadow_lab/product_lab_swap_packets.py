from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_swap_suggestion import (
    swap_suggestion_copy,
)


def with_swap_suggestion_chat_packet(
    packets: list[Mapping[str, Any]],
    product_recommendation: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    ux = _mapping(_mapping(product_recommendation.get("offer_synthesis")).get("ux_packet"))
    swap = _mapping(ux.get("swap_suggestion_packet"))
    if not swap:
        return list(packets)
    return [*packets, _swap_packet(product_recommendation, swap)]


def swap_product_fields(packet: Mapping[str, Any]) -> dict[str, Any]:
    swap = _mapping(packet.get("swap_suggestion_packet"))
    if not swap:
        return {}
    return {
        "product_lab_copy": str(packet.get("product_lab_copy") or ""),
        "swap_suggestion_packet": dict(swap),
        "product_runtime_output_refs": [
            str(item) for item in packet.get("product_runtime_output_refs") or []
        ],
    }


def _swap_packet(
    product_recommendation: Mapping[str, Any],
    swap: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "packet_id": "swap_suggestion:0",
        "workflow_family": "recommendation",
        "trigger_type": "swap_suggestion",
        "packet_kind": "swap_suggestion",
        "product_lab_copy": swap_suggestion_copy(swap),
        "swap_suggestion_packet": dict(swap),
        "memory_action_allowed": True,
        "product_runtime_output_refs": [
            str(product_recommendation.get("artifact_type") or "")
        ],
        "served_to_user": False,
        "delivery_attempted": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["swap_product_fields", "with_swap_suggestion_chat_packet"]
