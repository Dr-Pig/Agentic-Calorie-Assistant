from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_yuchayuan_superior_milk_tea_250ml",
    "exact_paichiachun_cranberry_vinegar_100ml",
    "exact_old_captain_douchi_eel_50g",
    "exact_maxwell_selected_instant_coffee_2g",
    "exact_asahi_jurokucha_soy_milk_tea_265ml",
    "exact_ottogi_spicy_cheddar_cheese_stir_fried_noodle_120g",
    "exact_imei_chocolate_sandwich_wafers_25g",
    "exact_paldo_creamy_cheese_spicy_chicken_noodle_130g",
    "exact_ottogi_spicy_cheese_stir_fried_noodle_130g",
    "exact_seikatsu_salmon_floss_50g",
    "exact_chisheng_douchi_dried_fish_10g",
    "exact_sushiexpress_braised_squid_can_45g",
}


def test_exact_batch_061_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_026.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_061_resolves_with_visible_macros() -> None:
    cases = [
        (
            "asahi jurokucha soy milk tea 265ml",
            "exact_asahi_jurokucha_soy_milk_tea_265ml",
            91.0,
            {"protein_g": 2.1, "carb_g": 17.0, "fat_g": 1.6},
        ),
        (
            "ottogi spicy cheddar cheese stir fried noodle 120g",
            "exact_ottogi_spicy_cheddar_cheese_stir_fried_noodle_120g",
            495.0,
            {"protein_g": 9.0, "carb_g": 81.0, "fat_g": 15.0},
        ),
        (
            "seikatsu salmon floss 50g",
            "exact_seikatsu_salmon_floss_50g",
            110.0,
            {"protein_g": 11.0, "carb_g": 1.7, "fat_g": 6.6},
        ),
        (
            "sushiexpress braised squid can 45g",
            "exact_sushiexpress_braised_squid_can_45g",
            84.1,
            {"protein_g": 8.4, "carb_g": 6.9, "fat_g": 2.6},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
