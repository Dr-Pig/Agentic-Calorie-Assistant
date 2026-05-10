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
    }:
        card = by_id[item_id]
        assert card["source_class"] == "official_brand_chain_page"
        assert str(card["source_url"]).startswith("https://711go.7-11.com.tw/")
        assert card["reviewed_date"] == "2026-05-11"
        assert card["macro_basis"] == "per_serving"
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
    ]

    for query, item_id, kcal, macros in cases:
        docs = resolve_exact_item_fts(query, limit=1)

        assert docs
        assert docs[0]["item_id"] == item_id
        assert docs[0]["label_kcal"] == kcal
        assert docs[0]["label_macros"] == macros
        assert docs[0]["macro_completeness"] == "complete"
        assert docs[0]["provenance"]["source_url"].startswith("https://711go.7-11.com.tw/")
