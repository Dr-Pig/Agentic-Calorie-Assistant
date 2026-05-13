from __future__ import annotations

from app.shared.contracts.reusable_meal_policy import (
    build_reusable_meal_policy_contract,
    evaluate_reusable_meal_policy,
)


def test_reusable_meal_policy_contract_declares_drift_and_exact_reuse_rules() -> None:
    artifact = build_reusable_meal_policy_contract()

    assert artifact["artifact_type"] == "shared_reusable_meal_policy_contract"
    assert artifact["status"] == "pass"
    assert artifact["candidate_threshold_repetition_count"] == 3
    assert artifact["exact_reuse_requires_explicit_same_as_before"] is True
    assert artifact["drift_forces_reestimate"] is True


def test_reusable_meal_policy_allows_exact_reuse_only_after_explicit_confirmation() -> None:
    artifact = evaluate_reusable_meal_policy(
        repetition_count=4,
        explicit_same_as_before=True,
        ingredient_drift=False,
        portion_drift=False,
        source_drift=False,
        correction_count=0,
    )

    assert artifact["decision"] == "reuse_exact"
    assert artifact["promote_candidate"] is True


def test_reusable_meal_policy_uses_anchored_reuse_for_stable_repetition_without_explicit_confirmation() -> None:
    artifact = evaluate_reusable_meal_policy(
        repetition_count=4,
        explicit_same_as_before=False,
        ingredient_drift=False,
        portion_drift=False,
        source_drift=False,
        correction_count=1,
    )

    assert artifact["decision"] == "reuse_anchored"
    assert artifact["promote_candidate"] is True


def test_reusable_meal_policy_forces_reestimate_when_drift_is_present() -> None:
    artifact = evaluate_reusable_meal_policy(
        repetition_count=8,
        explicit_same_as_before=True,
        ingredient_drift=True,
        portion_drift=False,
        source_drift=False,
        correction_count=0,
    )

    assert artifact["decision"] == "re_estimate_required"
    assert artifact["drift_flags"]["ingredient_drift"] is True


def test_reusable_meal_policy_keeps_low_repetition_meals_as_candidates_only() -> None:
    artifact = evaluate_reusable_meal_policy(
        repetition_count=2,
        explicit_same_as_before=False,
        ingredient_drift=False,
        portion_drift=False,
        source_drift=False,
        correction_count=0,
    )

    assert artifact["decision"] == "candidate_only"
    assert artifact["promote_candidate"] is False
