from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_kacha_salted_seaweed_rice_crust_130g",
    "exact_serena_oligo_egg_roll_32g",
    "exact_zess_original_soda_crackers_23g",
    "exact_yamamotoyama_small_fish_furikake_5_4g",
    "exact_nature_idea_vanilla_pepper_soda_cracker_18g",
    "exact_taiwan_livestock_pork_floss_25g",
    "exact_imei_classic_original_egg_roll_30g",
    "exact_kacha_yuzu_seaweed_32g",
    "exact_sanxing_spicy_grilled_eel_53g",
    "exact_hsin_tung_yang_braised_pork_sauce_55g",
    "exact_heidousang_black_bean_douchi_10g",
    "exact_hsin_tung_yang_spicy_meat_sauce_40g",
}


def test_exact_batch_057_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_022.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_057_resolves_with_visible_macros() -> None:
    cases = [
        (
            "sanxing spicy grilled eel 53g",
            "exact_sanxing_spicy_grilled_eel_53g",
            125.0,
            {"protein_g": 11.4, "carb_g": 5.7, "fat_g": 6.3},
        ),
        (
            "taiwan livestock pork floss 25g",
            "exact_taiwan_livestock_pork_floss_25g",
            118.0,
            {"protein_g": 5.3, "carb_g": 14.0, "fat_g": 4.5},
        ),
        (
            "hsin tung yang spicy meat sauce 40g",
            "exact_hsin_tung_yang_spicy_meat_sauce_40g",
            138.0,
            {"protein_g": 4.7, "carb_g": 1.2, "fat_g": 12.7},
        ),
        (
            "kacha salted seaweed rice crust 130g",
            "exact_kacha_salted_seaweed_rice_crust_130g",
            740.5,
            {"protein_g": 11.4, "carb_g": 57.9, "fat_g": 51.5},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
