from __future__ import annotations

from typing import Any, Mapping


def with_exercise_budget_chat_packet(
    packets: list[Mapping[str, Any]],
    exercise_budget: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if exercise_budget.get("status") != "pass":
        return list(packets)
    return [*packets, _exercise_packet(exercise_budget)]


def exercise_product_fields(packet: Mapping[str, Any]) -> dict[str, Any]:
    exercise = _mapping(packet.get("exercise_budget_packet"))
    if not exercise:
        return {}
    return {
        "product_lab_copy": str(packet.get("product_lab_copy") or ""),
        "exercise_budget_packet": dict(exercise),
        "product_runtime_output_refs": [
            str(item) for item in packet.get("product_runtime_output_refs") or []
        ],
    }


def _exercise_packet(exercise_budget: Mapping[str, Any]) -> dict[str, Any]:
    reply = _mapping(exercise_budget.get("chat_reply_packet"))
    return {
        "packet_id": "exercise_budget:0",
        "workflow_family": "exercise",
        "trigger_type": "exercise_budget_bonus",
        "packet_kind": "exercise_budget",
        "product_lab_copy": str(reply.get("copy") or ""),
        "exercise_budget_packet": {
            "lab_exercise_event": dict(
                _mapping(exercise_budget.get("lab_exercise_event"))
            ),
            "lab_ledger_entry": dict(_mapping(exercise_budget.get("lab_ledger_entry"))),
            "today_budget_projection": dict(
                _mapping(exercise_budget.get("lab_today_budget_projection"))
            ),
            "chat_reply_packet": dict(reply),
            "canonical_commit_requested": False,
        },
        "product_runtime_output_refs": [str(exercise_budget.get("artifact_type") or "")],
        "served_to_user": False,
        "delivery_attempted": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["exercise_product_fields", "with_exercise_budget_chat_packet"]
