from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_rizheng_crispy_frying_powder_20g",
    "exact_sato_millet_manjyu_10g",
    "exact_hutong_honey_pork_strips_140g",
    "exact_haidilao_tomato_vermicelli_131g",
    "exact_paldo_kimchi_ramen_120g",
    "exact_unipresident_beef_noodle_bag_90g",
    "exact_laiyike_beef_vegetable_cup_noodle_65g",
    "exact_doctor_diary_wheat_protein_noodle_80g",
    "exact_nanbeifang_chicken_shredded_noodle_50g",
    "exact_house_chicken_curry_pouch_200g",
    "exact_jereteria_muscat_jelly_drink_180g",
    "exact_sundown_milk_calcium_growth_powder_7g",
}


def test_exact_batch_055_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_020.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_055_resolves_with_visible_macros() -> None:
    cases = [
        (
            "paldo kimchi ramen 120g",
            "exact_paldo_kimchi_ramen_120g",
            487.0,
            {"protein_g": 10.0, "carb_g": 78.0, "fat_g": 15.0},
        ),
        (
            "doctor diary wheat protein noodle 80g",
            "exact_doctor_diary_wheat_protein_noodle_80g",
            259.0,
            {"protein_g": 20.5, "carb_g": 40.5, "fat_g": 1.7},
        ),
        (
            "house chicken curry pouch 200g",
            "exact_house_chicken_curry_pouch_200g",
            168.0,
            {"protein_g": 10.4, "carb_g": 14.0, "fat_g": 7.8},
        ),
        (
            "haidilao tomato vermicelli 131g",
            "exact_haidilao_tomato_vermicelli_131g",
            394.0,
            {"protein_g": 2.9, "carb_g": 79.1, "fat_g": 7.3},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
