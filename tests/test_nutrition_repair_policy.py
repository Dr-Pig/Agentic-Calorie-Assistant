from app.usecases.text_meal_nutrition_support import _nutrition_repair_note


def test_soft_polish_repair_removed_for_usable_heuristic_estimate() -> None:
    parsed = {
        "resolution_mode": "provisional_estimate",
        "estimate_mode": "heuristic_fallback",
        "confidence": "medium",
        "followup_question": "魚是怎麼做的？",
        "unresolved_info": [],
        "estimated_kcal": 700,
        "components": ["炒麵", "魚"],
    }
    nutrition_payload = {
        "exact_truth_available": False,
        "standardized_drink_like": False,
        "cup_size_provided": False,
        "packaged_exact_candidate_count": 0,
        "generic_drink_soft_avoid_exact": False,
        "exact_brand_conflict_count": 0,
        "core_default_candidate_count": 0,
        "anchor_lane_candidates": [{"title": "炒麵"}],
        "template_lane_hits": [],
        "meal_template_hit": False,
        "partial_grounding": {},
        "drink_customization_clues": [],
        "current_user_input": "我中午吃炒麵跟魚",
    }

    assert _nutrition_repair_note(parsed=parsed, nutrition_payload=nutrition_payload) is None


def test_soft_polish_repair_removed_for_usable_exact_answer_with_followup() -> None:
    parsed = {
        "resolution_mode": "exact_label_finalize",
        "estimate_mode": "exact_item",
        "confidence": "high",
        "followup_question": "杯量是大杯還是中杯？",
        "unresolved_info": [],
    }
    nutrition_payload = {
        "exact_truth_available": True,
        "standardized_drink_like": False,
        "cup_size_provided": True,
        "packaged_exact_candidate_count": 0,
        "generic_drink_soft_avoid_exact": False,
        "exact_brand_conflict_count": 0,
        "core_default_candidate_count": 1,
        "anchor_lane_candidates": [],
        "template_lane_hits": [],
        "meal_template_hit": False,
        "partial_grounding": {},
        "drink_customization_clues": [],
        "current_user_input": "我剛剛喝珍珠奶茶",
    }

    assert _nutrition_repair_note(parsed=parsed, nutrition_payload=nutrition_payload) is None


def test_legality_repair_kept_for_generic_drink_exact_finalize() -> None:
    parsed = {
        "resolution_mode": "exact_label_finalize",
        "estimate_mode": "exact_item",
        "confidence": "medium",
        "followup_question": "",
        "unresolved_info": [],
    }
    nutrition_payload = {
        "exact_truth_available": True,
        "standardized_drink_like": True,
        "cup_size_provided": False,
        "packaged_exact_candidate_count": 2,
        "generic_drink_soft_avoid_exact": True,
        "exact_brand_conflict_count": 0,
        "core_default_candidate_count": 0,
        "anchor_lane_candidates": [],
        "template_lane_hits": [],
        "meal_template_hit": False,
        "partial_grounding": {},
        "drink_customization_clues": [],
        "current_user_input": "我剛剛喝珍珠奶茶",
    }

    note = _nutrition_repair_note(parsed=parsed, nutrition_payload=nutrition_payload)
    assert note is not None
    assert "Do not finalize exact_item" in note
