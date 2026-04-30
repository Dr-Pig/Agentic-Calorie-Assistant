from __future__ import annotations

import pytest

from app.providers.tavily_adapter import TavilyAdapter


@pytest.mark.asyncio
async def test_search_merges_extracted_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = TavilyAdapter()
    monkeypatch.setattr(adapter, "_is_configured", lambda: True)

    async def _stub_candidates(query: str, *, max_results: int = 5):
        assert query == "coco pearl milk tea"
        return [
            {
                "title": "CoCo pearl milk tea",
                "url": "https://coco.example/menu",
                "snippet": "official menu",
                "officialness": "official",
            }
        ]

    async def _stub_extract(*, urls: list[str], query: str):
        assert urls == ["https://coco.example/menu"]
        assert query == "coco pearl milk tea"
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
                "raw_content": "per cup 400 kcal",
            }
        ]

    monkeypatch.setattr(adapter, "search_candidates", _stub_candidates)
    monkeypatch.setattr(adapter, "extract_structured_page_data", _stub_extract)

    rows = await adapter.search("coco pearl milk tea")
    assert len(rows) == 1
    row = rows[0]
    assert row["source_type"] == "official"
    assert row["serving_basis"] == "per_cup"
    assert row["brand_detected"] == "coco"
    assert row["customization_slots_present"] == ["size", "sugar"]


def test_extract_helpers_classify_fields() -> None:
    adapter = TavilyAdapter()
    raw = "per cup 400 kcal sugar ice protein 3g"
    assert adapter._infer_serving_basis(raw) == "per_cup"
    assert "sugar" in adapter._detect_customization_slots(raw)
    assert "ice" in adapter._detect_customization_slots(raw)
    assert "kcal" in adapter._detect_nutrition_fields(raw)
    assert adapter._detect_channel("menu page") == "handmade_foodservice"
