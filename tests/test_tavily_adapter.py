from __future__ import annotations

import pytest

from app.nutrition.infrastructure.web_search.tavily_adapter import TavilyAdapter


@pytest.mark.asyncio
async def test_search_merges_extracted_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = TavilyAdapter()
    monkeypatch.setattr(adapter, "_is_configured", lambda: True)

    async def _stub_candidates(query: str, *, max_results: int = 5, include_raw_content: bool = False):
        assert query == "珍珠奶茶"
        return [
            {
                "title": "CoCo 珍珠奶茶",
                "url": "https://coco.example/menu",
                "snippet": "菜單頁",
                "officialness": "official",
            }
        ]

    async def _stub_extract(*, urls: list[str], query: str, chunks_per_source: int = 3, extract_depth: str = "advanced"):
        assert urls == ["https://coco.example/menu"]
        return [
            {
                "url": "https://coco.example/menu",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_cup",
                "identity_confidence": "medium",
                "applicability_confidence": "medium",
                "customization_slots_present": ["size", "sugar"],
                "brand_detected": "coco",
                "channel_detected": "handmade_foodservice",
                "nutrition_fields_present": ["kcal"],
                "evidence_tier_candidate": "near-exact",
                "applicability_notes": "contains drink customization cues",
                "raw_content": "每杯 熱量",
            }
        ]

    monkeypatch.setattr(adapter, "search_candidates", _stub_candidates)
    monkeypatch.setattr(adapter, "extract_structured_page_data", _stub_extract)

    rows = await adapter.search("珍珠奶茶")
    assert len(rows) == 1
    row = rows[0]
    assert row["source_type"] == "official"
    assert row["serving_basis"] == "per_cup"
    assert row["brand_detected"] == "coco"
    assert row["customization_slots_present"] == ["size", "sugar"]


def test_extract_helpers_classify_fields() -> None:
    adapter = TavilyAdapter()
    raw = "每杯 熱量 400 kcal 半糖 少冰 蛋白質 3g"
    assert adapter._infer_serving_basis(raw) == "per_cup"
    assert "sugar" in adapter._detect_customization_slots(raw)
    assert "ice" in adapter._detect_customization_slots(raw)
    assert "kcal" in adapter._detect_nutrition_fields(raw)
    assert adapter._detect_channel("手搖飲 menu") == "handmade_foodservice"
