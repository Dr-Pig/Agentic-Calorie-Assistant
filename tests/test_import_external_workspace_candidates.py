from __future__ import annotations

from scripts.import_external_workspace_candidates import _build_aliases, _looks_mojibake, _map_base_record, _map_exact_record


def test_looks_mojibake_rejects_garbled_text() -> None:
    assert _looks_mojibake("??蝝??") is True


def test_looks_mojibake_rejects_private_use_text_even_with_cjk() -> None:
    assert _looks_mojibake("五十嵐珍珠奶茶") is True


def test_looks_mojibake_accepts_readable_cjk_text() -> None:
    assert _looks_mojibake("五十嵐四季春珍波椰") is False


def test_looks_mojibake_accepts_readable_ascii_text() -> None:
    assert _looks_mojibake("Starbucks Latte") is False


def test_map_exact_record_skips_mojibake_records() -> None:
    mapped = _map_exact_record(
        {
            "brand": "7-ELEVEN CITY CAFE",
            "title": "??蝝??",
            "variant": "",
            "category": "drink",
            "kcal": 248,
            "source_url": "https://example.com",
            "source_type": "curated_reference",
            "confidence": "medium",
            "notes": "",
            "serving_basis": {"label": "1 cup"},
        }
    )
    assert mapped is None


def test_map_exact_record_accepts_readable_records() -> None:
    mapped = _map_exact_record(
        {
            "brand": "Starbucks",
            "title": "Latte",
            "variant": "Tall",
            "category": "beverage",
            "kcal": 190,
            "source_url": "https://example.com",
            "source_type": "official_drink_product_page",
            "confidence": "high",
            "notes": "",
            "serving_basis": {"label": "Tall"},
        }
    )
    assert mapped is not None
    assert mapped["brand"] == "Starbucks"
    assert mapped["title"] == "Latte Tall"
    assert mapped["evidence_role"] == "exact_truth"


def test_map_base_record_requires_macro_fields() -> None:
    mapped = _map_base_record(
        {
            "brand": "TFDA",
            "title": "White Rice",
            "category": "rice",
            "kcal": 183,
            "source_url": "https://example.com",
            "source_name": "TFDA",
            "confidence": "high",
            "serving_basis": {"label": "100 g", "unit_type": "g", "amount": 100},
        }
    )
    assert mapped is None


def test_build_aliases_adds_brand_short_name_and_strips_package_prefix() -> None:
    aliases = _build_aliases(
        title="0.33公升*6罐裝金牌FREE啤酒風味飲料 朝沁百香多",
        variant="",
        brand="臺灣菸酒股份有限公司",
    )
    assert "台酒" in aliases
    assert "臺酒 金牌FREE啤酒風味飲料 朝沁百香多" in aliases or "台酒 金牌FREE啤酒風味飲料 朝沁百香多" in aliases
    assert any("金牌FREE啤酒風味飲料 朝沁百香多" == alias for alias in aliases)


def test_build_aliases_adds_familymart_short_brand_alias() -> None:
    aliases = _build_aliases(
        title="蘋果紅茶PET535ML",
        variant="",
        brand="全家便利商店股份有限公司",
    )
    assert "全家" in aliases
    assert "全家 蘋果紅茶PET535ML" in aliases
