from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.nutrition.application import fooddb_runtime_anchor_policy as anchor_policy
from app.nutrition.application.fooddb_runtime_anchor_records import (
    anchors_by_id,
    coverage_entry,
    promotion_candidate,
    runtime_anchor_from_candidate,
)
from app.nutrition.application.fooddb_runtime_anchor_status import build_status_packet
from app.nutrition.application.fooddb_runtime_anchor_update import (
    apply_runtime_anchor_batch_to_small_anchor_store,
)

FORBIDDEN_PROMOTIONS = anchor_policy.FORBIDDEN_PROMOTIONS
INTERNAL_SEED_BATCH_ANCHOR_IDS = anchor_policy.INTERNAL_SEED_BATCH_ANCHOR_IDS
MVP_COVERAGE_TARGETS = anchor_policy.MVP_COVERAGE_TARGETS
POLICY_VERSION = anchor_policy.POLICY_VERSION
PORTION_DEFAULTS = anchor_policy.PORTION_DEFAULTS


def build_fooddb_runtime_coverage_matrix(
    *,
    small_anchor_payload: dict[str, Any],
) -> dict[str, Any]:
    anchors = anchors_by_id(small_anchor_payload)
    entries = [coverage_entry(anchor_id, anchors.get(anchor_id)) for anchor_id in MVP_COVERAGE_TARGETS]
    return {
        "artifact_type": "accurate_intake_fooddb_runtime_coverage_matrix",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "claim_scope": "fooddb_coverage_diagnostic_only",
        "runtime_truth_changed": False,
        "classification_source": "structured_fooddb_records",
        "coverage_entries": entries,
        "summary": {
            "target_count": len(entries),
            "runtime_visible_count": sum(
                1 for entry in entries if entry["coverage_status"] == "runtime_visible"
            ),
            "existing_small_anchor_not_runtime_count": sum(
                1
                for entry in entries
                if entry["coverage_status"] == "existing_small_anchor_not_runtime"
            ),
            "gap_count": sum(1 for entry in entries if entry["coverage_status"] == "gap"),
        },
    }


def build_existing_anchor_promotion_plan(
    *,
    small_anchor_payload: dict[str, Any],
) -> dict[str, Any]:
    anchors = anchors_by_id(small_anchor_payload)
    candidates = [
        promotion_candidate(anchor_id, anchors.get(anchor_id))
        for anchor_id in INTERNAL_SEED_BATCH_ANCHOR_IDS
    ]
    return {
        "artifact_type": "accurate_intake_fooddb_existing_anchor_promotion_plan",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "claim_scope": "promotion_plan_only_no_runtime_truth",
        "runtime_truth_changed": False,
        "batch_policy": {
            "approval_mode": "internal_seed_batch_approved",
            "approval_scope": "pr110_mvp_gap_existing_small_anchor_batch",
            "max_items": 8,
            "source_policy": "existing_small_anchor_store_only",
            "runtime_role_after_promotion": "common_serving_anchor",
            "policy_version": POLICY_VERSION,
        },
        "forbidden_promotions": FORBIDDEN_PROMOTIONS,
        "candidates": candidates,
        "summary": {
            "candidate_count": len(candidates),
            "promotion_ready_count": sum(1 for candidate in candidates if candidate["promotion_ready"]),
            "blocked_count": sum(1 for candidate in candidates if not candidate["promotion_ready"]),
        },
    }


def build_internal_seed_runtime_anchor_batch(
    *,
    small_anchor_payload: dict[str, Any],
) -> dict[str, Any]:
    plan = build_existing_anchor_promotion_plan(small_anchor_payload=small_anchor_payload)
    anchors = [
        runtime_anchor_from_candidate(candidate)
        for candidate in plan["candidates"]
        if candidate["promotion_ready"]
    ]
    if len(anchors) > 8:
        raise ValueError("Internal seed batch exceeds the approved max_items=8 gate.")
    return {
        "artifact_type": "accurate_intake_fooddb_internal_seed_runtime_anchor_batch",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "claim_scope": "selected_internal_seed_runtime_anchor_batch",
        "policy_version": POLICY_VERSION,
        "runtime_truth_changed": True,
        "source_policy": "existing_small_anchor_store_only",
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
        "forbidden_promotions": FORBIDDEN_PROMOTIONS,
        "anchors": anchors,
        "summary": {
            "selected_runtime_anchor_count": len(anchors),
            "source_evidence_only_count": 0,
            "exact_card_count": 0,
        },
    }


def apply_internal_seed_runtime_anchor_batch_to_small_anchor_store(
    small_anchor_payload: dict[str, Any],
    runtime_batch: dict[str, Any],
) -> dict[str, Any]:
    return apply_runtime_anchor_batch_to_small_anchor_store(small_anchor_payload, runtime_batch)


def build_fooddb_status_packet(
    *,
    small_anchor_payload: dict[str, Any],
    coverage_matrix: dict[str, Any],
    runtime_batch: dict[str, Any],
) -> dict[str, Any]:
    return build_status_packet(
        small_anchor_payload=small_anchor_payload,
        coverage_matrix=coverage_matrix,
        runtime_batch=runtime_batch,
        generated_at_utc=_now(),
    )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "INTERNAL_SEED_BATCH_ANCHOR_IDS",
    "POLICY_VERSION",
    "apply_internal_seed_runtime_anchor_batch_to_small_anchor_store",
    "build_existing_anchor_promotion_plan",
    "build_fooddb_runtime_coverage_matrix",
    "build_fooddb_status_packet",
    "build_internal_seed_runtime_anchor_batch",
]
