from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_uha_fruit_gummy_90g",
    "exact_valnerina_truffle_spread_30g",
    "exact_skyflakes_cream_sandwich_crackers_30g",
    "exact_yuki_lemon_sandwich_cookies_18_7g",
    "exact_milka_raisin_nut_milk_chocolate_15g",
    "exact_ricky_waffle_butter_biscuit_15g",
    "exact_julies_lemond_cheese_sandwich_biscuit_18g",
    "exact_zess_lemon_sandwich_18g",
}


def test_exact_batch_034_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_014.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_034_resolves_with_visible_macros() -> None:
    cases = [
        (
            "uha fruit gummy 90g",
            "exact_uha_fruit_gummy_90g",
            352.4,
            {"protein_g": 2.4, "carb_g": 74.0, "fat_g": 5.2},
        ),
        (
            "skyflakes cream sandwich crackers 30g",
            "exact_skyflakes_cream_sandwich_crackers_30g",
            146.0,
            {"protein_g": 2.0, "carb_g": 21.0, "fat_g": 6.0},
        ),
        (
            "milka raisin nut milk chocolate 15g",
            "exact_milka_raisin_nut_milk_chocolate_15g",
            77.0,
            {"protein_g": 0.9, "carb_g": 9.0, "fat_g": 4.2},
        ),
        (
            "julies lemond cheese sandwich biscuit 18g",
            "exact_julies_lemond_cheese_sandwich_biscuit_18g",
            92.0,
            {"protein_g": 1.4, "carb_g": 11.3, "fat_g": 4.6},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
