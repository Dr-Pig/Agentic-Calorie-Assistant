from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_quaker_milk_oatmeal_28g",
    "exact_quaker_sunshine_oatmeal_33g",
    "exact_taisugar_black_oat_flakes_50g",
    "exact_vitamax_pumpkin_oatmeal_30g",
    "exact_quaker_cocoa_oatmeal_28g",
    "exact_quaker_chia_black_grain_nut_cereal_31g",
    "exact_kelloggs_extra_raisin_almond_muesli_37_5g",
    "exact_ovaltine_malt_drink_powder_30g",
}


def test_exact_batch_018_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_008.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_018_resolves_with_visible_macros() -> None:
    cases = [
        (
            "quaker milk oatmeal 28g",
            "exact_quaker_milk_oatmeal_28g",
            124.0,
            {"protein_g": 1.6, "carb_g": 20.5, "fat_g": 4.2},
        ),
        (
            "taisugar black oat flakes 50g",
            "exact_taisugar_black_oat_flakes_50g",
            173.2,
            {"protein_g": 4.9, "carb_g": 39.0, "fat_g": 1.2},
        ),
        (
            "ovaltine malt drink powder 30g",
            "exact_ovaltine_malt_drink_powder_30g",
            123.0,
            {"protein_g": 2.4, "carb_g": 23.3, "fat_g": 2.5},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
