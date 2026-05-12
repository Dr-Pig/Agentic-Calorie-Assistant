from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


EXACT_CARDS = Path("app/knowledge/exact_item_cards_tw.json")


def _cards() -> list[dict[str, object]]:
    payload = json.loads(EXACT_CARDS.read_text(encoding="utf-8-sig"))
    return [dict(card) for card in payload["cards"]]


def test_exact_label_lane_adds_official_label_macro_cards() -> None:
    by_id = {str(card["item_id"]): card for card in _cards()}

    for item_id in {
        "exact_chungabern_mini_scallion_pancake_90g",
        "exact_wangsteak_braised_lion_head_100g",
        "exact_yuhofang_sweet_potato_crisps_60g",
        "exact_7eleven_jiucai_he_135g",
        "exact_shaka_shrimp_cracker_original_30g",
        "exact_regent_braised_beef_noodle_pack",
        "exact_fresh123_mullet_roe_bite_10g",
        "exact_fresh123_japanese_simmered_abalone_100g",
        "exact_fresh123_railway_pork_chop_100g",
        "exact_fresh123_chickpea_vegetable_curry_100g",
        "exact_fresh123_tomato_beef_stew_100g",
        "exact_charlie_brown_white_sauce_smoked_chicken_bagel_90g",
        "exact_chungabern_scallion_pork_dumpling_18g",
        "exact_chungabern_cabbage_pork_dumpling_18g",
        "exact_kaz_sweet_potato_crisps_40g",
        "exact_aisin_crispy_fish_chunk_100g",
    }:
        card = by_id[item_id]
        assert card["source_class"] in {
            "official_brand_chain_page",
            "official_brand_page",
        }
        assert str(card["source_url"]).startswith("https://")
        assert card["reviewed_date"] in {"2026-05-11", "2026-05-12"}
        assert card["macro_basis"] in {"per_serving", "per_package"}
        assert card["macro_confidence"] == "high"
        assert card["macro_source_strength"] == "official_label"


def test_exact_label_lane_cards_resolve_with_visible_macros() -> None:
    cases = [
        (
            "\u8525\u963f\u4f2fMini\u4e09\u661f\u8525\u6cb9\u990c90\u516c\u514b",
            "exact_chungabern_mini_scallion_pancake_90g",
            219.6,
            {"protein_g": 7.3, "carb_g": 40.0, "fat_g": 3.3},
        ),
        (
            "\u738b\u54c1\u56b4\u9078\u91ac\u7168\u7d05\u71d2\u7345\u5b50\u982d100\u516c\u514b",
            "exact_wangsteak_braised_lion_head_100g",
            164.0,
            {"protein_g": 11.1, "carb_g": 7.4, "fat_g": 10.0},
        ),
        (
            "\u5fa1\u79be\u574a\u5730\u74dc\u916560\u516c\u514b",
            "exact_yuhofang_sweet_potato_crisps_60g",
            281.4,
            {"protein_g": 1.0, "carb_g": 44.4, "fat_g": 11.2},
        ),
        (
            "\u97ed\u83dc\u76d2135\u516c\u514b",
            "exact_7eleven_jiucai_he_135g",
            284.0,
            {"protein_g": 8.2, "carb_g": 39.8, "fat_g": 10.1},
        ),
        (
            "\u8766\u5580\u9bae\u8766\u9905\u539f\u547330\u516c\u514b",
            "exact_shaka_shrimp_cracker_original_30g",
            148.0,
            {"protein_g": 1.0, "carb_g": 19.9, "fat_g": 7.1},
        ),
        (
            "\u6676\u83ef\u7d05\u71d2\u725b\u8089\u9eb51\u5165",
            "exact_regent_braised_beef_noodle_pack",
            860.3,
            {"protein_g": 36.0, "carb_g": 68.4, "fat_g": 49.2},
        ),
        (
            "愛上新鮮一口吃烏魚子10公克",
            "exact_fresh123_mullet_roe_bite_10g",
            43.0,
            {"protein_g": 4.0, "carb_g": 0.1, "fat_g": 3.0},
        ),
        (
            "日式磯煮一口鮑100g",
            "exact_fresh123_japanese_simmered_abalone_100g",
            42.7,
            {"protein_g": 5.7, "carb_g": 4.3, "fat_g": 0.3},
        ),
        (
            "古早味鐵路排骨100g",
            "exact_fresh123_railway_pork_chop_100g",
            167.7,
            {"protein_g": 18.5, "carb_g": 8.8, "fat_g": 6.5},
        ),
        (
            "鷹嘴豆野蔬咖哩100g",
            "exact_fresh123_chickpea_vegetable_curry_100g",
            168.7,
            {"protein_g": 10.7, "carb_g": 18.2, "fat_g": 5.9},
        ),
        (
            "愛上新鮮番茄燉牛肉100公克",
            "exact_fresh123_tomato_beef_stew_100g",
            161.3,
            {"protein_g": 13.8, "carb_g": 1.1, "fat_g": 11.3},
        ),
        (
            "查理布朗白醬燻雞水嫩貝果90公克",
            "exact_charlie_brown_white_sauce_smoked_chicken_bagel_90g",
            203.4,
            {"protein_g": 6.6, "carb_g": 31.2, "fat_g": 5.8},
        ),
        (
            "蔥阿伯青蔥豬肉水餃18g",
            "exact_chungabern_scallion_pork_dumpling_18g",
            34.1,
            {"protein_g": 1.5, "carb_g": 1.7, "fat_g": 1.0},
        ),
        (
            "蔥阿伯高麗菜豬肉水餃18g",
            "exact_chungabern_cabbage_pork_dumpling_18g",
            34.3,
            {"protein_g": 1.5, "carb_g": 4.6, "fat_g": 1.1},
        ),
        (
            "卡滋雙色番薯脆片40公克",
            "exact_kaz_sweet_potato_crisps_40g",
            198.0,
            {"protein_g": 1.2, "carb_g": 27.2, "fat_g": 9.4},
        ),
        (
            "香酥魚塊100g",
            "exact_aisin_crispy_fish_chunk_100g",
            192.0,
            {"protein_g": 17.5, "carb_g": 11.6, "fat_g": 8.4},
        ),
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
        assert docs[0]["provenance"]["source_url"].startswith("https://")
