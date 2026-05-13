from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "advanced_product_lab_context_engineering_mechanism_review.yaml"
)
TRAIN_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "advanced_product_lab_context_engineering_stress_pr_train.yaml"
)


def _review() -> dict:
    return yaml.safe_load(REVIEW_PATH.read_text(encoding="utf-8-sig"))


def _train() -> dict:
    return yaml.safe_load(TRAIN_PATH.read_text(encoding="utf-8-sig"))


def test_mechanism_decision_pack_adopts_pending_intent_short_term_state() -> None:
    from app.advanced_shadow_lab.context_engineering_mechanism_review import (
        build_context_engineering_mechanism_decision_pack,
    )

    pack = build_context_engineering_mechanism_decision_pack()

    assert pack["artifact_type"] == "advanced_product_lab_context_engineering_mechanism_decision_pack"
    assert pack["status"] == "pass"
    assert pack["recommended_option"] == "first_class_short_term_context_state"
    assert pack["runtime_effect_allowed"] is False
    assert pack["mainline_activation_enabled"] is False
    assert pack["canonical_mutation_allowed"] is False
    assert pack["next_decision"]["build_next"] == "context_engineering_stress_pr_train"


def test_mechanism_decision_pack_preserves_rejected_options_and_owner_boundary() -> None:
    from app.advanced_shadow_lab.context_engineering_mechanism_review import (
        build_context_engineering_mechanism_decision_pack,
    )

    pack = build_context_engineering_mechanism_decision_pack()

    assert pack["rejected_options"] == [
        "long_term_memory_record",
        "canonical_meal_thread_draft",
        "recommendation_intent_state",
        "keep_as_shadow_packet_only",
    ]
    assert pack["truth_owner"] == "hybrid"
    assert "classify_turn_and_plan_capabilities" in pack["llm_role"]
    assert "enforce_pending_intent_ttl" in pack["deterministic_role"]
    assert "raw_user_text_keyword_route" in pack["do_not_use_as_semantic_truth"]


def test_mechanism_review_validation_rejects_wrong_pending_option() -> None:
    from app.advanced_shadow_lab.context_engineering_mechanism_review import (
        validate_context_engineering_mechanism_review,
    )

    review = _review()
    review["pending_meal_intent_assessment"]["recommended_option"] = (
        "long_term_memory_record"
    )

    validation = validate_context_engineering_mechanism_review(review)

    assert validation["status"] == "fail"
    assert "pending_meal_intent.recommended_option_not_short_term_state" in validation[
        "blockers"
    ]


def test_context_engineering_train_marks_slice_three_complete() -> None:
    train = _train()

    assert train["dynamic_remaining_slice_count"] == 13
    assert train["last_completed_slice_number"] == 3
    assert train["last_merge_evidence"]["completed_slices"][-1] == {
        "slice_number": 3,
        "slice_id": "mechanism_challenge_decision_pack",
        "result": "mechanism_decision_pack_completed",
        "artifact": "app/advanced_shadow_lab/context_engineering_mechanism_review.py",
        "dynamic_remaining_slice_count_after": 13,
    }
