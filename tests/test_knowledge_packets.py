from __future__ import annotations

from app.agent.knowledge_packets import search_local_knowledge


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
