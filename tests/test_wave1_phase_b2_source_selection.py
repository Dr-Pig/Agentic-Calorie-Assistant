from __future__ import annotations

from app.nutrition.application.evidence_source_selection import select_evidence_source
from app.nutrition.application.retrieval_intent import build_retrieval_intent


def test_source_selection_uses_exact_db_first_for_exact_brand_intent_without_web_activation() -> None:
    selection = select_evidence_source(build_retrieval_intent("我吃了松屋特盛牛丼"))

    assert selection.source_path == "exact_db"
    assert selection.evidence_required == "exact_item_card"
    assert selection.web_allowed is False
    assert selection.reason == "exact_brand_intent_uses_local_exact_db_first"
    assert selection.decides_logged_or_draft is False


def test_source_selection_uses_generic_anchor_for_generic_intent_without_deciding_semantics() -> None:
    selection = select_evidence_source(build_retrieval_intent("我喝了一杯珍珠奶茶"))

    assert selection.source_path == "generic_anchor"
    assert selection.evidence_required == "generic_anchor_packet"
    assert selection.web_allowed is False
    assert selection.decides_logged_or_draft is False
    assert selection.product_policy_status == "source_selection_only"


def test_source_selection_routes_listed_item_luwei_to_fanout() -> None:
    selection = select_evidence_source(build_retrieval_intent("我吃了豆干、海帶、貢丸的滷味"))

    assert selection.source_path == "listed_item_fanout"
    assert selection.evidence_required == "generic_anchor_packet_per_listed_item"
    assert selection.web_allowed is False


def test_source_selection_routes_unknown_composition_to_ask_user_without_canonicalizing_policy() -> None:
    selection = select_evidence_source(build_retrieval_intent("我吃了滷味"))

    assert selection.source_path == "ask_user"
    assert selection.evidence_required == "clarify_support"
    assert selection.web_allowed is False
    assert selection.product_policy_status == "pending_or_provisional"
    assert selection.decides_logged_or_draft is False


def test_source_selection_keeps_query_only_read_only() -> None:
    selection = select_evidence_source(build_retrieval_intent("統一巧克力牛乳 400ml多少熱量？"))

    assert selection.source_path == "exact_db"
    assert selection.read_only is True
    assert selection.mutation_allowed is False
    assert selection.web_allowed is False
