from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_chungabern_baby_cabbage_pork_dumpling_100g",
    "exact_chungabern_peeled_chili_pork_dumpling_43g",
    "exact_aisin_handmade_fresh_pork_dumpling_50g",
    "exact_charlie_brown_peanut_bread_100g",
    "exact_charlie_brown_garlic_bread_100g",
    "exact_charlie_brown_mentaiko_bread_100g",
    "exact_aisin_lemon_chicken_drumstick_100g",
    "exact_aisin_fried_squid_popcorn_100g",
}


def test_exact_batch_006_loads_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_003.json"
        assert card["source_class"] in {"official_brand_chain_page", "official_brand_page"}
        assert str(card["source_url"]).startswith("https://")
        assert card["macro_basis"] in {"per_serving", "per_package"}
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_006_resolves_with_visible_macros() -> None:
    cases = [
        (
            "chungabern baby cabbage pork dumpling 100g",
            "exact_chungabern_baby_cabbage_pork_dumpling_100g",
            196.2,
            {"protein_g": 8.0, "carb_g": 22.6, "fat_g": 8.2},
        ),
        (
            "charlie brown garlic bread 100g",
            "exact_charlie_brown_garlic_bread_100g",
            341.7,
            {"protein_g": 6.6, "carb_g": 34.7, "fat_g": 20.1},
        ),
        (
            "aisin fried squid popcorn 100g",
            "exact_aisin_fried_squid_popcorn_100g",
            229.3,
            {"protein_g": 10.3, "carb_g": 19.8, "fat_g": 12.1},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
