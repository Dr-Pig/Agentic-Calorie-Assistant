from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


REQUIRED_RUNTIME_FIELDS = (
    "runtime_role",
    "runtime_estimate_allowed",
    "runtime_truth_allowed",
    "serving_basis",
    "portion_basis",
    "kcal_point",
    "kcal_range",
    "source_provenance",
    "approval_metadata",
    "runtime_usage_boundary",
)

BREAKFAST_AND_STAPLE_IDS = {
    "breakfast_staple_egg_pancake",
    "breakfast_staple_rice_roll",
    "breakfast_staple_sandwich",
    "staple_dumplings",
    "staple_potstickers",
}


def build_fooddb_broad_coverage_taxonomy(
    *,
    small_anchor_payload: dict[str, Any],
) -> dict[str, Any]:
    anchors = [item for item in small_anchor_payload.get("anchors") or [] if isinstance(item, dict)]
    runtime_visible = [
        item
        for item in anchors
        if item.get("record_kind") == "generic_anchor"
        and item.get("runtime_role") == "common_serving_anchor"
        and item.get("runtime_truth_allowed") is True
    ]
    existing_not_runtime = [
        item
        for item in anchors
        if item.get("record_kind") == "generic_anchor"
        and item.get("runtime_truth_allowed") is not True
    ]
    semantic_only = [
        item
        for item in anchors
        if item.get("record_kind") == "generic_semantic_only"
    ]
    groups = _candidate_groups(existing_not_runtime)
    runtime_groups = _candidate_groups(runtime_visible, promotion_status="runtime_visible")
    return {
        "artifact_type": "accurate_intake_fooddb_broad_coverage_taxonomy",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "fooddb_broad_coverage_taxonomy_report_only",
        "runtime_truth_changed": False,
        "product_loop_integration_claimed": False,
        "manager_context_changed": False,
        "summary": {
            "total_anchor_count": len(anchors),
            "runtime_visible_common_serving_count": len(runtime_visible),
            "existing_generic_not_runtime_count": len(existing_not_runtime),
            "semantic_only_basket_count": len(semantic_only),
            "next_runtime_batch_candidate_count": len(existing_not_runtime),
        },
        "runtime_groups": runtime_groups,
        "candidate_groups": groups,
        "semantic_only_baskets": [_semantic_only_basket(item) for item in semantic_only],
        "basket_boundary": {
            "bare_basket_behavior": "ask_followup_no_estimate",
            "listed_basket_behavior": "estimate_approved_runtime_component_anchors_only",
            "runtime_truth_changed": False,
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_product_loop_integration",
            "no_manager_context_change",
            "no_live_provider_call",
        ],
    }


def _candidate_groups(
    anchors: list[dict[str, Any]],
    *,
    promotion_status: str = "candidate_report_only",
) -> dict[str, list[dict[str, Any]]]:
    groups = {
        "single_items": [],
        "customizable_drinks": [],
        "breakfast_and_staples": [],
        "listed_basket_components": [],
        "composite_meals": [],
    }
    for anchor in anchors:
        group = _group_name(anchor)
        groups[group].append(_candidate_summary(anchor, promotion_status=promotion_status))
    for items in groups.values():
        items.sort(key=lambda item: item["anchor_id"])
    return groups


def _group_name(anchor: dict[str, Any]) -> str:
    anchor_id = str(anchor.get("anchor_id") or "")
    dish_type = str(anchor.get("dish_type") or "")
    if anchor_id in BREAKFAST_AND_STAPLE_IDS or dish_type == "breakfast_staple":
        return "breakfast_and_staples"
    if dish_type == "customizable_drink":
        return "customizable_drinks"
    if dish_type == "listed_item":
        return "listed_basket_components"
    if dish_type == "single_item":
        return "single_items"
    return "composite_meals"


def _candidate_summary(anchor: dict[str, Any], *, promotion_status: str) -> dict[str, Any]:
    missing = [
        field for field in REQUIRED_RUNTIME_FIELDS if anchor.get(field) in (None, "", [])
    ]
    return {
        "anchor_id": anchor.get("anchor_id"),
        "canonical_name": anchor.get("canonical_name"),
        "dish_type": anchor.get("dish_type"),
        "composition_posture": anchor.get("composition_posture"),
        "variance_level": anchor.get("variance_level"),
        "semantic_hints": list(anchor.get("semantic_hints") or []),
        "followup_hints": list(anchor.get("followup_hints") or []),
        "kcal_point": anchor.get("baseline_likely_kcal"),
        "kcal_range": anchor.get("baseline_kcal_range"),
        "major_modifiers": list(anchor.get("major_modifiers") or []),
        "promotion_status": promotion_status,
        "runtime_truth_allowed_after_report": promotion_status == "runtime_visible",
        "missing_runtime_fields": missing,
    }


def _semantic_only_basket(anchor: dict[str, Any]) -> dict[str, Any]:
    return {
        "semantic_id": anchor.get("canonical_name"),
        "canonical_name": anchor.get("canonical_name"),
        "aliases": list(anchor.get("aliases") or []),
        "dish_type": anchor.get("dish_type"),
        "composition_posture": anchor.get("composition_posture"),
        "clarify_required": anchor.get("clarify_required") is True,
        "runtime_truth_allowed": False,
        "runtime_usage_boundary": "semantic_only_bare_basket_followup",
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_broad_coverage_taxonomy"]
