from __future__ import annotations

from app.shared.contracts.reusable_meal_memory_hint_bridge import (
    build_reusable_meal_memory_hint_bridge,
    build_reusable_meal_memory_hint_bridge_contract,
)


def test_reusable_meal_memory_hint_bridge_contract_keeps_memory_as_hint_only() -> None:
    artifact = build_reusable_meal_memory_hint_bridge_contract()

    assert artifact["artifact_type"] == "shared_reusable_meal_memory_hint_bridge_contract"
    assert artifact["status"] == "pass"
    assert artifact["memory_role"] == "suggest_reusable_meal_candidates_only"
    assert artifact["memory_must_not_assert_nutrition_truth"] is True


def test_reusable_meal_memory_hint_bridge_filters_memory_hints_to_known_candidates() -> None:
    artifact = build_reusable_meal_memory_hint_bridge(
        memory_summary={
            "suggested_reusable_meal_candidate_ids": ["ufe-1", "ufe-3"],
        },
        reusable_meal_candidate_ids=["ufe-1", "ufe-2"],
    )

    assert artifact["status"] == "pass"
    assert artifact["memory_hint_used"] is True
    assert artifact["suggested_candidate_ids"] == ["ufe-1"]
    assert artifact["candidate_truth_must_be_validated_separately"] is True


def test_reusable_meal_memory_hint_bridge_does_not_invent_candidates() -> None:
    artifact = build_reusable_meal_memory_hint_bridge(
        memory_summary={
            "suggested_reusable_meal_candidate_ids": ["ufe-9"],
        },
        reusable_meal_candidate_ids=["ufe-1", "ufe-2"],
    )

    assert artifact["memory_hint_used"] is False
    assert artifact["suggested_candidate_ids"] == []
