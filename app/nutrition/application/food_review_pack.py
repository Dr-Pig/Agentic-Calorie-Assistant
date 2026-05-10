from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.nutrition.application.fooddb_macro_contract import (
    MACRO_REVIEW_DECISION_REQUIRED,
    build_macro_review_policy,
)
from app.nutrition.application.fooddb_quality_plan import FIRST_BATCH_REVIEW_FAMILIES


_REVIEW_DECISION_REQUIRED = [
    "candidate_identity_review",
    "source_class_selection",
    "source_provenance_review",
    "portion_default_review",
    "estimate_point_and_range_policy_review",
    "item_level_human_approval",
]


def build_food_evidence_human_review_pack(
    *,
    food_gap_register: dict[str, Any],
    inventory: dict[str, Any],
    quality_plan: dict[str, Any],
) -> dict[str, Any]:
    candidates = _candidate_dicts(food_gap_register)
    review_families = _review_families(quality_plan)
    macro_review_policy = build_macro_review_policy()
    review_packets = [
        _review_packet(
            family=family,
            candidates=[candidate for candidate in candidates if candidate["gap_family"] == family],
            macro_review_policy=macro_review_policy,
        )
        for family in review_families
    ]
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_food_evidence_human_review_pack",
        "status": "generated",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "claim_scope": "human_review_pack_before_fooddb_truth_promotion",
        "local_only": True,
        "contains_personal_diet_logs": True,
        "do_not_commit": True,
        "source_artifacts": {
            "food_gap_register": str(food_gap_register.get("artifact_type") or "unknown"),
            "inventory": str(inventory.get("artifact_type") or "unknown"),
            "quality_plan": str(quality_plan.get("artifact_type") or "unknown"),
        },
        "source_status": {
            "food_gap_register": str(food_gap_register.get("status") or "unknown"),
            "quality_plan_claim_scope": str(quality_plan.get("claim_scope") or "unknown"),
        },
        "inventory_snapshot": _inventory_snapshot(inventory),
        "macro_review_contract": macro_review_policy,
        "review_policy": {
            "truth_promotion_gate": "item_level_human_approval",
            "generic_anchor_estimate_policy_status": "pending_pr116_policy_manifest",
            "llm_extraction_allowed": False,
            "food_gap_candidate_can_create_truth": False,
            "raw_user_text_role": "display_only",
            "classification_source": "food_gap_register_structured_fields",
        },
        "summary": {
            "review_packet_count": len(review_packets),
            "candidate_count": sum(len(packet["candidates"]) for packet in review_packets),
            "promotion_ready_count": 0,
            "families_requiring_human_review": list(review_families),
        },
        "review_packets": review_packets,
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
        "not_claiming": [
            "fooddb_truth_promoted",
            "nutrition_seed_created",
            "exact_card_created",
            "packet_truth_created",
            "one_day_dogfood_pass",
            "product_readiness",
        ],
    }


def _candidate_dicts(food_gap_register: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(candidate)
        for candidate in list(food_gap_register.get("food_gap_candidates") or [])
        if isinstance(candidate, dict)
    ]


def _review_families(quality_plan: dict[str, Any]) -> list[str]:
    families = [
        str(family)
        for family in list(quality_plan.get("first_batch_review_families") or [])
        if str(family)
    ]
    return families or list(FIRST_BATCH_REVIEW_FAMILIES)


def _review_packet(
    *,
    family: str,
    candidates: list[dict[str, Any]],
    macro_review_policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "gap_family": family,
        "status": "review_packet_only",
        "promotion_allowed": False,
        "candidate_count": len(candidates),
        "review_decision_required": list(_REVIEW_DECISION_REQUIRED),
        "macro_review_decision_required": list(MACRO_REVIEW_DECISION_REQUIRED),
        "macro_review_policy": dict(macro_review_policy),
        "classification_source": {
            "input_source": "food_gap_register",
            "raw_user_text_role": "display_only",
            "raw_user_text_used_for_classification": False,
            "assistant_text_used_for_classification": False,
        },
        "candidates": [_review_candidate(candidate) for candidate in candidates],
        "blocked_actions": {
            "can_update_food_kb_truth": False,
            "can_create_nutrition_seed": False,
            "can_create_exact_card": False,
            "can_create_packet_truth": False,
            "can_create_macro_truth": False,
            "can_create_eval_oracle": False,
        },
    }


def _review_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "status": "review_candidate",
        "observed_trace_id": candidate.get("observed_trace_id"),
        "observed_turn_id": candidate.get("observed_turn_id"),
        "candidate_label": candidate.get("candidate_label"),
        "gap_family": candidate.get("gap_family"),
        "observed_user_text_for_display_only": candidate.get(
            "observed_user_text_for_display_only"
        ),
        "manager_decision_summary": _json_safe(candidate.get("manager_decision_summary")),
        "required_evidence_type": list(candidate.get("required_evidence_type") or []),
        "source_priority_hint": list(candidate.get("source_priority_hint") or []),
        "evidence_missing_because": list(candidate.get("evidence_missing_because") or []),
        "reason_from_review_surface": candidate.get("reason_from_review_surface"),
        "human_review_status": "needs_review",
        "promotion_allowed": False,
        "requires_human_review_before_promotion": True,
        "macro_candidate_review": {
            "status": "needs_review",
            "candidate_can_create_macro_truth": False,
            "values_may_remain_null": True,
            "missing_macro_blocks_kcal_logging": False,
        },
        "cannot_update_food_kb_truth": True,
        "cannot_create_nutrition_seed": True,
        "cannot_create_exact_card": True,
        "cannot_create_packet_truth": True,
        "cannot_create_eval_oracle": True,
        "classification_source": {
            "from_food_gap_register": True,
            "raw_user_text_used_for_classification": False,
            "assistant_text_used_for_classification": False,
        },
    }


def _inventory_snapshot(inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo_contained_seed_counts": dict(inventory.get("repo_contained_seed_counts") or {}),
        "source_class_breakdown": dict(inventory.get("source_class_breakdown") or {}),
        "missing_source_metadata_count": int(inventory.get("missing_source_metadata_count") or 0),
    }


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


__all__ = ["build_food_evidence_human_review_pack"]
