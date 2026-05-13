from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


BATCH_IDS = {
    "exact_unipresident_ab_yogurt_drink_strawberry_300_6ml",
    "exact_anlene_high_protein_calcium_formula_200ml",
    "exact_lipton_milk_tea_250ml",
    "exact_nestle_eagle_condensed_milk_10g",
    "exact_imei_milk_cream_wafer_38g",
    "exact_ganbai_shi_96_dark_chocolate_10g",
    "exact_kelloggs_coco_pops_cereal_30g",
    "exact_imei_almond_powder_no_sugar_30g",
}


def test_exact_batch_042_loads_pxmart_official_label_macro_cards() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for item_id in BATCH_IDS:
        card = by_id[item_id]
        assert card["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_017.json"
        assert card["source_class"] == "official_retailer_product_page"
        assert str(card["source_url"]).startswith("https://pxbox.es.pxmart.com.tw/product/")
        assert card["macro_basis"] == "per_serving"
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"
        assert card["protein_g"] > 0
        assert card["carb_g"] > 0
        assert card["fat_g"] > 0


def test_exact_batch_042_resolves_with_visible_macros() -> None:
    cases = [
        (
            "unipresident ab yogurt drink strawberry",
            "exact_unipresident_ab_yogurt_drink_strawberry_300_6ml",
            209.0,
            {"protein_g": 8.1, "carb_g": 40.0, "fat_g": 1.8},
        ),
        (
            "anlene high protein calcium formula 200ml",
            "exact_anlene_high_protein_calcium_formula_200ml",
            145.0,
            {"protein_g": 15.0, "carb_g": 18.3, "fat_g": 1.5},
        ),
        (
            "lipton milk tea 250ml",
            "exact_lipton_milk_tea_250ml",
            109.5,
            {"protein_g": 1.0, "carb_g": 20.8, "fat_g": 2.5},
        ),
        (
            "kelloggs coco pops cereal 30g",
            "exact_kelloggs_coco_pops_cereal_30g",
            116.0,
            {"protein_g": 1.5, "carb_g": 25.5, "fat_g": 1.1},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
