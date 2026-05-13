from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_klim_family_triple_calcium_milk_powder_42g",
    "exact_hsiangwei_quinoa_black_sesame_powder_30g",
    "exact_quaker_golden_grain_milk_oatmeal_33g",
    "exact_cheetos_special_spicy_corn_sticks_25_2g",
    "exact_minor_figures_barista_oat_milk_100ml",
    "exact_nestle_koko_krunch_cereal_30g",
    "exact_want_want_jumbo_rice_crackers_22_4g",
    "exact_palade_caramel_cinnamon_roll_cookie_35g",
    "exact_palade_earl_grey_roll_cookie_56g",
    "exact_kuangchi_iron_zinc_protein_oatmeal_100g",
    "exact_lotte_chocolate_bouchee_cake_27g",
    "exact_want_want_senbei_25g",
}


def test_exact_batch_059_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_024.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_059_resolves_with_visible_macros() -> None:
    cases = [
        (
            "klim family triple calcium milk powder 42g",
            "exact_klim_family_triple_calcium_milk_powder_42g",
            175.0,
            {"protein_g": 8.4, "carb_g": 23.5, "fat_g": 5.3},
        ),
        (
            "nestle koko krunch cereal 30g",
            "exact_nestle_koko_krunch_cereal_30g",
            113.0,
            {"protein_g": 2.4, "carb_g": 25.1, "fat_g": 0.8},
        ),
        (
            "palade earl grey roll cookie 56g",
            "exact_palade_earl_grey_roll_cookie_56g",
            269.0,
            {"protein_g": 5.3, "carb_g": 38.9, "fat_g": 10.2},
        ),
        (
            "want want senbei 25g",
            "exact_want_want_senbei_25g",
            119.0,
            {"protein_g": 1.1, "carb_g": 18.7, "fat_g": 4.5},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
