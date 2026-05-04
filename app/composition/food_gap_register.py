from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

_FAMILY_RULES = {
    "breakfast_": {
        "gap_family": "breakfast_combo",
        "required_evidence_type": [
            "generic_anchor",
            "combo_split_policy",
        ],
        "source_priority_hint": [
            "existing_repo_seed",
            "taiwan_tfda_open_data",
            "official_brand_chain_page",
        ],
        "evidence_missing_because": [
            "no_accepted_packet",
            "combo_split_policy_missing",
        ],
    },
    "lunch_": {
        "gap_family": "chicken_bento_rice_modifier",
        "required_evidence_type": [
            "taiwan_bento_anchor",
            "rice_portion_modifier",
        ],
        "source_priority_hint": [
            "existing_repo_seed",
            "taiwan_tfda_open_data",
            "official_brand_chain_page",
        ],
        "evidence_missing_because": [
            "no_accepted_packet",
            "portion_modifier_unresolved",
        ],
    },
    "tea_": {
        "gap_family": "bubble_tea_sugar_size_modifier",
        "required_evidence_type": [
            "drink_base_anchor",
            "sugar_modifier",
            "size_modifier",
            "pearl_component",
        ],
        "source_priority_hint": [
            "existing_repo_seed",
            "official_brand_chain_page",
            "open_food_facts",
        ],
        "evidence_missing_because": [
            "no_accepted_packet",
            "portion_modifier_unresolved",
            "source_quality_unknown",
        ],
    },
    "dinner_basket_": {
        "gap_family": "luwei_listed_components",
        "required_evidence_type": [
            "basket_component_anchor",
            "component_quantity_default",
        ],
        "source_priority_hint": [
            "existing_repo_seed",
            "taiwan_tfda_open_data",
            "usda_fallback",
        ],
        "evidence_missing_because": [
            "no_accepted_packet",
            "offline_fallback_insufficient",
        ],
    },
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _family_rule(turn_id: str) -> dict[str, Any]:
    for prefix, rule in _FAMILY_RULES.items():
        if turn_id.startswith(prefix):
            return rule
    return {
        "gap_family": "unclassified_food_evidence_gap",
        "required_evidence_type": ["food_evidence_review"],
        "source_priority_hint": ["existing_repo_seed"],
        "evidence_missing_because": ["no_accepted_packet"],
    }


def _candidate_from_turn(
    *,
    source_trace_id: str,
    turn_review: dict[str, Any],
) -> dict[str, Any]:
    turn_id = str(turn_review.get("turn_id") or "unknown-turn")
    rule = _family_rule(turn_id)
    return {
        "candidate_id": f"food_gap_{turn_id}",
        "status": "review_candidate",
        "observed_trace_id": source_trace_id,
        "observed_turn_id": turn_id,
        "candidate_label": rule["gap_family"],
        "gap_family": rule["gap_family"],
        "observed_user_text_for_display_only": str(
            turn_review.get("display_raw_user_input") or ""
        ),
        "manager_decision_summary": _json_safe(
            turn_review.get("manager_decision_summary")
        ),
        "required_evidence_type": list(rule["required_evidence_type"]),
        "source_priority_hint": list(rule["source_priority_hint"]),
        "human_review_status": "needs_review",
        "promotion_allowed": False,
        "cannot_update_food_kb_truth": True,
        "cannot_create_nutrition_seed": True,
        "cannot_create_exact_card": True,
        "cannot_create_packet_truth": True,
        "cannot_create_eval_oracle": True,
        "requires_human_review_before_promotion": True,
        "reason_from_review_surface": str(
            turn_review.get("evidence_gap_reason") or "food_evidence_gap"
        ),
        "evidence_missing_because": list(rule["evidence_missing_because"]),
        "classification_source": {
            "from_operator_review_surface": True,
            "raw_user_text_used_for_classification": False,
            "assistant_text_used_for_classification": False,
        },
    }


def build_food_kb_gap_register(operator_review: dict[str, Any]) -> dict[str, Any]:
    source_artifact = str(
        operator_review.get("artifact_type")
        or operator_review.get("source_artifact")
        or "unknown_operator_review"
    )
    source_trace_id = str(
        operator_review.get("source_artifact")
        or "accurate_intake_one_day_realistic_web_dogfood"
    )
    candidates: list[dict[str, Any]] = []
    non_candidate_turns: list[dict[str, Any]] = []

    for turn_review in list(operator_review.get("turn_reviews") or []):
        if not isinstance(turn_review, dict):
            continue
        classification = str(turn_review.get("classification") or "unknown")
        if classification == "food_evidence_gap":
            candidates.append(
                _candidate_from_turn(
                    source_trace_id=source_trace_id,
                    turn_review=turn_review,
                )
            )
            continue
        non_candidate_turns.append(
            {
                "observed_trace_id": source_trace_id,
                "observed_turn_id": str(turn_review.get("turn_id") or "unknown-turn"),
                "classification": classification,
                "reason": "turn is not a food_evidence_gap review candidate",
                "promotion_allowed": False,
            }
        )

    family_counts: dict[str, int] = {}
    for candidate in candidates:
        family = str(candidate["gap_family"])
        family_counts[family] = family_counts.get(family, 0) + 1

    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_food_kb_gap_register",
        "status": "generated",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_artifact": source_artifact,
        "source_status": str(operator_review.get("status") or "unknown"),
        "claim_scope": "food_gap_review_candidates_only",
        "local_only": True,
        "contains_personal_diet_logs": True,
        "do_not_commit": True,
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
        "promotion_policy": {
            "gap_candidate_status": "review_candidate",
            "promotion_allowed_by_default": False,
            "human_review_required_before_promotion": True,
            "can_update_food_kb_truth": False,
            "can_create_nutrition_seed": False,
            "can_create_exact_card": False,
            "can_create_packet_truth": False,
            "can_create_eval_oracle": False,
        },
        "classification_policy": {
            "input_source": "operator_review_surface",
            "raw_user_text_role": "display_only",
            "raw_user_text_used_for_classification": False,
            "assistant_text_used_for_classification": False,
            "food_kb_truth_update_allowed": False,
        },
        "summary": {
            "candidate_count": len(candidates),
            "non_candidate_count": len(non_candidate_turns),
            "family_counts": family_counts,
            "promotion_ready_count": 0,
        },
        "food_gap_candidates": _json_safe(candidates),
        "non_candidate_turns": _json_safe(non_candidate_turns),
    }


__all__ = ["build_food_kb_gap_register"]
