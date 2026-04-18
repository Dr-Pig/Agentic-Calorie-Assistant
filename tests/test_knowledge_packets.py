from __future__ import annotations

from app.agent.exact_item_packets import build_exact_item_lane_packet, resolve_exact_item
from app.agent.local_knowledge_selector import search_local_knowledge


def test_search_local_knowledge_marks_exact_item_high_confidence_for_true_alias_match() -> None:
    docs = search_local_knowledge(
        "統一巧克力牛乳400ml",
        user_input="統一巧克力牛乳400ml",
        risk_flags=[],
        limit=5,
    )

    top = docs[0]
    assert top["title"] == "統一巧克力牛乳(400ml)"
    assert top["evidence_role"] == "exact_truth"
    assert top["match_confidence"] == "high"
    assert top["match_path"] in {"exact_alias", "exact_title", "brand_plus_alias_partial"}


def test_search_local_knowledge_does_not_promote_brand_only_drink_match_to_high_confidence() -> None:
    docs = search_local_knowledge(
        "五十嵐珍珠奶茶",
        user_input="五十嵐珍珠奶茶",
        risk_flags=["drink_custom"],
        limit=5,
    )

    exact_hits = [doc for doc in docs if doc.get("evidence_role") == "exact_truth"]
    assert not exact_hits
    assert any(doc.get("evidence_role") in {"ingredient_anchor", "dish_prior"} for doc in docs)


def test_resolve_exact_item_uses_exact_only_lane_for_711_sandwich_query() -> None:
    docs = resolve_exact_item("7-11 燻雞總匯鮮蔬三明治", limit=5)

    banned_titles = {"F6511022水手牌小林煎餅專用粉", "新東陽辣味豬肉乾110G(貿易)"}
    assert all(doc.get("retrieval_lane") == "exact_lane" for doc in docs)
    assert all(doc.get("title") not in banned_titles for doc in docs)
    assert all(doc.get("query_alignment") in {"exact_title", "exact_alias", "partial_title"} for doc in docs)


def test_exact_item_lane_packet_uses_brand_context_before_fallback(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_resolve_exact_item(
        query: str,
        *,
        active_brand_context: str | None = None,
        required_slots: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, object]]:
        seen["query"] = query
        seen["active_brand_context"] = active_brand_context
        seen["required_slots"] = required_slots
        seen["limit"] = limit
        return [
            {
                "title": "吉野家牛丼",
                "brand": "吉野家",
                "source_class": "exact_item_db",
                "evidence_role": "exact_truth",
                "retrieval_lane": "exact_lane",
                "identity_confidence": "high",
            }
        ]

    monkeypatch.setattr("app.agent.exact_item_packets.resolve_exact_item", fake_resolve_exact_item)

    packet = build_exact_item_lane_packet("牛丼", active_brand_context="吉野家", limit=3)

    assert seen["query"] == "牛丼"
    assert seen["active_brand_context"] == "吉野家"
    assert seen["limit"] == 3
    assert packet["local_exact_truth_present"] is True
    assert packet["should_skip_web_fallback"] is True
    assert packet["exact_lane_count"] == 1


def test_resolve_exact_item_uses_exact_only_lane_for_711_oyakodon_query() -> None:
    docs = resolve_exact_item("7-11 一鍋燒滑蛋嫩雞親子丼", limit=5)

    banned_titles = {"F6511022水手牌小林煎餅專用粉", "新東陽辣味豬肉乾110G(貿易)"}
    assert all(doc.get("retrieval_lane") == "exact_lane" for doc in docs)
    assert all(doc.get("title") not in banned_titles for doc in docs)
    assert all(doc.get("query_alignment") in {"exact_title", "exact_alias", "partial_title"} for doc in docs)
