from app.application.evidence_assembly import search_result_quality as _search_result_quality


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
    assert len(results) == 2


def test_search_result_quality_rejects_sibling_variant_when_only_domain_overlaps() -> None:
    quality, results = _search_result_quality(
        "pocari sweat 580ml \u71df\u990a \u71b1\u91cf",
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
    assert len(results) == 2


def test_search_result_quality_is_only_medium_when_identity_or_official_signal_is_partial() -> None:
    quality, results = _search_result_quality(
        "吉野家 牛丼 營養",
        [
            {
                "title": "吉野家 門市資訊",
                "url": "https://www.yoshinoya.com.tw/store",
                "snippet": "official site",
            },
            {
                "title": "牛丼熱量整理",
                "url": "https://example.com/beef-bowl",
                "snippet": "generic nutrition blog",
            },
        ],
    )

    assert quality == "medium"
    assert len(results) == 2
