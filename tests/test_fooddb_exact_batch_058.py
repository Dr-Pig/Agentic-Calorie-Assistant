from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_weiwei_a_black_garlic_tonkotsu_noodle_99g",
    "exact_nongshim_seafood_udon_noodle_120g",
    "exact_yorihada_beef_brisket_soup_500ml",
    "exact_ebara_mentaiko_udon_sauce_22g",
    "exact_daisho_ago_dashi_shabu_soup_148_5ml",
    "exact_master_pasta_bolognese_sauce_120g",
    "exact_master_tomato_basil_pasta_sauce_155g",
    "exact_master_onion_tomato_pasta_sauce_155g",
    "exact_master_mushroom_pasta_sauce_120g",
    "exact_paldo_volcano_spicy_chicken_stir_fried_noodle_140g",
    "exact_indomie_mi_goreng_cup_82g",
    "exact_ottogi_original_cheese_stir_fried_noodle_120g",
}


def test_exact_batch_058_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_023.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_058_resolves_with_visible_macros() -> None:
    cases = [
        (
            "weiwei a black garlic tonkotsu noodle 99g",
            "exact_weiwei_a_black_garlic_tonkotsu_noodle_99g",
            481.0,
            {"protein_g": 9.1, "carb_g": 54.4, "fat_g": 25.2},
        ),
        (
            "nongshim seafood udon noodle 120g",
            "exact_nongshim_seafood_udon_noodle_120g",
            425.0,
            {"protein_g": 8.9, "carb_g": 67.0, "fat_g": 13.5},
        ),
        (
            "master tomato basil pasta sauce 155g",
            "exact_master_tomato_basil_pasta_sauce_155g",
            102.0,
            {"protein_g": 3.1, "carb_g": 16.1, "fat_g": 2.8},
        ),
        (
            "ottogi original cheese stir fried noodle 120g",
            "exact_ottogi_original_cheese_stir_fried_noodle_120g",
            525.0,
            {"protein_g": 11.0, "carb_g": 82.0, "fat_g": 17.0},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
