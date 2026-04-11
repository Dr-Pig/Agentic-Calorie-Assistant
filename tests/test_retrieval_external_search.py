import asyncio

from app.usecases.evidence.retrieval import EvidenceRetrieval
from app.application.evidence_normalizer import source_class_for_item, source_tier_for_item
from app.application.evidence_assembly import (
    build_reasoning_state,
    execute_primary_tool_request,
    extract_search_evidence_blocks,
)
from app.schemas import EstimateRequest, TurnIntentResult


def test_extract_search_evidence_blocks_marks_official_identity_hits() -> None:
    blocks = extract_search_evidence_blocks(
        [
            {
                "title": "Pocari Sweat 580ml Nutrition Facts",
                "url": "https://www.pocari.com.tw/product/580ml",
                "snippet": "official calories and nutrition facts",
            },
            {
                "title": "Sports Drink Review",
                "url": "https://example.com/review",
                "snippet": "generic review",
            },
        ],
        query="pocari sweat 580ml nutrition",
        identity_target="pocari sweat 580ml",
    )

    assert blocks[0]["source_class"] == "web_search_official"
    assert blocks[0]["identity_confidence"] == "high"
    assert blocks[0]["source_officialness"] == "official"
    assert blocks[1]["source_class"] == "web_search_nonexact"


def test_evidence_normalizer_classifies_source_tier_from_source_class() -> None:
    assert source_class_for_item({"source_type": "web_search_official"}) == "web_search_official"
    assert source_tier_for_item({"source_class": "exact_item_db"}) == "tier_1_exact_verified"
    assert source_tier_for_item({"source_class": "web_search_official"}) == "tier_4_web_nonexact"
    assert source_tier_for_item({"source_class": "meal_template_db"}) == "tier_3_anchor_prior"
    assert source_tier_for_item({}) == "tier_5_model_context"


def test_build_reasoning_state_flags_template_only_and_brand_detection() -> None:
    state = build_reasoning_state(
        user_input="我吃吉野家牛丼",
        selected_evidence=[
            {
                "title": "牛丼模板",
                "source_class": "meal_template_db",
                "retrieval_lane": "template_lane",
                "identity_confidence": "low",
            }
        ],
        partial_grounding={"missing_components": [{"name": "份量", "importance": "high"}]},
        used_search=False,
        search_attempt_count=0,
    )

    assert state["brand_detected"] is True
    assert state["template_lane_count"] == 1
    assert state["anchor_lane_count"] == 0
    assert state["exact_lane_count"] == 0
    assert state["why_current_evidence_is_insufficient"] == "only template scaffold evidence available"
    assert state["missing_high_impact_slots"] == ["份量"]


def test_execute_primary_tool_request_returns_quality_meta_for_external_search() -> None:
    class FakeSearch:
        async def search(self, query, limit=5):
            return [
                {
                    "title": "Pocari Sweat 580ml Nutrition Facts",
                    "url": "https://www.pocari.com.tw/product/580ml",
                    "snippet": "official calories and nutrition facts",
                },
                {
                    "title": "ION WATER 580ml",
                    "url": "https://www.pocari.tw/ion-water",
                    "snippet": "official product page",
                },
            ]

    async def _run():
        executed = []
        results, search_sources, query, quality = await execute_primary_tool_request(
            tool_request="search_official_nutrition",
            tool_reason="Need official product evidence.",
            retrieval_query="pocari sweat 580ml nutrition",
            resolved_query="pocari sweat 580ml nutrition",
            planner_result=TurnIntentResult(normalized_user_input="pocari sweat 580ml", input_signals={"foods": ["pocari sweat 580ml"]}),
            request=EstimateRequest(text="pocari sweat 580ml", allow_search=True),
            search_adapter=FakeSearch(),
            executed_tool_calls=executed,
            build_tool_result=lambda **kwargs: kwargs,
        )
        return results, search_sources, query, quality, executed

    results, search_sources, query, quality, executed = asyncio.run(_run())

    assert query is not None
    assert results
    assert search_sources
    assert quality is not None
    assert quality["extractor_used"] is True
    assert quality["observation"]["official_hit_count"] >= 1
    assert quality["quality"] in {"medium", "high"}
    assert executed[0]["tool_name"] == "search_official_nutrition"


def test_evidence_retrieval_uses_branded_chain_fast_path_before_web_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.usecases.evidence.retrieval.resolve_exact_item",
        lambda query, limit=4: [],
    )
    monkeypatch.setattr(
        "app.usecases.evidence.retrieval.resolve_chain_item",
        lambda query, limit=4: [
            {
                "title": "Starbucks Iced Latte",
                "brand": "Starbucks",
                "source_class": "exact_item_db",
                "evidence_role": "exact_truth",
                "identity_confidence": "high",
                "kcal": 120,
            }
        ],
    )
    monkeypatch.setattr(
        "app.usecases.evidence.retrieval.resolve_ingredient_anchors",
        lambda foods, portion_hints=None, limit=4: [],
    )

    retrieval = EvidenceRetrieval()
    result = retrieval.execute(
        retrieval_query="Starbucks iced latte",
        evidence_strategy="local_then_exact",
        input_signals={"foods": ["iced latte"], "brands": ["Starbucks"], "portion_clues": []},
        user_input="Starbucks iced latte",
    )

    assert result.retrieval_triggered is True
    assert result.filtered_knowledge
    assert result.filtered_knowledge[0]["title"] == "Starbucks Iced Latte"
    assert result.filtered_knowledge[0]["source_class"] == "exact_item_db"
    assert result.filtered_knowledge[0]["tool_name"] == "resolve_exact_item"
    assert result.filtered_knowledge[0]["retrieval_lane"] == "exact_lane"
    assert result.executed_tool_calls[0]["tool_name"] == "resolve_exact_item"
    assert result.executed_tool_calls[0]["quality"] == "high"
