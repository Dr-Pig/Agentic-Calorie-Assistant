from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_kikkoman_black_tea_soy_milk_200ml",
    "exact_so_good_high_protein_almond_milk_unsweetened_200ml",
    "exact_quaker_complete_nutrition_fiber_original_250ml",
    "exact_quaker_chia_oatmeal_nut_29g",
    "exact_mayushan_high_protein_black_sesame_paste_30g",
    "exact_taiquan_kuromi_dried_strawberry_30g",
    "exact_guguliu_naked_heart_drink_295ml",
    "exact_nestle_chocolate_au_lait_capsule_33_8g",
}


def test_exact_batch_032_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_013.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_032_resolves_with_visible_macros() -> None:
    cases = [
        (
            "kikkoman black tea soy milk 200ml",
            "exact_kikkoman_black_tea_soy_milk_200ml",
            97.0,
            {"protein_g": 4.4, "carb_g": 14.0, "fat_g": 2.6},
        ),
        (
            "so good high protein almond milk unsweetened 200ml",
            "exact_so_good_high_protein_almond_milk_unsweetened_200ml",
            78.0,
            {"protein_g": 8.2, "carb_g": 1.2, "fat_g": 4.6},
        ),
        (
            "quaker complete nutrition fiber original 250ml",
            "exact_quaker_complete_nutrition_fiber_original_250ml",
            242.0,
            {"protein_g": 9.0, "carb_g": 36.0, "fat_g": 7.8},
        ),
        (
            "mayushan high protein black sesame paste 30g",
            "exact_mayushan_high_protein_black_sesame_paste_30g",
            118.0,
            {"protein_g": 12.0, "carb_g": 12.5, "fat_g": 2.4},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
