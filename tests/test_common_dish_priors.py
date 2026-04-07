from __future__ import annotations

from app.agent.knowledge_packets import resolve_ingredient_anchors, search_local_knowledge
from app.agent.nutrition_resolution_llm import normalize_structured_answer
from app.application.evidence_assembly import infer_expected_components


def test_infer_expected_components_splits_taiwanese_multi_item_quantity_list() -> None:
    components = infer_expected_components(
        user_input="林記米粉湯 1x 燙青菜 1x 黑白切 1x 乾麵 油豆腐",
        planner_foods=[],
    )

    assert "燙青菜" in components
    assert "黑白切" in components
    assert "乾麵" in components
    assert "油豆腐" in components
    assert "米粉湯" not in components


def test_search_local_knowledge_returns_common_dish_priors_for_taiwanese_small_eats() -> None:
    results = search_local_knowledge(
        "米粉湯 燙青菜 黑白切 乾麵 油豆腐",
        user_input="林記米粉湯 1x 燙青菜 1x 黑白切 1x 乾麵 油豆腐",
        limit=8,
    )

    titles = {str(item.get("title") or "") for item in results}
    assert "米粉湯" in titles
    assert "燙青菜" in titles
    assert "黑白切" in titles
    assert "乾麵" in titles
    assert "油豆腐" in titles


def test_common_dish_priors_get_non_none_identity_confidence() -> None:
    results = search_local_knowledge(
        "米粉湯 燙青菜 黑白切 乾麵 油豆腐",
        user_input="林記米粉湯 1x 燙青菜 1x 黑白切 1x 乾麵 油豆腐",
        limit=8,
    )
    by_title = {str(item.get("title") or ""): item for item in results}

    assert by_title["米粉湯"]["identity_confidence"] in {"low", "medium", "high"}
    assert by_title["燙青菜"]["identity_confidence"] in {"low", "medium", "high"}
    assert by_title["黑白切"]["identity_confidence"] in {"low", "medium", "high"}


def test_resolve_ingredient_anchors_includes_common_dish_priors() -> None:
    anchors = resolve_ingredient_anchors(["米粉湯", "燙青菜", "黑白切", "乾麵", "油豆腐"], limit=8)
    titles = {str(item.get("title") or "") for item in anchors}

    assert "米粉湯" in titles
    assert "燙青菜" in titles
    assert "黑白切" in titles
    assert "乾麵" in titles
    assert "油豆腐" in titles


def test_normalize_structured_answer_keeps_component_calories_from_nutrition_model() -> None:
    normalized = normalize_structured_answer(
        {
            "resolution_mode": "provisional_estimate",
            "resolution_basis": "cultural_dish_knowledge",
            "nutrition_model": {
                "total_calories": 780,
                "macros": {"protein_g": 38, "carbs_g": 98, "fat_g": 25},
                "components": [
                    {"name": "米粉湯", "calories": 190, "macros": {"protein_g": 4, "carbs_g": 34, "fat_g": 4}},
                    {"name": "燙青菜", "calories": 90, "macros": {"protein_g": 3, "carbs_g": 7, "fat_g": 6}},
                ],
            },
        },
        user_text="林記米粉湯 1x 燙青菜 1x 黑白切 1x 乾麵 油豆腐",
    )

    assert normalized["estimated_kcal"] == 780
    assert normalized["answer_payload"]["items"][0]["estimated_kcal"] == 190
    assert normalized["answer_payload"]["items"][1]["estimated_kcal"] == 90


def test_normalize_structured_answer_accepts_macro_aliases_without_g_suffix() -> None:
    normalized = normalize_structured_answer(
        {
            "resolution_mode": "provisional_estimate",
            "resolution_basis": "anchored_partial_grounding",
            "nutrition_model": {
                "calories": 730,
                "macros": {"protein": 35, "carbs": 72, "fat": 34},
            },
        },
        user_text="林記米粉湯 1x 燙青菜 1x 黑白切 1x 乾麵 油豆腐",
    )

    assert normalized["estimated_kcal"] == 730
    assert normalized["protein_g"] == 35
    assert normalized["carb_g"] == 72
    assert normalized["fat_g"] == 34
