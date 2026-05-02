from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.exact_item_card_lookup import lookup_exact_item_card_candidates
from app.nutrition.application.retrieval_intent import RetrievalIntent, build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates


ROOT = Path(__file__).resolve().parents[1]
COVERAGE_MAP_PATH = ROOT / "docs" / "quality" / "food_knowledge_mvp_coverage_map.json"


def _load_coverage_map() -> dict[str, object]:
    return json.loads(COVERAGE_MAP_PATH.read_text(encoding="utf-8"))


def test_food_knowledge_mvp_map_declares_evidence_support_boundary() -> None:
    coverage = _load_coverage_map()

    assert coverage["coverage_id"] == "food_knowledge_mvp_deterministic_v1"
    assert coverage["scope"] == "local_deterministic_evidence_support"
    assert coverage["truth_owner"] == "none"
    assert coverage["mutation_authority"] == "none"
    assert coverage["live_llm_required"] is False
    assert coverage["web_tavily_required"] is False
    assert coverage["schema_migration_required"] is False
    assert {
        "food_knowledge_is_product_truth",
        "food_knowledge_can_authorize_mutation",
        "food_knowledge_can_update_ledger",
    } <= set(coverage["not_claiming"])


def test_food_knowledge_mvp_map_covers_required_taiwan_ux_categories() -> None:
    coverage = _load_coverage_map()
    categories = {item["ux_category"]: item for item in coverage["coverage"]}

    assert set(categories) == {
        "滷味",
        "麻辣燙",
        "便當",
        "珍奶",
        "炸醬麵",
        "牛丼",
        "超商 exact item",
    }
    assert categories["滷味"]["coverage_type"] == "semantic_only"
    assert categories["麻辣燙"]["coverage_type"] == "semantic_only"
    assert categories["便當"]["coverage_type"] == "generic_anchor"
    assert categories["珍奶"]["coverage_type"] == "generic_anchor"
    assert categories["炸醬麵"]["coverage_type"] == "generic_anchor"
    assert categories["牛丼"]["coverage_type"] == "generic_anchor"
    assert categories["超商 exact item"]["coverage_type"] == "exact_item"
    assert all(item["role"] == "evidence_support_only" for item in categories.values())


def test_food_knowledge_generic_anchor_expansion_keeps_mutation_authority_none() -> None:
    zhajiangmian = lookup_anchor_candidates(build_retrieval_intent("我吃了炸醬麵"))
    gyudon = lookup_anchor_candidates(build_retrieval_intent("我吃了牛丼"))

    assert zhajiangmian.defer_reason is None
    assert [candidate.canonical_name for candidate in zhajiangmian.candidates] == ["炸醬麵"]
    assert zhajiangmian.candidates[0].support_role == "lookup_support_only"
    assert zhajiangmian.candidates[0].truth_level == "anchor"
    assert zhajiangmian.candidates[0].source_posture == "generic_anchor_seed"
    assert "ask_sauce_amount" in zhajiangmian.candidates[0].followup_hints
    assert zhajiangmian.mutation_authority == "none"

    assert gyudon.defer_reason is None
    assert [candidate.canonical_name for candidate in gyudon.candidates] == ["牛丼"]
    assert gyudon.candidates[0].support_role == "lookup_support_only"
    assert gyudon.candidates[0].truth_level == "anchor"
    assert "ask_bowl_size" in gyudon.candidates[0].followup_hints
    assert gyudon.mutation_authority == "none"


def test_food_knowledge_semantic_only_and_listed_item_fanout_stay_non_authoritative() -> None:
    hotpot = lookup_anchor_candidates(build_retrieval_intent("我吃了麻辣燙"))
    fanout = lookup_anchor_candidates(
        RetrievalIntent(
            base_dish="滷味",
            aliases=[],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=["豆干", "海帶", "貢丸"],
            retrieval_goal="listed_item_lookup",
        )
    )

    assert hotpot.candidates == ()
    assert hotpot.clarify_support is not None
    assert hotpot.clarify_support.record_kind == "generic_semantic_only"
    assert hotpot.clarify_support.clarify_required is True
    assert hotpot.mutation_authority == "none"

    assert fanout.candidates == ()
    assert fanout.defer_reason == "listed_item_fanout_deferred"
    assert fanout.mutation_authority == "none"


def test_food_knowledge_exact_convenience_item_card_remains_support_only() -> None:
    result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="巧克力牛乳",
            aliases=["統一巧克力牛乳 400ml"],
            brand_hint="統一",
            size_hint="400ml",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        )
    )

    assert result.defer_reason is None
    assert [candidate.title for candidate in result.candidates] == ["統一巧克力牛乳(400ml)"]
    assert result.candidates[0].source == "local_exact_item_seed"
    assert result.candidates[0].support_only is True
