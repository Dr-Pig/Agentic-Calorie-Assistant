from __future__ import annotations

import hashlib
import json
from typing import Any

from app.nutrition.application.fooddb_runtime_anchor_policy import (
    POLICY_VERSION,
    PORTION_DEFAULTS,
)


def anchors_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("anchor_id")): item
        for item in payload.get("anchors") or []
        if isinstance(item, dict) and item.get("anchor_id")
    }


def coverage_entry(anchor_id: str, anchor: dict[str, Any] | None) -> dict[str, Any]:
    if anchor is None:
        return {
            "anchor_id": anchor_id,
            "display_name": None,
            "coverage_status": "gap",
            "classification_source": "structured_fooddb_records",
            "recommended_next_action": "add_review_candidate_before_truth",
            "runtime_anchor_available": False,
        }
    status = (
        "runtime_visible"
        if anchor.get("runtime_role") == "common_serving_anchor"
        and anchor.get("runtime_truth_allowed") is True
        else "existing_small_anchor_not_runtime"
    )
    return {
        "anchor_id": anchor_id,
        "display_name": anchor.get("canonical_name"),
        "coverage_status": status,
        "classification_source": "structured_fooddb_records",
        "recommended_next_action": (
            "none_runtime_visible"
            if status == "runtime_visible"
            else "consider_internal_seed_batch_promotion"
        ),
        "runtime_anchor_available": status == "runtime_visible",
        "kcal_point": anchor.get("kcal_point") or anchor.get("baseline_likely_kcal"),
        "kcal_range": anchor.get("kcal_range") or anchor.get("baseline_kcal_range"),
        "variance_level": anchor.get("variance_level"),
        "followup_hints": list(anchor.get("followup_hints") or []),
    }


def promotion_candidate(anchor_id: str, anchor: dict[str, Any] | None) -> dict[str, Any]:
    default = PORTION_DEFAULTS.get(anchor_id) or {}
    existing = anchor is not None
    kcal_point = anchor.get("baseline_likely_kcal") if anchor else None
    kcal_range = anchor.get("baseline_kcal_range") if anchor else None
    blockers = []
    if not existing:
        blockers.append("missing_existing_small_anchor")
    if not kcal_point:
        blockers.append("missing_kcal_point")
    if not kcal_range:
        blockers.append("missing_kcal_range")
    if not default:
        blockers.append("missing_portion_basis")
    return {
        "anchor_id": anchor_id,
        "display_name": anchor.get("canonical_name") if anchor else None,
        "existing_small_anchor_present": existing,
        "source_posture": "existing_small_anchor_store",
        "source_posture_flags": ["internal_seed", "not_external_source_promotion"],
        "kcal_point": kcal_point,
        "kcal_range": kcal_range,
        "serving_basis": "common_serving" if default else None,
        "portion_basis": portion_basis(anchor_id),
        "variance_level": anchor.get("variance_level") if anchor else None,
        "followup_hints": list(anchor.get("followup_hints") or []) if anchor else [],
        "runtime_usage_boundary": default.get("runtime_usage_boundary"),
        "promotion_ready": not blockers,
        "blocker_if_not_ready": blockers,
        "runtime_truth_allowed_after_n3": not blockers,
    }


def runtime_anchor_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    anchor_id = candidate["anchor_id"]
    kcal_range = candidate["kcal_range"]
    return {
        "anchor_id": anchor_id,
        "canonical_name": candidate["display_name"],
        "runtime_role": "common_serving_anchor",
        "runtime_estimate_allowed": True,
        "runtime_truth_allowed": True,
        "serving_basis": "common_serving",
        "portion_basis": candidate["portion_basis"],
        "kcal_point": candidate["kcal_point"],
        "kcal_range": kcal_range,
        "source_refs": [
            {
                "source_evidence_id": f"internal_seed_{anchor_id}",
                "runtime_role": "internal_seed_baseline",
                "serving_basis": "existing_small_anchor_baseline",
                "kcal_point": candidate["kcal_point"],
                "kcal_range": kcal_range,
            }
        ],
        "source_provenance": {
            "source_id": "existing_small_anchor_store_tw",
            "source_file": "app/knowledge/small_anchor_store_tw.json",
            "source_url": None,
            "record_id": anchor_id,
            "raw_row_hash": stable_hash(
                {
                    "anchor_id": anchor_id,
                    "kcal_point": candidate["kcal_point"],
                    "kcal_range": kcal_range,
                    "portion_basis": candidate["portion_basis"],
                }
            ),
        },
        "source_posture_flags": ["internal_seed", "not_external_source_promotion"],
        "approval_metadata": {
            "approval_mode": "internal_seed_batch_approved",
            "approval_scope": "pr110_mvp_gap_existing_small_anchor_batch",
            "policy_version": POLICY_VERSION,
            "approved_by": "user_batch_policy",
            "approved_at": None,
            "runtime_truth_allowed": True,
        },
        "range_policy": {
            "uncertainty_category": uncertainty_category(candidate["variance_level"]),
            "range_basis": "existing_small_anchor_baseline_range",
        },
        "runtime_usage_boundary": candidate["runtime_usage_boundary"],
        "kcal_basis": {
            "runtime_value_source": "existing_mvp_anchor_baseline",
            "external_source_role": "not_used_for_runtime_truth",
        },
    }


def portion_basis(anchor_id: str) -> dict[str, Any] | None:
    default = PORTION_DEFAULTS.get(anchor_id)
    if not default:
        return None
    return {
        key: value
        for key, value in default.items()
        if key not in {"runtime_usage_boundary"}
    } | {"derived_from": ["existing_small_anchor_store", "internal_seed_batch_policy"]}


def uncertainty_category(variance_level: str | None) -> str:
    if variance_level == "low":
        return "low_variance_single_item"
    if variance_level == "high":
        return "high_variance_customizable_drink_or_meal"
    return "moderate_prepared_item"


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


__all__ = [
    "anchors_by_id",
    "coverage_entry",
    "portion_basis",
    "promotion_candidate",
    "runtime_anchor_from_candidate",
    "stable_hash",
    "uncertainty_category",
]
