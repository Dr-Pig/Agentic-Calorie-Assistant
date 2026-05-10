from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.runtime_lab_consumer_summary_pack import (
    build_runtime_lab_memory_consumer_summary_pack,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_reviewed_memory_consumer_bridge"
)
CLAIM_FLAGS = (
    "runtime_effect_allowed",
    "durable_product_memory_written",
    "user_facing_behavior_changed",
    "canonical_mutation_changed",
    "manager_context_packet_changed",
    "manager_context_injected",
)


def build_consumer_summary_projection_from_shadow_memory_context_pack(
    context_pack: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = _context_pack_blockers(context_pack)
    contract = {
        "artifact_type": "runtime_lab_memory_candidate_review_contract",
        "status": "blocked" if blockers else "pass",
        "reviewed_shadow_candidates": []
        if blockers
        else [_candidate(entry) for entry in _entries(context_pack)],
        "blockers": blockers,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }
    projection = build_runtime_lab_memory_consumer_summary_pack(contract)
    projection["source_context_pack_artifact_type"] = context_pack.get("artifact_type")
    projection["source_context_pack_used"] = not blockers
    projection["source_store_type"] = context_pack.get("source_store_type")
    projection["reviewed_memory_store_used"] = bool(
        context_pack.get("reviewed_memory_store_used")
    )
    projection["omission_trace"] = [
        *projection.get("omission_trace", []),
        *_context_omissions(context_pack),
    ]
    projection["runtime_effect_allowed"] = False
    projection["durable_product_memory_written"] = False
    projection["manager_context_packet_changed"] = False
    projection["recommendation_served"] = False
    projection["rescue_proposal_committed"] = False
    projection["proactive_sent"] = False
    return projection


def _context_pack_blockers(context_pack: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if context_pack.get("artifact_type") != "shadow_memory_context_pack":
        blockers.append("shadow_memory_context_pack.unsupported_artifact_type")
    if context_pack.get("status") != "pass":
        blockers.append("shadow_memory_context_pack.status_not_pass")
    if context_pack.get("reviewed_memory_store_used") is not True:
        blockers.append("shadow_memory_context_pack.reviewed_store_not_used")
    for flag in CLAIM_FLAGS:
        if context_pack.get(flag) is True:
            blockers.append(f"shadow_memory_context_pack.{flag}")
    return blockers


def _candidate(entry: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = str(entry.get("candidate_id") or "unknown_candidate")
    return {
        "candidate_id": candidate_id,
        "candidate_type": str(entry.get("candidate_type") or "memory"),
        "source_object_refs": list(entry.get("source_object_refs") or []),
        "review_status": _review_status(entry),
        "payload": {
            "summary": _summary(entry),
            "store_name": "",
            "item_names": [],
        },
        "promotion_allowed_now": False,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def _review_status(entry: Mapping[str, Any]) -> str:
    if entry.get("review_status") == "accepted":
        return "accepted_shadow"
    return str(entry.get("review_status") or "pending")


def _summary(entry: Mapping[str, Any]) -> str:
    summary = str(entry.get("summary") or "")
    prefix = f"{entry.get('candidate_type')}: "
    return summary.removeprefix(prefix)


def _entries(context_pack: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [entry for entry in context_pack.get("entries", []) if isinstance(entry, Mapping)]


def _context_omissions(context_pack: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "candidate_id": str(item.get("candidate_id") or "unknown_candidate"),
            "reason": str(item.get("reason") or "omitted_from_context_pack"),
        }
        for item in context_pack.get("omission_trace", [])
        if isinstance(item, Mapping)
    ]


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_consumer_summary_projection_from_shadow_memory_context_pack",
]
