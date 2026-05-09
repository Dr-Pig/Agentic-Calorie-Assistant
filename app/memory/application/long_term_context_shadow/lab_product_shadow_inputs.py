from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.lab_active_view import (
    reviewed_lab_context_view,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.long_term_context_shadow.lab_product_shadow_inputs"
)


def reviewed_consumer_shadow_input(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
    consumer_id: str,
) -> dict[str, Any]:
    view = reviewed_lab_context_view(fixture, candidates)
    consumer_view = view["consumer_views"][consumer_id]
    return {
        "reviewed_lab_view_status": view["status"],
        "reviewed_lab_context_source_artifact": view["source_artifact_type"],
        "reviewed_lab_record_ids": consumer_view["active_memory_record_ids"],
        "reviewed_lab_record_summaries": consumer_view["active_records"],
        "runtime_effect_allowed": False,
        "manager_context_injection_allowed": False,
    }


def reviewed_lab_memory_triggers(reviewed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "trigger_id": f"reviewed-trigger-{record['source_candidate_id']}",
            "source_memory_record_id": record["memory_record_id"],
            "source_candidate_id": record["source_candidate_id"],
            "reason": record["memory_text"],
            "scheduler_activated": False,
            "proactive_sent": False,
            "runtime_effect_allowed": False,
        }
        for record in reviewed["reviewed_lab_record_summaries"]
    ]


def reviewed_lab_rescue_packets(reviewed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "packet_id": f"reviewed-rescue-{record['source_candidate_id']}",
            "source_memory_record_id": record["memory_record_id"],
            "source_candidate_id": record["source_candidate_id"],
            "reason": record["memory_text"],
            "proposal_commit_allowed": False,
            "budget_mutation_requested": False,
            "runtime_effect_allowed": False,
        }
        for record in reviewed["reviewed_lab_record_summaries"]
    ]


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "reviewed_consumer_shadow_input",
    "reviewed_lab_memory_triggers",
    "reviewed_lab_rescue_packets",
]
