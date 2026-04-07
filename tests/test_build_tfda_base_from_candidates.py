from __future__ import annotations

from scripts.build_tfda_base_from_candidates import (
    _build_aliases,
    _build_row_groups,
    _build_row_index,
    _map_tfda_candidate,
    _match_row,
)


def test_match_row_uses_category_description_variant_and_kcal() -> None:
    row = {
        "整合編號": "A0100101",
        "食品分類": "穀物類",
        "樣品名稱": "大麥仁",
        "內容物描述": "樣品狀態:生,已去殼; 前處理描述:混合均勻磨碎",
        "修正熱量(kcal)": 346.6895,
    }
    row_index = _build_row_index([row])
    row_groups = _build_row_groups([row])
    candidate = {
        "id": "tfda_00001",
        "category": "穀物類",
        "title": "樣品狀態:生,已去殼; 前處理描述:混合均勻磨碎",
        "variant": "大麥仁",
        "kcal": 346.7,
    }
    matched = _match_row(candidate, row_index, row_groups)
    assert matched == row


def test_build_aliases_combines_variant_synonyms_and_description_tokens() -> None:
    aliases = _build_aliases(
        {
            "brand": "小薏仁,洋薏仁,珍珠薏仁",
            "title": "樣品狀態:生,已去殼; 前處理描述:混合均勻磨碎",
            "variant": "大麥仁",
        },
        {
            "樣品名稱": "大麥仁",
            "俗名": "小薏仁,洋薏仁,珍珠薏仁",
        },
    )
    assert "大麥仁" in aliases
    assert "小薏仁" in aliases
    assert "洋薏仁" in aliases


def test_map_tfda_candidate_emits_runtime_macro_schema() -> None:
    candidate = {
        "id": "tfda_00001",
        "brand": "小薏仁,洋薏仁,珍珠薏仁",
        "title": "樣品狀態:生,已去殼; 前處理描述:混合均勻磨碎",
        "variant": "大麥仁",
        "category": "穀物類",
        "kcal": 346.7,
    }
    row = {
        "整合編號": "A0100101",
        "食品分類": "穀物類",
        "樣品名稱": "大麥仁",
        "內容物描述": "樣品狀態:生,已去殼; 前處理描述:混合均勻磨碎",
        "俗名": "小薏仁,洋薏仁,珍珠薏仁",
        "修正熱量(kcal)": 346.6895,
        "粗蛋白(g)": 8.5578,
        "粗脂肪(g)": 1.5935,
        "總碳水化合物(g)": 77.1418,
        "鈉(mg)": 3.0,
        "廢棄率(%)": 0,
    }
    mapped = _map_tfda_candidate(candidate, row)
    assert mapped["title"] == "大麥仁"
    assert mapped["serving_basis"]["label"] == "100 g edible portion"
    assert mapped["nutrition"]["protein_g"] == 8.5578
    assert mapped["nutrition"]["carb_g"] == 77.1418
    assert mapped["nutrition"]["fat_g"] == 1.5935
    assert mapped["nutrition"]["sodium_mg"] == 3.0
    assert mapped["source_type"] == "government_nutrition"
