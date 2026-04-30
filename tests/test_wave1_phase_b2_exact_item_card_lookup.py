from __future__ import annotations

from app.nutrition.application.exact_item_card_lookup import lookup_exact_item_card_candidates
from app.nutrition.application.retrieval_intent import RetrievalIntent, build_retrieval_intent


class _FakeEvidenceStore:
    def load_small_anchor_records(self) -> list[dict[str, object]]:
        return []

    def load_exact_item_card_records(self) -> list[dict[str, object]]:
        return [
            {
                "item_id": "exact_test_food_large",
                "title": "Test Brand Food Large",
                "aliases": ["Test Brand Food Large"],
                "brand": "Test Brand",
                "serving_basis": "large serving",
                "kcal": 123,
            }
        ]


def test_exact_item_lookup_accepts_injected_evidence_store_port() -> None:
    result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="Food",
            aliases=["Test Brand Food Large"],
            brand_hint="Test Brand",
            size_hint="Large",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        ),
        evidence_store=_FakeEvidenceStore(),
    )

    assert result.defer_reason is None
    assert [candidate.item_id for candidate in result.candidates] == ["exact_test_food_large"]
    assert result.candidates[0].kcal == 123


def test_exact_item_lookup_resolves_unified_chocolate_milk_400ml() -> None:
    result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="\u5de7\u514b\u529b\u725b\u4e73",
            aliases=["\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73 400ml"],
            brand_hint="\u7d71\u4e00",
            size_hint="400ml",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        )
    )

    assert result.defer_reason is None
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.title == "\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73(400ml)"
    assert candidate.match_path == "exact_title"
    assert candidate.source == "local_exact_item_seed"
    assert candidate.support_only is True


def test_exact_item_lookup_prefers_iced_starbucks_latte_over_hot_sibling() -> None:
    result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))

    assert result.defer_reason is None
    assert [candidate.title for candidate in result.candidates] == [
        "\u661f\u5df4\u514b \u90a3\u5802(\u51b0) \u5927\u676f"
    ]


def test_exact_item_lookup_matches_sushiro_alias_with_quotes_and_possessive() -> None:
    result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="\u7126\u7cd6\u9bae\u9b5a",
            aliases=["\u722d\u9bae\u8ff4\u8f49\u58fd\u53f8\u7684\u300c\u7126\u7cd6\u9bae\u9b5a\u300d\uff08\u5169\u8cab\uff09"],
            brand_hint="\u722d\u9bae",
            size_hint="\u5169\u8cab",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        )
    )

    assert result.defer_reason is None
    assert len(result.candidates) == 1
    assert result.candidates[0].title == "\u722d\u9bae \u7126\u7cd6\u9bae\u9b5a(\u5169\u8cab)"
    assert result.candidates[0].match_path == "exact_alias"


def test_exact_item_lookup_resolves_matsuya_tokumori_gyudon() -> None:
    result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="\u725b\u4e3c",
            aliases=["\u677e\u5c4b\u7279\u76db\u725b\u4e3c"],
            brand_hint="\u677e\u5c4b",
            size_hint="\u7279\u76db",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        )
    )

    assert result.defer_reason is None
    assert [candidate.title for candidate in result.candidates] == ["\u677e\u5c4b\u7279\u76db\u725b\u4e3c"]


def test_exact_item_lookup_query_only_brand_case_stays_support_only() -> None:
    result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="\u5de7\u514b\u529b\u725b\u4e73",
            aliases=["\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73 400ml"],
            brand_hint="\u7d71\u4e00",
            size_hint="400ml",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="query_only_answer",
        )
    )

    assert result.defer_reason is None
    assert len(result.candidates) == 1
    assert result.candidates[0].support_only is True


def test_exact_item_lookup_rejects_generic_anchor_goal() -> None:
    result = lookup_exact_item_card_candidates(build_retrieval_intent("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336"))

    assert result.candidates == ()
    assert result.defer_reason == "unsupported_retrieval_goal"


def test_exact_item_lookup_brand_or_size_mismatch_filters_all_candidates() -> None:
    result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="\u90a3\u5802",
            aliases=["\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"],
            brand_hint="\u661f\u5df4\u514b",
            size_hint="\u4e2d\u676f",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        )
    )

    assert result.candidates == ()
    assert result.defer_reason == "metadata_filtered_all_candidates"


def test_exact_item_lookup_returns_no_exact_item_match_when_nothing_matches() -> None:
    result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="\u8d85\u7d1a\u62b9\u8336\u6b50\u857e",
            aliases=["\u8d85\u7d1a\u62b9\u8336\u6b50\u857e"],
            brand_hint="\u7d71\u4e00",
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        )
    )

    assert result.candidates == ()
    assert result.defer_reason == "no_exact_item_match"
