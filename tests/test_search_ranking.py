from app.application.evidence_assembly import (
    build_search_query as _build_search_query,
    search_result_quality as _search_result_quality,
)


def test_search_result_quality_penalizes_calculator_pages_against_nutrition_pages() -> None:
    quality, results = _search_result_quality(
        "\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73 400ml \u71df\u990a\u6a19\u793a",
        [
            {
                "title": "Convert 400 Milliliters to Cups",
                "url": "https://www.calculateme.com/volume/milliliters/to-cups/400",
                "snippet": "400 milliliters is equal to about 1.69 cups.",
            },
            {
                "title": "\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73 \u71df\u990a\u6a19\u793a",
                "url": "https://www.uni-president.com.tw/product/chocolate-milk",
                "snippet": "\u71b1\u91cf 340 kcal\uff0c\u86cb\u767d\u8cea 12 \u516c\u514b\u3002",
            },
        ],
    )

    assert quality == "high"
    assert results
    assert "uni-president" in results[0]["url"]


def test_search_result_quality_rejects_sibling_variant_when_only_domain_overlaps() -> None:
    quality, results = _search_result_quality(
        "pocari sweat 580ml 熱量 營養",
        [
            {
                "title": "ION WATER 580ml",
                "url": "https://www.pocari.tw/ion-water",
                "snippet": "electrolyte drink product page",
            },
            {
                "title": "Pocari Sweat 580ml Nutrition Facts",
                "url": "https://www.pocari.com.tw/product/580ml",
                "snippet": "calories and nutrition facts",
            },
        ],
    )

    assert quality == "high"
    assert results
    assert "sweat" in results[0]["title"].lower()


def test_build_search_query_adds_ramen_specific_terms() -> None:
    query = _build_search_query(
        "一蘭拉麵",
        user_input="一蘭拉麵",
        risk_packet={"risk_flags": ["ramen"]},
        retrieved_knowledge=[],
    )

    assert "一蘭拉麵" in query
    assert "熱量" in query
    assert "營養" in query
    assert "湯" in query
    assert "湯" in query
