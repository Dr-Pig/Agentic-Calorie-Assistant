from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.nutrition.application.food_source_quality_policy import FOOD_EVIDENCE_SOURCE_CLASSES

FOOD_EVIDENCE_PROMOTION_STAGES = (
    "review_candidate",
    "human_reviewed",
    "approved_seed_or_exact_card",
    "packet_truth",
)


def build_food_evidence_promotion_policy() -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_food_evidence_promotion_policy",
        "claim_scope": "truth_promotion_gate_before_food_kb_expansion",
        "promotion_stages": list(FOOD_EVIDENCE_PROMOTION_STAGES),
        "source_classes": deepcopy(FOOD_EVIDENCE_SOURCE_CLASSES),
        "llm_extraction_can_approve_truth": False,
        "food_gap_candidate_can_create_seed": False,
        "dogfood_correction_can_create_nutrition_truth": False,
        "deterministic_validator_role": [
            "validate_schema",
            "validate_provenance",
            "validate_source_class_compatibility",
            "require_human_approval",
        ],
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
    }


def evaluate_food_evidence_promotion_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    source_class = str(candidate.get("source_class") or "")
    requested = str(candidate.get("requested_promotion") or "review_candidate")
    human_review_status = str(candidate.get("human_review_status") or "needs_review")
    provenance = candidate.get("provenance") if isinstance(candidate.get("provenance"), dict) else {}
    blockers: list[str] = []

    source_policy = FOOD_EVIDENCE_SOURCE_CLASSES.get(source_class)
    if source_policy is None:
        blockers.append("unknown_source_class")
    else:
        for field in list(source_policy.get("required_provenance") or []):
            if field not in provenance:
                blockers.append(f"missing_required_provenance:{field}")

    if requested not in FOOD_EVIDENCE_PROMOTION_STAGES:
        blockers.append("unknown_requested_promotion_stage")
    if requested != "review_candidate" and human_review_status != "approved":
        blockers.append("human_review_required")
    if candidate.get("llm_extracted") is True and requested == "packet_truth":
        blockers.append("llm_extraction_cannot_create_packet_truth")
    if source_class == "dogfood_user_correction" and requested in {
        "approved_seed_or_exact_card",
        "packet_truth",
    }:
        blockers.append("dogfood_user_correction_is_review_material_only")
    if candidate.get("candidate_origin") == "food_gap_register" and requested in {
        "approved_seed_or_exact_card",
        "packet_truth",
    } and human_review_status != "approved":
        blockers.append("food_gap_candidate_requires_human_review")
    if requested == "packet_truth" and candidate.get("source_truth_stage") != "approved_seed_or_exact_card":
        blockers.append("packet_truth_requires_approved_seed_or_exact_card")

    allowed = not blockers
    return {
        "candidate_id": candidate.get("candidate_id"),
        "current_stage": _current_stage(human_review_status),
        "requested_promotion": requested,
        "next_stage": requested if allowed else None,
        "promotion_allowed": allowed,
        "blockers": blockers,
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
    }


def _current_stage(human_review_status: str) -> str:
    if human_review_status == "approved":
        return "human_reviewed"
    return "review_candidate"


__all__ = [
    "FOOD_EVIDENCE_PROMOTION_STAGES",
    "build_food_evidence_promotion_policy",
    "evaluate_food_evidence_promotion_candidate",
]
