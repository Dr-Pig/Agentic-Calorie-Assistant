from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.live_bundle_fixture_inputs import (
    build_live_bundle_chain_payload,
)


def build_memory_record_chain_payload(summary: Mapping[str, Any]) -> dict[str, Any]:
    payload = build_live_bundle_chain_payload()
    memory_projection = memory_projection_from_summary(summary)
    recommendation_payload = dict(payload["recommendation_payload"])
    recommendation_payload["memory_summary_projection"] = memory_projection
    golden_candidate(recommendation_payload).update(
        {
            "title": "Morning Bar oatmeal",
            "store_name": "Morning Bar",
            "estimated_kcal": 420,
            "estimated_kcal_range": {"min": 360, "max": 420},
            "item_patterns": ["oatmeal"],
            "source_refs": ["memory_candidate:golden-breakfast-oatmeal"],
        }
    )
    return {
        **payload,
        "memory_summary_projection": memory_projection,
        "recommendation_payload": recommendation_payload,
    }


def memory_projection_from_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    memory_ids = memory_record_ids(summary)
    negative_ids = [item for item in memory_ids if item.startswith("negative-")]
    golden_ids = [item for item in memory_ids if item.startswith("golden-")]
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": memory_ids,
            "negative_preference_blockers": negative_ids,
        },
        "golden_order_summary": {
            "orders": [
                {
                    "candidate_id": "golden-1",
                    "memory_record_id": golden_ids[0] if golden_ids else "",
                    "store_name": "Morning Bar",
                }
            ]
        },
        "suppression_summary": {"suppression_blockers": []},
        **dict(FALSE_FLAGS),
    }


def memory_record_ids(summary: Mapping[str, Any]) -> list[str]:
    return [str(item) for item in summary.get("lab_memory_record_ids") or []]


def golden_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    for item in payload.get("candidate_source_fixture") or []:
        if isinstance(item, dict) and item.get("candidate_id") == "golden-1":
            return item
    raise ValueError("candidate_not_found:golden-1")


__all__ = [
    "build_memory_record_chain_payload",
    "memory_projection_from_summary",
    "memory_record_ids",
]
