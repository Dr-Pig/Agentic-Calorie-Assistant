from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
MECHANISM_REVIEW_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "advanced_product_lab_context_engineering_mechanism_review.yaml"
)
EXPECTED_REJECTED_OPTIONS = [
    "long_term_memory_record",
    "canonical_meal_thread_draft",
    "recommendation_intent_state",
    "keep_as_shadow_packet_only",
]


def load_context_engineering_mechanism_review() -> dict[str, Any]:
    return dict(yaml.safe_load(MECHANISM_REVIEW_PATH.read_text(encoding="utf-8-sig")))


def validate_context_engineering_mechanism_review(
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = review or load_context_engineering_mechanism_review()
    blockers: list[str] = []

    _expect_equal(
        blockers,
        "artifact_type",
        data.get("artifact_type"),
        "advanced_product_lab_context_engineering_mechanism_review",
    )
    _expect_equal(blockers, "status", data.get("status"), "active")

    pending = dict(data.get("pending_meal_intent_assessment") or {})
    if pending.get("recommended_option") != "first_class_short_term_context_state":
        blockers.append("pending_meal_intent.recommended_option_not_short_term_state")

    rejected_options = list((pending.get("rejected_options") or {}).keys())
    if rejected_options != EXPECTED_REJECTED_OPTIONS:
        blockers.append("pending_meal_intent.rejected_options_drift")

    boundary = dict(data.get("llm_deterministic_boundary") or {})
    if boundary.get("truth_owner") != "hybrid":
        blockers.append("llm_deterministic_boundary.truth_owner_not_hybrid")
    for required in [
        "classify_turn_and_plan_capabilities",
        "judge_when_user_language_requests_proposal_vs_confirmation",
    ]:
        if required not in boundary.get("llm_role", []):
            blockers.append(f"llm_role.missing:{required}")
    for required in ["enforce_pending_intent_ttl", "enforce_mutation_legality"]:
        if required not in boundary.get("deterministic_role", []):
            blockers.append(f"deterministic_role.missing:{required}")
    if "raw_user_text_keyword_route" not in boundary.get("do_not_use_as_semantic_truth", []):
        blockers.append("semantic_truth_boundary.raw_user_text_keyword_route_missing")

    if (data.get("next_decision") or {}).get("build_next") != (
        "context_engineering_stress_pr_train"
    ):
        blockers.append("next_decision.build_next_not_context_stress_train")

    return {
        "artifact_type": "advanced_product_lab_context_engineering_mechanism_review_validation",
        "status": "pass" if not blockers else "fail",
        "blockers": blockers,
    }


def build_context_engineering_mechanism_decision_pack() -> dict[str, Any]:
    review = load_context_engineering_mechanism_review()
    validation = validate_context_engineering_mechanism_review(review)
    pending = dict(review["pending_meal_intent_assessment"])
    boundary = dict(review["llm_deterministic_boundary"])
    return {
        "artifact_type": "advanced_product_lab_context_engineering_mechanism_decision_pack",
        "status": validation["status"],
        "runtime_effect_allowed": False,
        "mainline_activation_enabled": False,
        "canonical_mutation_allowed": False,
        "recommended_option": pending["recommended_option"],
        "rejected_options": list(pending["rejected_options"].keys()),
        "required_next_capabilities": pending["required_next_capabilities"],
        "truth_owner": boundary["truth_owner"],
        "llm_role": boundary["llm_role"],
        "deterministic_role": boundary["deterministic_role"],
        "do_not_use_as_semantic_truth": boundary["do_not_use_as_semantic_truth"],
        "next_decision": review["next_decision"],
        "validation": validation,
    }


def _expect_equal(blockers: list[str], field: str, actual: object, expected: object) -> None:
    if actual != expected:
        blockers.append(f"{field}.expected_{expected}_actual_{actual}")


__all__ = [
    "MECHANISM_REVIEW_PATH",
    "build_context_engineering_mechanism_decision_pack",
    "load_context_engineering_mechanism_review",
    "validate_context_engineering_mechanism_review",
]
