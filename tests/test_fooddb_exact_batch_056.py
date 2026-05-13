from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_shanmeida_pudding_cake_100g",
    "exact_fengrong_fruit_gummies_40g",
    "exact_rizheng_low_gluten_flour_25g",
    "exact_nanbeifang_pancake_mix_25g",
    "exact_imei_thick_seaweed_egg_roll_38g",
    "exact_knorr_mentaiko_pasta_sauce_140g",
    "exact_hoshitaro_truffle_ham_snack_sticks_32_5g",
    "exact_mishima_furikake_mini_pack_3g",
    "exact_datui_roasted_seaweed_original_40g",
    "exact_guanshan_fragrant_rice_100g",
    "exact_imei_classic_seaweed_pancake_38_5g",
    "exact_hanwei_seaweed_crisp_corn_soup_45g",
}


def test_exact_batch_056_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_021.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_056_resolves_with_visible_macros() -> None:
    cases = [
        (
            "shanmeida pudding cake 100g",
            "exact_shanmeida_pudding_cake_100g",
            176.4,
            {"protein_g": 3.3, "carb_g": 30.3, "fat_g": 4.8},
        ),
        (
            "knorr mentaiko pasta sauce 140g",
            "exact_knorr_mentaiko_pasta_sauce_140g",
            151.6,
            {"protein_g": 4.5, "carb_g": 6.6, "fat_g": 12.2},
        ),
        (
            "guanshan fragrant rice 100g",
            "exact_guanshan_fragrant_rice_100g",
            345.0,
            {"protein_g": 6.2, "carb_g": 79.6, "fat_g": 0.2},
        ),
        (
            "hanwei seaweed crisp corn soup 45g",
            "exact_hanwei_seaweed_crisp_corn_soup_45g",
            294.9,
            {"protein_g": 4.6, "carb_g": 13.1, "fat_g": 24.9},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
