from app.nutrition.agent.local_knowledge_selector import load_retrieval_documents, search_local_knowledge
from app.nutrition.agent.exact_item_packets import resolve_exact_item
from app.nutrition.agent.nutrition_engine import _kcal, deterministic_macro_estimate, lookup_ingredient_profile
from app.schemas import IngredientCandidate


def test_load_retrieval_documents_includes_base_nutrition_records() -> None:
    docs = load_retrieval_documents()
    banana = next(
        doc for doc in docs if doc["source_type"] == "base_nutrition" and doc["title"] == "Banana"
    )
    assert banana["kcal_band"] == "82.4 kcal"
    assert "\u5317\u8549\u5e73\u5747\u503c" in banana["aliases"]
    assert banana["evidence_role"] == "ingredient_anchor"
    assert banana["macro_completeness"] == "kcal_only"
    assert banana["estimate_eligibility"] == "heuristic_only"


def test_search_local_knowledge_can_hit_base_nutrition_records() -> None:
    docs = search_local_knowledge("\u9999\u8549", user_input="\u6211\u5403\u4e86\u9999\u8549", limit=3)
    assert docs
    assert docs[0]["source_type"] in {"exact_item_card", "base_nutrition"}


def test_multi_token_base_food_results_are_usable_for_local_retrieval() -> None:
    docs = search_local_knowledge(
        "\u9999\u8549 \u8c46\u6f3f",
        user_input="\u6211\u65e9\u9910\u5403\u9999\u8549\u8ddf\u8c46\u6f3f",
        limit=4,
    )
    titles = [doc["title"] for doc in docs[:4]]
    assert "Soy Milk" in titles
    assert "Banana" in titles


def test_search_local_knowledge_prefers_exact_item_card_for_branded_drink() -> None:
    docs = search_local_knowledge(
        "\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73 400ml",
        user_input="\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73 400ml",
        limit=3,
    )
    assert docs
    assert docs[0]["source_type"] == "exact_item_card"
    assert docs[0]["evidence_role"] == "exact_truth"
    assert docs[0]["title"] == "\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73(400ml)"


def test_bootstrap_ramen_profile_is_not_promoted_to_exact_truth() -> None:
    docs = search_local_knowledge(
        "\u9df9\u6d41\u62c9\u9eb52929\u8c5a\u9aa8\u62c9\u9eb5",
        user_input="\u9df9\u6d41\u62c9\u9eb52929\u8c5a\u9aa8\u62c9\u9eb5",
        limit=5,
    )
    assert docs
    eagle = next(doc for doc in docs if "\u9df9\u6d41" in doc["title"])
    assert eagle["evidence_role"] == "dish_prior"
    assert eagle["record_role"] == "dish_prior"
    assert eagle["estimate_eligibility"] == "anchored"


def test_resolve_exact_item_ignores_bootstrap_ramen_shop_profile() -> None:
    docs = resolve_exact_item("\u9df9\u6d41\u62c9\u9eb52929\u8c5a\u9aa8\u62c9\u9eb5", limit=5)
    assert all("\u9df9\u6d41" not in doc["title"] for doc in docs)


def test_search_local_knowledge_matches_exact_item_card_with_possessive_and_quotes() -> None:
    docs = search_local_knowledge(
        "\u722d\u9bae\u8ff4\u8f49\u58fd\u53f8\u7684\u7126\u7cd6\u9bae\u9b5a\uff08\u5169\u8cab\uff09",
        user_input="\u722d\u9bae\u8ff4\u8f49\u58fd\u53f8\u7684\u300c\u7126\u7cd6\u9bae\u9b5a\u300d\uff08\u5169\u8cab\uff09",
        limit=3,
    )
    assert docs
    assert docs[0]["source_type"] == "exact_item_card"
    assert docs[0]["title"] == "\u722d\u9bae \u7126\u7cd6\u9bae\u9b5a(\u5169\u8cab)"


def test_resolve_exact_item_prefers_iced_latte_over_hot_variant() -> None:
    docs = resolve_exact_item("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f", limit=3)

    assert docs
    assert docs[0]["title"] == "\u661f\u5df4\u514b \u90a3\u5802(\u51b0) \u5927\u676f"
    assert docs[0]["evidence_role"] == "exact_truth"


def test_resolve_exact_item_accepts_prefixed_user_sentence_for_starbucks_latte() -> None:
    docs = resolve_exact_item("\u6211\u559d\u4e86\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f", limit=3)

    assert docs
    assert docs[0]["title"] == "\u661f\u5df4\u514b \u90a3\u5802(\u51b0) \u5927\u676f"
    assert docs[0]["evidence_role"] == "exact_truth"


def test_lookup_ingredient_profile_uses_exact_base_nutrition_macros() -> None:
    profile = lookup_ingredient_profile("\u8c46\u6f3f", "", "other")
    assert profile is not None
    assert profile.protein_g == 3
    assert profile.carb_g == 9
    assert profile.fat_g == 1
    assert _kcal(profile) == 57


def test_lookup_ingredient_profile_can_use_kcal_only_tfda_anchor() -> None:
    profile = lookup_ingredient_profile("\u9999\u8549", "", "other")
    assert profile is not None
    assert profile.carb_g > 0
    assert _kcal(profile) > 0


def test_food_specific_kcal_only_avocado_uses_fat_heavy_heuristic() -> None:
    profile = lookup_ingredient_profile("\u916a\u68a8", "", "other")
    assert profile is not None
    assert profile.fat_g > profile.carb_g
    assert profile.fat_g > 0


def test_generic_fruit_heuristic_still_treats_banana_as_carb_dominant() -> None:
    profile = lookup_ingredient_profile("\u9999\u8549", "", "other")
    assert profile is not None
    assert profile.carb_g > profile.fat_g


def test_deterministic_estimate_marks_banana_soymilk_as_anchored_component_mode() -> None:
    result = deterministic_macro_estimate(
        [
            IngredientCandidate(name="\u9999\u8549", amount_hint="small", role="vegetable"),
            IngredientCandidate(name="\u8c46\u6f3f", amount_hint="small", role="other"),
        ]
    )
    assert result["estimate_mode"] == "heuristic_fallback_mode"
    assert "kcal_only_anchor" in result["heuristic_dependencies"]
    assert result["totals"]["estimated_kcal"] > 0


def test_deterministic_estimate_keeps_complete_anchor_out_of_exact_mode() -> None:
    result = deterministic_macro_estimate(
        [
            IngredientCandidate(name="\u8c46\u6f3f", amount_hint="small", role="other"),
        ]
    )
    assert result["estimate_mode"] == "anchored_component_mode"
    assert result["why_not_exact"] == "No exact item truth matched; estimate comes from complete ingredient anchors."
