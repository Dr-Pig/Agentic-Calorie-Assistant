from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
from typing import Any


POLICY_VERSION = "fooddb_internal_seed_anchor_batch_v1"

INTERNAL_SEED_BATCH_ANCHOR_IDS = (
    "single_item_tea_egg",
    "breakfast_staple_egg_pancake",
    "custom_drink_latte",
    "generic_meal_chicken_bento",
    "listed_item_kelp",
    "listed_item_meatball",
    "listed_item_greens_home_cooked",
)

MVP_COVERAGE_TARGETS = (
    "single_item_tea_egg",
    "custom_drink_boba_milk_tea",
    "custom_drink_latte",
    "generic_meal_chicken_bento",
    "listed_item_tofu_dried",
    "listed_item_kelp",
    "listed_item_meatball",
    "listed_item_greens_home_cooked",
    "breakfast_staple_egg_pancake",
)

PORTION_DEFAULTS = {
    "single_item_tea_egg": {
        "portion_unit": "egg",
        "portion_quantity": 1,
        "portion_grams": 60,
        "label": "one tea egg",
        "runtime_usage_boundary": "stable_single_item_common_serving",
    },
    "breakfast_staple_egg_pancake": {
        "portion_unit": "serving",
        "portion_quantity": 1,
        "portion_grams": 130,
        "label": "one Taiwan breakfast egg pancake",
        "runtime_usage_boundary": "generic_range_estimate_with_refinement_not_exact",
    },
    "custom_drink_latte": {
        "portion_unit": "medium_cup",
        "portion_quantity": 1,
        "portion_ml": 360,
        "label": "one medium latte",
        "runtime_usage_boundary": "generic_drink_range_estimate_with_refinement",
    },
    "generic_meal_chicken_bento": {
        "portion_unit": "box",
        "portion_quantity": 1,
        "label": "one generic chicken bento",
        "runtime_usage_boundary": "generic_range_estimate_only_not_exact",
    },
    "listed_item_kelp": {
        "portion_unit": "piece",
        "portion_quantity": 1,
        "portion_grams": 30,
        "label": "one listed luwei kelp component",
        "runtime_usage_boundary": "listed_component_only",
    },
    "listed_item_meatball": {
        "portion_unit": "piece",
        "portion_quantity": 1,
        "portion_grams": 35,
        "label": "one listed luwei meatball component",
        "runtime_usage_boundary": "listed_component_only",
    },
    "listed_item_greens_home_cooked": {
        "portion_unit": "listed_component_portion",
        "portion_quantity": 1,
        "portion_grams": 100,
        "label": "one listed greens component portion",
        "runtime_usage_boundary": "listed_component_only_not_generic_vegetable_truth",
    },
}

FORBIDDEN_PROMOTIONS = [
    "new_food",
    "tfda_per_100g_as_common_serving",
    "open_food_facts_runtime_truth",
    "usda_runtime_truth",
    "old_base_db_runtime_truth",
    "official_brand_exact_card_runtime_truth",
]


def build_fooddb_runtime_coverage_matrix(
    *,
    small_anchor_payload: dict[str, Any],
) -> dict[str, Any]:
    anchors = _anchors_by_id(small_anchor_payload)
    entries = [_coverage_entry(anchor_id, anchors.get(anchor_id)) for anchor_id in MVP_COVERAGE_TARGETS]
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
    anchors = _anchors_by_id(small_anchor_payload)
    candidates = [_promotion_candidate(anchor_id, anchors.get(anchor_id)) for anchor_id in INTERNAL_SEED_BATCH_ANCHOR_IDS]
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
        _runtime_anchor_from_candidate(candidate)
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
    metadata_by_id = {
        anchor["anchor_id"]: anchor
        for anchor in runtime_batch.get("anchors") or []
        if isinstance(anchor, dict) and anchor.get("anchor_id")
    }
    updated = deepcopy(small_anchor_payload)
    for item in updated.get("anchors") or []:
        anchor_id = item.get("anchor_id")
        metadata = metadata_by_id.get(anchor_id)
        if not metadata:
            continue
        for key in (
            "runtime_role",
            "runtime_estimate_allowed",
            "runtime_truth_allowed",
            "serving_basis",
            "portion_basis",
            "kcal_point",
            "kcal_range",
            "source_refs",
            "source_provenance",
            "source_posture_flags",
            "approval_metadata",
            "range_policy",
            "runtime_usage_boundary",
            "kcal_basis",
        ):
            item[key] = metadata[key]
        item["baseline_likely_kcal"] = metadata["kcal_point"]
        item["baseline_kcal_range"] = metadata["kcal_range"]
    return updated


def build_fooddb_status_packet(
    *,
    small_anchor_payload: dict[str, Any],
    coverage_matrix: dict[str, Any],
    runtime_batch: dict[str, Any],
) -> dict[str, Any]:
    runtime_anchor_ids = [
        item["anchor_id"]
        for item in small_anchor_payload.get("anchors") or []
        if item.get("record_kind") == "generic_anchor"
        and item.get("runtime_role") == "common_serving_anchor"
        and item.get("runtime_truth_allowed") is True
    ]
    return {
        "artifact_type": "accurate_intake_fooddb_status_packet",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "fooddb_status_for_future_downstream_consumption",
        "pl_ce_files_changed": False,
        "product_loop_integration_claimed": False,
        "web_readiness_claimed": False,
        "private_self_use_approved": False,
        "live_provider_used": False,
        "real_fooddb_evidence_available": bool(runtime_anchor_ids),
        "runtime_visible_anchor_count": len(runtime_anchor_ids),
        "runtime_visible_anchor_ids": runtime_anchor_ids,
        "coverage_summary": coverage_matrix.get("summary", {}),
        "runtime_batch_summary": runtime_batch.get("summary", {}),
        "non_claims": [
            "no_product_loop_integration",
            "no_web_readiness",
            "no_private_self_use_approval",
            "no_live_provider_call",
            "no_kimi_or_grokfast",
        ],
    }


def _coverage_entry(anchor_id: str, anchor: dict[str, Any] | None) -> dict[str, Any]:
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


def _promotion_candidate(anchor_id: str, anchor: dict[str, Any] | None) -> dict[str, Any]:
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
        "portion_basis": _portion_basis(anchor_id),
        "variance_level": anchor.get("variance_level") if anchor else None,
        "followup_hints": list(anchor.get("followup_hints") or []) if anchor else [],
        "runtime_usage_boundary": default.get("runtime_usage_boundary"),
        "promotion_ready": not blockers,
        "blocker_if_not_ready": blockers,
        "runtime_truth_allowed_after_n3": not blockers,
    }


def _runtime_anchor_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
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
            "raw_row_hash": _stable_hash(
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
            "uncertainty_category": _uncertainty_category(candidate["variance_level"]),
            "range_basis": "existing_small_anchor_baseline_range",
        },
        "runtime_usage_boundary": candidate["runtime_usage_boundary"],
        "kcal_basis": {
            "runtime_value_source": "existing_mvp_anchor_baseline",
            "external_source_role": "not_used_for_runtime_truth",
        },
    }


def _portion_basis(anchor_id: str) -> dict[str, Any] | None:
    default = PORTION_DEFAULTS.get(anchor_id)
    if not default:
        return None
    return {
        key: value
        for key, value in default.items()
        if key not in {"runtime_usage_boundary"}
    } | {"derived_from": ["existing_small_anchor_store", "internal_seed_batch_policy"]}


def _anchors_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("anchor_id")): item
        for item in payload.get("anchors") or []
        if isinstance(item, dict) and item.get("anchor_id")
    }


def _uncertainty_category(variance_level: str | None) -> str:
    if variance_level == "low":
        return "low_variance_single_item"
    if variance_level == "high":
        return "high_variance_customizable_drink_or_meal"
    return "moderate_prepared_item"


def _stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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
