from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_SET_PATH = ROOT / "docs" / "quality" / "runtime_lab_memory_edd_golden_set.yaml"
GOLDEN_EXTRACTION_CASE_IDS = (
    "explicit_preference_confirm_candidate",
    "profile_positive_large_satiety_fewer_meals",
    "profile_positive_strong_flavor_preference",
    "profile_positive_eating_out_no_cooking",
    "profile_positive_foodpanda_matsuya_discount_affinity",
    "temporary_preference_expires_without_confirmed_memory",
    "repeated_item_pattern_candidate_only",
    "golden_order_materialized_from_history",
    "correction_updates_canonical_not_memory",
)
CASE_INPUT_SUMMARIES = {
    "explicit_preference_confirm_candidate": (
        "User explicitly says they prefer high-satiety meals and can eat fewer, "
        "larger meals when dieting."
    ),
    "profile_positive_large_satiety_fewer_meals": (
        "User prefers larger portions and fullness, often eating two meals or even "
        "one meal per day."
    ),
    "profile_positive_strong_flavor_preference": (
        "User likes stronger-flavored foods and finds bland meals less appealing."
    ),
    "profile_positive_eating_out_no_cooking": (
        "User almost never cooks and usually eats out or orders delivery."
    ),
    "profile_positive_foodpanda_matsuya_discount_affinity": (
        "User often orders Matsuya on foodpanda because discounts make it attractive."
    ),
    "temporary_preference_expires_without_confirmed_memory": (
        "User says only this week they want lighter dinners because of a short event."
    ),
    "repeated_item_pattern_candidate_only": (
        "Canonical history shows five weekday lunches with chicken bento."
    ),
    "golden_order_materialized_from_history": (
        "Canonical history has three Morning Bar oatmeal plus latte bundles in 30 days."
    ),
    "correction_updates_canonical_not_memory": (
        "User corrects a meal estimate from 500 kcal to 700 kcal; this updates the "
        "meal thread rather than creating a memory."
    ),
}


def build_memory_record_grokfast_extraction_cases(
    *,
    golden_set_path: Path = GOLDEN_SET_PATH,
) -> list[dict[str, Any]]:
    golden = yaml.safe_load(golden_set_path.read_text(encoding="utf-8-sig"))
    by_id = {str(case["case_id"]): case for case in golden.get("cases") or []}
    cases: list[dict[str, Any]] = []
    for case_id in GOLDEN_EXTRACTION_CASE_IDS:
        source_case = by_id[case_id]
        trace_fields = _mapping(source_case.get("trace_fields"))
        cases.append(
            {
                "case_id": case_id,
                "case_type": str(source_case.get("case_type") or ""),
                "split": str(source_case.get("split") or ""),
                "source": str(source_case.get("source") or ""),
                "user_input_summary": CASE_INPUT_SUMMARIES[case_id],
                "manager_decision_field": str(
                    trace_fields.get("manager_decision_field") or ""
                ),
                "source_refs": [str(ref) for ref in trace_fields.get("source_refs") or []],
                "expected_candidate": dict(source_case.get("expected_candidate") or {}),
            }
        )
    return cases


def memory_record_grokfast_extraction_provider_payload(
    cases: list[Mapping[str, Any]],
    *,
    constraints: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "target_surface": "advanced_product_lab_memory_record_extraction_diagnostic",
        "case_count": len(cases),
        "cases": [
            {
                "case_id": str(case.get("case_id") or ""),
                "case_type": str(case.get("case_type") or ""),
                "user_input_summary": str(case.get("user_input_summary") or ""),
                "manager_decision_field": str(case.get("manager_decision_field") or ""),
                "source_refs": list(case.get("source_refs") or []),
            }
            for case in cases
        ],
        "output_contract": {
            "candidate_type_allowed": [
                "preference",
                "negative_preference",
                "temporary_preference",
                "pattern",
                "golden_order",
                "suppression",
                "contradiction_review",
                "feedback_event",
                "none",
            ],
            "polarity_allowed": ["positive", "negative", "neutral"],
            "strength_allowed": ["boost", "downrank", "block", "none"],
            "promotion_allowed_now_default": False,
            "human_review_required_for_preference_candidates": True,
            "durable_memory_write_allowed": False,
        },
        "constraints": dict(constraints),
    }


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
