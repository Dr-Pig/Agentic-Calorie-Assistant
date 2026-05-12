from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)


TURN = {
    "session_id": "recommendation-blocker-live-edd",
    "turn_id": "turn-pr10",
    "semantic_intent_fixture": "next_meal_recommendation",
}


def build_recommendation_blocker_case_reports() -> list[dict[str, Any]]:
    return [
        _case_report(
            case_id="positive_memory_boost_allowed",
            memory_entries=[_golden_order("memory-ramen", ["ramen"], 640)],
            blocked_candidate_id="",
        ),
        _case_report(
            case_id="negative_block_wins_over_positive_boost",
            memory_entries=[_golden_order("memory-spicy-ramen", ["spicy", "ramen"], 620)],
            blocked_candidate_id="memory-spicy-ramen",
        ),
    ]


def _case_report(
    *,
    case_id: str,
    memory_entries: list[dict[str, Any]],
    blocked_candidate_id: str,
) -> dict[str, Any]:
    artifact = run_product_lab_recommendation(
        turn=TURN,
        fixture_inputs=_fixture_inputs(),
        memory_context_pack=_memory_pack(memory_entries),
    )
    retrieval = _mapping(artifact.get("retrieval_guard_scoring"))
    primary = _mapping(_mapping(artifact.get("offer_synthesis")).get("selected_primary"))
    filtered = _filtered_by_id(retrieval, blocked_candidate_id)
    return {
        "case_id": case_id,
        "status": "pass" if _passes(artifact, blocked_candidate_id, filtered) else "blocked",
        "primary_candidate_id": str(primary.get("candidate_id") or ""),
        "primary_source_type": str(primary.get("source_type") or ""),
        "allowed_candidate_ids": list(retrieval.get("allowed_candidate_ids") or []),
        "filtered_candidates": list(retrieval.get("filtered_candidates") or []),
        "blocked_candidate_id": blocked_candidate_id,
        "blocked_candidate_reason_codes": list(filtered.get("reason_codes") or []),
        "pool_decision": str(retrieval.get("pool_decision") or ""),
        "lab_recommendation_served": artifact.get("recommendation_served_to_lab") is True,
        "mainline_activation_enabled": artifact.get("mainline_activation_enabled") is True,
        "durable_product_memory_written": artifact.get("durable_product_memory_written") is True,
        "canonical_product_mutation_allowed": artifact.get(
            "canonical_product_mutation_allowed"
        )
        is True,
        "source_artifact_status": str(artifact.get("status") or ""),
    }


def _fixture_inputs() -> dict[str, Any]:
    inputs = build_product_lab_fixture_inputs()
    payload = inputs["recommendation_payload"]
    payload["negative_preference_summary"] = {
        "items": [
            {"pattern": "spicy", "status": "confirmed_negative_preference"},
            {"pattern": "bitter_melon", "status": "confirmed_negative_preference"},
        ]
    }
    payload["open_rescue_context"] = {"accepted_conflict_patterns": []}
    return inputs


def _memory_pack(entries: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [str(entry["record_id"]) for entry in entries]
    return {
        "artifact_type": "advanced_product_lab_memory_context_pack",
        "status": "pass",
        "session_id": TURN["session_id"],
        "turn_id": TURN["turn_id"],
        "entries": entries,
        "selected_record_ids": ids,
        "negative_preference_blockers": [],
        "memory_context_injected": True,
        "lab_memory_context_pack_used": True,
        "mainline_activation_enabled": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": [],
    }


def _golden_order(record_id: str, item_names: list[str], estimated_kcal: int) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "memory_type": "golden_order",
        "summary": "Remembered lab order",
        "store_name": "Lab Ramen",
        "item_names": item_names,
        "estimated_kcal": estimated_kcal,
    }


def _filtered_by_id(
    retrieval: Mapping[str, Any],
    candidate_id: str,
) -> Mapping[str, Any]:
    for item in retrieval.get("filtered_candidates") or []:
        if isinstance(item, Mapping) and item.get("candidate_id") == candidate_id:
            return item
    return {}


def _passes(
    artifact: Mapping[str, Any],
    blocked_candidate_id: str,
    filtered: Mapping[str, Any],
) -> bool:
    if artifact.get("status") != "pass":
        return False
    if artifact.get("mainline_activation_enabled") is True:
        return False
    if not blocked_candidate_id:
        return artifact.get("recommendation_served_to_lab") is True
    return filtered.get("reason_codes") == ["confirmed_negative_preference"]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_recommendation_blocker_case_reports"]
