from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


TARGET_SPEC_PATH = "docs/quality/FOODDB_SELF_USE_V1_1000_PACKET_READY_COVERAGE_PLAN.md"

TARGET_LANE_COUNTS = {
    "exact_item_card": 250,
    "generic_common_serving": 400,
    "listed_component": 350,
}

TARGET_TOTAL = sum(TARGET_LANE_COUNTS.values())
EXACT_MACRO_COMPLETE_MINIMUM = 200
EDGE_LIVE_MATRIX_MIN_CASES = 36


def build_fooddb_self_use_v1_coverage_gap(
    *,
    approved_packet_ready_artifact: dict[str, Any],
) -> dict[str, Any]:
    summary = approved_packet_ready_artifact.get("summary") or {}
    lane_counts = _lane_counts(summary.get("packet_ready_lane_counts"))
    macro_complete = _int(summary.get("macro_complete_item_count"))
    current_total = sum(lane_counts.values())
    lane_gaps = {
        lane: max(0, target - lane_counts.get(lane, 0))
        for lane, target in TARGET_LANE_COUNTS.items()
    }
    macro_gap = max(0, EXACT_MACRO_COMPLETE_MINIMUM - macro_complete)
    complete = (
        current_total >= TARGET_TOTAL
        and all(lane_gaps[lane] == 0 for lane in TARGET_LANE_COUNTS)
        and macro_gap == 0
    )

    return {
        "artifact_type": "fooddb_self_use_v1_1000_packet_ready_coverage_gap",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "claim_scope": "fooddb_self_use_v1_coverage_gap_report_only",
        "target_spec_path": TARGET_SPEC_PATH,
        "producer_track": "FoodDB",
        "intended_consumers": ["FoodDB", "ManagerRuntime"],
        "fixture_or_real": approved_packet_ready_artifact.get("fixture_or_real") or "unknown",
        "runtime_truth_changed": False,
        "fooddb_truth_updated": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "target": {
            "packet_ready_item_count": TARGET_TOTAL,
            "lane_counts": dict(TARGET_LANE_COUNTS),
            "exact_macro_complete_minimum": EXACT_MACRO_COMPLETE_MINIMUM,
            "edge_live_matrix_min_cases": EDGE_LIVE_MATRIX_MIN_CASES,
        },
        "current": {
            "packet_ready_item_count": current_total,
            "lane_counts": lane_counts,
            "exact_macro_complete_count": macro_complete,
            "source_artifact_type": approved_packet_ready_artifact.get("artifact_type"),
            "selection_profile": summary.get("selection_profile"),
        },
        "gap": {
            "packet_ready_item_count": max(0, TARGET_TOTAL - current_total),
            "lane_counts": lane_gaps,
            "exact_macro_complete_count": macro_gap,
        },
        "status": "target_met" if complete else "below_target",
        "next_batch_priorities": _next_batch_priorities(lane_gaps, macro_gap),
        "non_claims": [
            "report_only",
            "no_fooddb_promotion",
            "no_runtime_truth_change",
            "no_manager_semantic_change",
            "no_product_readiness",
            "no_private_self_use_approval",
        ],
    }


def _lane_counts(value: Any) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    return {lane: _int(source.get(lane)) for lane in TARGET_LANE_COUNTS}


def _next_batch_priorities(lane_gaps: dict[str, int], macro_gap: int) -> list[str]:
    priorities: list[str] = []
    if lane_gaps["exact_item_card"] > 0 or macro_gap > 0:
        priorities.append("exact_brand_item_macro_complete_batch")
    if lane_gaps["generic_common_serving"] > 0:
        priorities.append("generic_common_serving_anchor_batch")
    if lane_gaps["listed_component"] > 0:
        priorities.append("listed_component_anchor_batch")
    return priorities


def _int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_self_use_v1_coverage_gap"]
