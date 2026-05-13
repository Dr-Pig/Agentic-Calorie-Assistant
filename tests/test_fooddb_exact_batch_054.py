from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_teasers_salted_caramel_chocolate_50g",
    "exact_fujiya_seika_brown_sugar_candy_50g",
    "exact_tops_75_no_sugar_dark_chocolate_50g",
    "exact_katz_caramel_sea_salt_popcorn_50g",
    "exact_yafang_hot_pot_tofu_skin_20g",
    "exact_nanbeifang_bread_crumbs_20g",
    "exact_formosa_chang_garlic_sausage_50g",
    "exact_hongjin_seaweed_corn_stick_7g",
    "exact_rio_santo_french_dressing_35_1g",
    "exact_maltesers_malt_chocolate_30g",
    "exact_zheyiguo_slow_stew_chicken_soup_50g",
    "exact_mcvities_original_digestive_biscuits_25g",
}


def test_exact_batch_054_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_019.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_054_resolves_with_visible_macros() -> None:
    cases = [
        (
            "teasers salted caramel chocolate 50g",
            "exact_teasers_salted_caramel_chocolate_50g",
            248.0,
            {"protein_g": 2.2, "carb_g": 33.2, "fat_g": 11.8},
        ),
        (
            "yafang hot pot tofu skin 20g",
            "exact_yafang_hot_pot_tofu_skin_20g",
            95.0,
            {"protein_g": 10.3, "carb_g": 2.2, "fat_g": 5.0},
        ),
        (
            "katz caramel sea salt popcorn 50g",
            "exact_katz_caramel_sea_salt_popcorn_50g",
            287.0,
            {"protein_g": 1.8, "carb_g": 29.0, "fat_g": 18.2},
        ),
        (
            "rio santo french dressing 35.1g",
            "exact_rio_santo_french_dressing_35_1g",
            72.0,
            {"protein_g": 0.2, "carb_g": 3.0, "fat_g": 6.6},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
