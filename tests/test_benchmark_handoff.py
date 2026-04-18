from __future__ import annotations

from app.application.context_assembly import build_nutrition_resolution_payload
from app.schemas import DecisionPassResult, TaskMealLinkResult


def test_nutrition_resolution_payload_includes_exact_truth_candidates() -> None:
    payload = build_nutrition_resolution_payload(
        meal_state=None,
        meal_link_result=TaskMealLinkResult(),
        decision_result=DecisionPassResult(),
        normalized_evidence=[
            {
                "source_type": "local_retrieval",
                "query": "starbucks iced latte grande",
                "match_quality": "medium",
                "top_match": "latte (iced)",
                "raw": {
                    "title": "latte (iced)",
                    "brand": "Starbucks",
                    "kcal": 189,
                    "evidence_role": "exact_truth",
                    "match_confidence": "medium",
                    "match_path": "brand_plus_core_token",
                    "source_class": "exact_item_db",
                },
            }
        ],
        calibration_packet=None,
        user_input="starbucks iced latte grande",
        partial_grounding={},
    )

    assert payload["exact_truth_available"] is True
    assert payload["exact_truth_candidates"] == [
        {
            "title": "latte (iced)",
            "brand": "Starbucks",
            "kcal": 189,
            "label_macros": {},
            "match_quality": "medium",
            "match_path": "brand_plus_core_token",
            "source_class": "exact_item_db",
            "portion_basis_quality": "",
            "serving_basis": "",
            "brand_hint": "Starbucks",
            "query_alignment": "weak",
            "variant_type": "core_default",
            "candidate_relationship": "default_same_item_candidate",
            "retrieval_lane": "exact_lane",
            "aliases": [],
        }
    ]
