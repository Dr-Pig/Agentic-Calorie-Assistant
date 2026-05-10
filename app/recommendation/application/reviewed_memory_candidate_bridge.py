from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.runtime_lab_downstream_boundary import (
    consumer_summary_projection_blockers,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.reviewed_memory_candidate_bridge"
)


def build_reviewed_memory_recommendation_three_node_payload(
    memory_summary_projection: Mapping[str, Any],
    *,
    remaining_budget_kcal: int,
) -> dict[str, Any]:
    blockers = consumer_summary_projection_blockers(memory_summary_projection)
    candidates = (
        []
        if blockers
        else _candidate_source(memory_summary_projection, remaining_budget_kcal)
    )
    selected_id = str(candidates[0]["candidate_id"]) if candidates else ""
    return {
        "source_memory_artifact_type": memory_summary_projection.get("artifact_type"),
        "reviewed_memory_projection_used": not blockers,
        "bridge_blockers": blockers,
        "current_budget_view": {"remaining_kcal": remaining_budget_kcal},
        "negative_preference_summary": _negative_summary(memory_summary_projection),
        "open_rescue_context": {"accepted_conflict_patterns": []},
        "candidate_source_fixture": candidates,
        "manager_recommendation_decision_fixture": {
            "decision_mode": "llm_fixture",
            "top_candidate_id": selected_id,
            "decision_summary": "lab fixture selects reviewed-memory golden order",
            "candidate_spec": {
                "source": "reviewed_memory_projection",
                "constraints": ["budget", "negative_preference", "reviewed_memory"],
            },
        },
        "shadow_offer_packet_fixture": {
            "decision_mode": "llm_fixture",
            "candidate_id": selected_id,
            "recommendation_served": False,
            "is_canonical_truth": False,
            "intake_commit_requested": False,
        },
        "activation_flags": _false_flags(),
    }


def build_reviewed_memory_recommendation_five_node_payload(
    memory_summary_projection: Mapping[str, Any],
    *,
    remaining_budget_kcal: int,
) -> dict[str, Any]:
    payload = build_reviewed_memory_recommendation_three_node_payload(
        memory_summary_projection,
        remaining_budget_kcal=remaining_budget_kcal,
    )
    selected_id = str(
        _mapping(payload.get("manager_recommendation_decision_fixture")).get(
            "top_candidate_id", ""
        )
    )
    payload.update(
        {
            "legacy_five_node_compatibility_payload": True,
            "canonical_recommendation_graph": "three_node",
            "recommendation_context_fixture": {
                "decision_mode": "llm_fixture",
                "context_summary": (
                    "reviewed memory projection framed for lab recommendation"
                ),
            },
            "candidate_spec_fixture": {
                "decision_mode": "llm_fixture",
                "intent": "suggest_reviewed_memory_candidate",
                "constraints": ["budget", "negative_preference", "reviewed_memory"],
            },
            "ranking_synthesis_fixture": {
                "decision_mode": "llm_fixture",
                "selected_candidate_id": selected_id,
                "ranked_candidate_ids": [selected_id] if selected_id else [],
                "rationale": "lab fixture selects reviewed-memory golden order",
            },
            "response_offer_fixture": {
                "decision_mode": "llm_fixture",
                "candidate_id": selected_id,
                "recommendation_served": False,
                "is_canonical_truth": False,
                "intake_commit_requested": False,
            },
        }
    )
    return payload


def _candidate_source(
    memory_summary_projection: Mapping[str, Any],
    remaining_budget_kcal: int,
) -> list[dict[str, Any]]:
    golden = _mapping(memory_summary_projection.get("golden_order_summary"))
    return [
        _candidate_from_order(order, remaining_budget_kcal)
        for order in _items(golden.get("orders"))
    ]


def _candidate_from_order(
    order: Mapping[str, Any],
    remaining_budget_kcal: int,
) -> dict[str, Any]:
    candidate_id = str(order.get("candidate_id") or "unknown_candidate")
    item_names = [str(item) for item in order.get("item_names") or []]
    store_name = str(order.get("store_name") or "")
    title = str(order.get("summary") or " ".join([store_name, *item_names]).strip())
    kcal = _int_or_default(
        order.get("estimated_kcal"),
        min(520, remaining_budget_kcal + 1),
    )
    return {
        "candidate_id": candidate_id,
        "title": title,
        "store_name": store_name,
        "source_type": "reviewed_memory_golden_order",
        "estimated_kcal": kcal,
        "estimated_kcal_range": {"min": max(kcal - 120, 0), "max": kcal},
        "remaining_budget_kcal": remaining_budget_kcal,
        "evidence_posture": "exact",
        "availability_posture": "available",
        "realistic_executable": True,
        "user_accessible": True,
        "item_patterns": _patterns([title, store_name, *item_names]),
        "hard_avoid_flags": [],
        "source_refs": [f"memory_candidate:{candidate_id}"],
    }


def _negative_summary(memory_summary_projection: Mapping[str, Any]) -> dict[str, Any]:
    profile = _mapping(memory_summary_projection.get("preference_profile_summary"))
    return {
        "items": [
            {
                "candidate_id": str(candidate_id),
                "pattern": str(candidate_id),
                "status": "confirmed_negative_preference",
            }
            for candidate_id in profile.get("negative_preference_blockers") or []
        ]
    }


def _patterns(values: list[str]) -> list[str]:
    return list(dict.fromkeys(_normalize(value) for value in values if value))


def _normalize(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


def _false_flags() -> dict[str, bool]:
    return {
        "runtime_effect_allowed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "live_search_used": False,
        "ranking_llm_invoked": False,
        "manager_context_packet_changed": False,
        "durable_memory_written": False,
    }


def _items(value: Any) -> list[Mapping[str, Any]]:
    return [
        item for item in value if isinstance(item, Mapping)
    ] if isinstance(value, list) else []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_or_default(value: Any, default: int) -> int:
    return value if isinstance(value, int) else default


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_reviewed_memory_recommendation_three_node_payload",
    "build_reviewed_memory_recommendation_five_node_payload",
]
