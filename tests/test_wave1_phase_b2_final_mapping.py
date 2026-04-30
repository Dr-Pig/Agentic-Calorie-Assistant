from __future__ import annotations

from app.nutrition.application.final_mapping import (
    map_final_item_result,
    map_final_item_results,
)


def _item_result(
    *,
    exactness_posture: str = "estimated",
    likely_kcal: float | None = 450,
    kcal_range: list[float] | None = None,
    suggested_followup_question: str | None = "請補充糖度和杯型。",
) -> dict[str, object]:
    return {
        "interpreted_food_identity": "珍珠奶茶",
        "assumed_composition": "customizable drink",
        "kcal_range": kcal_range or [350, 550],
        "likely_kcal": likely_kcal,
        "exactness_posture": exactness_posture,
        "evidence_confidence": "moderate" if exactness_posture != "unresolved" else "insufficient",
        "evidence_used": [{"packet_id": "pkt_generic_anchor_custom_drink_boba_milk_tea"}],
        "rejected_candidates": [],
        "uncertainty_reason": "generic_anchor_modifier_requires_refinement",
        "suggested_followup_question": suggested_followup_question,
    }


def test_estimate_with_followup_maps_to_logged_when_write_owner_allows() -> None:
    mapping = map_final_item_result(
        _item_result(),
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )

    assert mapping["final_mapping_owner"] == "nutrition_final_mapping"
    assert mapping["external_outcome"] == "logged"
    assert mapping["ledger_status"] == "included"
    assert mapping["mutation_allowed"] is True
    assert mapping["followup_role"] == "precision_refinement"


def test_estimate_with_followup_maps_to_draft_when_write_owner_blocks() -> None:
    mapping = map_final_item_result(
        _item_result(),
        canonical_write_decision={"can_write_canonical": False},
        interaction_type="food_logging",
    )

    assert mapping["external_outcome"] == "draft"
    assert mapping["ledger_status"] == "excluded_pending_info"
    assert mapping["mutation_allowed"] is False
    assert mapping["followup_role"] == "precision_refinement"
    assert mapping["reason"] == "canonical_write_owner_blocked"


def test_unresolved_item_maps_to_draft_even_when_write_owner_allows() -> None:
    mapping = map_final_item_result(
        _item_result(exactness_posture="unresolved", likely_kcal=None, kcal_range=None),
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )

    assert mapping["external_outcome"] == "draft"
    assert mapping["ledger_status"] == "excluded_pending_info"
    assert mapping["mutation_allowed"] is False
    assert mapping["followup_role"] == "clarification_required"


def test_query_only_estimable_item_maps_to_no_mutation_query() -> None:
    mapping = map_final_item_result(
        _item_result(suggested_followup_question=None),
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="nutrition_info_query",
    )

    assert mapping["external_outcome"] == "no_mutation_query"
    assert mapping["ledger_status"] == "not_applicable"
    assert mapping["mutation_allowed"] is False
    assert mapping["followup_role"] == "none"


def test_final_mapping_many_preserves_order_and_marks_owner() -> None:
    results = map_final_item_results(
        [_item_result(), _item_result(exactness_posture="unresolved", likely_kcal=None, kcal_range=None)],
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )

    assert [item["external_outcome"] for item in results] == ["logged", "draft"]
    assert all(item["final_mapping_owner"] == "nutrition_final_mapping" for item in results)
