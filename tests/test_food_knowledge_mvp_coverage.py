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
        "food_knowledge_can_decide_logged_or_draft",
        "live_food_search_ready",
    } <= set(coverage["not_claiming"])


def test_food_knowledge_mvp_map_covers_required_taiwan_ux_categories() -> None:
    coverage = _load_coverage_map()
    categories = {item["ux_category"]: item for item in coverage["coverage"]}

    assert set(categories) == {
        "茶葉蛋",
        "珍奶",
        "雞腿便當",
        "滷味",
        "麻辣燙",
        "麻辣臭豆腐",
        "鹽酥雞單品",
        "鹽酥雞籃子",
        "鹽酥雞列品項",
        "UX listed basket components",
        "超商 exact item",
        "松屋 exact item",
    }
    assert categories["茶葉蛋"]["coverage_type"] == "generic_anchor"
    assert categories["珍奶"]["coverage_type"] == "generic_anchor"
    assert categories["雞腿便當"]["coverage_type"] == "generic_anchor"
    assert categories["滷味"]["coverage_type"] == "semantic_only"
    assert categories["麻辣燙"]["coverage_type"] == "semantic_only"
    assert categories["麻辣臭豆腐"]["coverage_type"] == "generic_anchor"
    assert categories["鹽酥雞單品"]["coverage_type"] == "generic_anchor"
    assert categories["鹽酥雞籃子"]["coverage_type"] == "semantic_only"
    assert categories["鹽酥雞列品項"]["coverage_type"] == "listed_item_fanout"
    assert categories["UX listed basket components"]["coverage_type"] == "listed_item_components"
    assert categories["超商 exact item"]["coverage_type"] == "exact_item"
    assert categories["松屋 exact item"]["coverage_type"] == "exact_item"
    assert all(item["role"] == "evidence_support_only" for item in categories.values())
    assert not any(
        {"logged", "draft", "no_mutation", "mutation_authority", "decides_logged_or_draft"} & set(item)
        for item in categories.values()
    )


def test_food_knowledge_generic_anchor_expansion_keeps_mutation_authority_none() -> None:
    tea_egg = lookup_anchor_candidates(build_retrieval_intent("茶葉蛋"))
    boba = lookup_anchor_candidates(build_retrieval_intent("珍珠奶茶"))
    bento = lookup_anchor_candidates(build_retrieval_intent("雞腿便當"))
    spicy_stinky_tofu = lookup_anchor_candidates(build_retrieval_intent("麻辣臭豆腐"))
    salt_crispy_chicken = lookup_anchor_candidates(build_retrieval_intent("一份鹽酥雞"))

    for result, expected_name in (
        (tea_egg, "茶葉蛋"),
        (boba, "珍珠奶茶"),
        (bento, "雞腿便當"),
        (spicy_stinky_tofu, "麻辣臭豆腐"),
        (salt_crispy_chicken, "鹽酥雞"),
    ):
        assert result.defer_reason is None
        assert [candidate.canonical_name for candidate in result.candidates] == [expected_name]
        assert result.candidates[0].support_role == "lookup_support_only"
        assert result.candidates[0].truth_level == "anchor"
        assert result.candidates[0].source_posture == "generic_anchor_seed"
        assert result.mutation_authority == "none"

    assert "ask_sugar_level" in boba.candidates[0].followup_hints
    assert "ask_rice_portion" in bento.candidates[0].followup_hints
    assert "ask_broth_consumption" in spicy_stinky_tofu.candidates[0].followup_hints
    assert "ask_portion" in salt_crispy_chicken.candidates[0].followup_hints


def test_food_knowledge_semantic_only_and_listed_item_fanout_stay_non_authoritative() -> None:
    hotpot = lookup_anchor_candidates(build_retrieval_intent("我吃了麻辣燙"))
    luwei = lookup_anchor_candidates(build_retrieval_intent("我吃了滷味"))
    bare_salt_crispy_chicken = lookup_anchor_candidates(build_retrieval_intent("鹽酥雞"))
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
    salt_crispy_chicken_fanout = lookup_anchor_candidates(build_retrieval_intent("鹽酥雞，有甜不辣、米血、四季豆"))

    for result, expected_name in (
        (hotpot, "麻辣燙"),
        (luwei, "滷味"),
        (bare_salt_crispy_chicken, "鹽酥雞"),
    ):
        assert result.candidates == ()
        assert result.clarify_support is not None
        assert result.clarify_support.canonical_name == expected_name
        assert result.clarify_support.record_kind == "generic_semantic_only"
        assert result.clarify_support.clarify_required is True
        assert result.mutation_authority == "none"

    assert fanout.candidates == ()
    assert fanout.defer_reason == "listed_item_fanout_deferred"
    assert fanout.mutation_authority == "none"
    assert salt_crispy_chicken_fanout.candidates == ()
    assert salt_crispy_chicken_fanout.defer_reason == "listed_item_fanout_deferred"
    assert salt_crispy_chicken_fanout.mutation_authority == "none"


def test_food_knowledge_covers_v18_listed_basket_components_as_support_only() -> None:
    for item_name, expected_hints in (
        ("豆皮", {"luwei_component"}),
        ("王子麵", {"luwei_component", "fried_snack_component"}),
        ("雞排", {"fried_snack_component"}),
    ):
        result = lookup_anchor_candidates(
            RetrievalIntent(
                base_dish="listed basket",
                aliases=[],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[item_name],
                retrieval_goal="listed_item_lookup",
            )
        )

        assert result.defer_reason is None
        assert result.mutation_authority == "none"
        assert [candidate.canonical_name for candidate in result.candidates] == [item_name]
        candidate = result.candidates[0]
        assert candidate.dish_type == "listed_item"
        assert candidate.support_role == "lookup_support_only"
        assert candidate.truth_level == "anchor"
        assert set(candidate.semantic_hints) >= expected_hints


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


def test_food_knowledge_exact_brand_item_card_remains_support_only() -> None:
    result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="牛丼",
            aliases=["松屋特盛牛丼"],
            brand_hint="松屋",
            size_hint="特盛",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        )
    )

    assert result.defer_reason is None
    assert [candidate.title for candidate in result.candidates] == ["松屋特盛牛丼"]
    assert result.candidates[0].source == "local_exact_item_seed"
    assert result.candidates[0].support_only is True
