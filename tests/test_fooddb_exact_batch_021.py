from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_quaker_five_grain_yam_sesame_29_5g",
    "exact_quaker_complete_plant_protein_drink_250ml",
    "exact_quaker_sunshine_5bean_5grain_23g",
    "exact_quaker_black_sesame_quinoa_24g",
    "exact_lamole_classic_crispbread_original_25g",
    "exact_popochacha_clam_chili_ramen_115g",
    "exact_kuangchuan_fresh_soy_milk_200ml",
    "exact_unipresident_maixiang_ceylon_milk_tea_300ml",
}


def test_exact_batch_021_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_009.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_021_resolves_with_visible_macros() -> None:
    cases = [
        (
            "quaker five grain yam sesame 29.5g",
            "exact_quaker_five_grain_yam_sesame_29_5g",
            124.0,
            {"protein_g": 3.1, "carb_g": 23.5, "fat_g": 2.4},
        ),
        (
            "popochacha clam chili ramen 115g",
            "exact_popochacha_clam_chili_ramen_115g",
            511.0,
            {"protein_g": 11.3, "carb_g": 73.5, "fat_g": 19.1},
        ),
        (
            "kuangchuan fresh soy milk 200ml",
            "exact_kuangchuan_fresh_soy_milk_200ml",
            80.6,
            {"protein_g": 6.2, "carb_g": 7.2, "fat_g": 3.0},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
