from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
from typing import Any


POLICY_VERSION = "fooddb_guarded_afk_internal_seed_batch_v1"
MAX_BATCH_SIZE = 40
FORBIDDEN_PROMOTIONS = [
    "new_food",
    "tfda_per_100g_as_common_serving",
    "open_food_facts_runtime_truth",
    "usda_runtime_truth",
    "old_base_db_runtime_truth",
    "official_brand_exact_card_runtime_truth",
]


def build_guarded_afk_runtime_anchor_batch(
    *,
    small_anchor_payload: dict[str, Any],
    max_items: int = MAX_BATCH_SIZE,
) -> dict[str, Any]:
    candidates = [
        item
        for item in small_anchor_payload.get("anchors") or []
        if isinstance(item, dict)
        and item.get("record_kind") == "generic_anchor"
        and item.get("runtime_truth_allowed") is not True
    ]
    anchors = [_runtime_anchor_from_existing_seed(candidate) for candidate in candidates]
    if len(anchors) > max_items:
        raise ValueError(f"Guarded AFK runtime batch exceeds max_items={max_items}.")
    return {
        "artifact_type": "accurate_intake_fooddb_guarded_afk_runtime_anchor_batch",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "claim_scope": "existing_small_anchor_guarded_afk_runtime_batch",
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
            "new_food_count": 0,
            "source_evidence_only_count": 0,
            "exact_card_count": 0,
        },
    }


def apply_guarded_afk_runtime_anchor_batch_to_small_anchor_store(
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


def _runtime_anchor_from_existing_seed(seed: dict[str, Any]) -> dict[str, Any]:
    anchor_id = str(seed["anchor_id"])
    kcal_point = seed["baseline_likely_kcal"]
    kcal_range = seed["baseline_kcal_range"]
    return {
        "anchor_id": anchor_id,
        "canonical_name": seed.get("canonical_name"),
        "runtime_role": "common_serving_anchor",
        "runtime_estimate_allowed": True,
        "runtime_truth_allowed": True,
        "serving_basis": "common_serving",
        "portion_basis": _portion_basis(seed),
        "kcal_point": kcal_point,
        "kcal_range": kcal_range,
        "source_refs": [
            {
                "source_evidence_id": f"internal_seed_{anchor_id}",
                "runtime_role": "internal_seed_baseline",
                "serving_basis": "existing_small_anchor_baseline",
                "kcal_point": kcal_point,
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
                    "kcal_point": kcal_point,
                    "kcal_range": kcal_range,
                    "major_modifiers": seed.get("major_modifiers") or [],
                }
            ),
        },
        "source_posture_flags": [
            "internal_seed",
            "guarded_afk_batch",
            "not_external_source_promotion",
        ],
        "approval_metadata": {
            "approval_mode": "guarded_afk_batch_policy_approved",
            "approval_scope": "existing_small_anchor_broad_taiwan_fooddb_batch",
            "policy_version": POLICY_VERSION,
            "approved_by": "guarded_afk_policy",
            "approved_at": None,
            "runtime_truth_allowed": True,
        },
        "range_policy": {
            "uncertainty_category": _uncertainty_category(seed.get("variance_level")),
            "range_basis": "existing_small_anchor_baseline_range",
        },
        "runtime_usage_boundary": _runtime_usage_boundary(seed),
        "kcal_basis": {
            "runtime_value_source": "existing_mvp_anchor_baseline",
            "external_source_role": "not_used_for_runtime_truth",
        },
    }


def _portion_basis(seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "portion_unit": _portion_unit(seed),
        "portion_quantity": 1,
        "label": f"one existing FoodDB common serving for {seed.get('canonical_name')}",
        "derived_from": [
            "existing_small_anchor_store",
            "guarded_afk_batch_policy",
        ],
    }


def _portion_unit(seed: dict[str, Any]) -> str:
    dish_type = str(seed.get("dish_type") or "")
    if dish_type == "customizable_drink":
        return "drink_serving"
    if dish_type == "listed_item":
        return "listed_component_portion"
    if dish_type == "single_item":
        return "single_item_serving"
    if dish_type in {"breakfast_staple", "rice_bowl", "generic_meal"}:
        return "meal_serving"
    return "generic_common_serving"


def _runtime_usage_boundary(seed: dict[str, Any]) -> str:
    dish_type = str(seed.get("dish_type") or "")
    if dish_type == "listed_item":
        return "listed_component_only"
    if dish_type == "customizable_drink":
        return "generic_drink_range_estimate_with_refinement"
    if dish_type == "single_item":
        return "generic_single_item_range_estimate_with_refinement"
    if dish_type == "breakfast_staple":
        return "generic_breakfast_staple_range_estimate_with_refinement"
    return "generic_range_estimate_with_refinement_not_exact"


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
    "MAX_BATCH_SIZE",
    "POLICY_VERSION",
    "apply_guarded_afk_runtime_anchor_batch_to_small_anchor_store",
    "build_guarded_afk_runtime_anchor_batch",
]
