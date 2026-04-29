from __future__ import annotations

from app.nutrition.application.b2_candidate_packetizer import add_hard_recheck_metadata
from app.nutrition.application.b2_packet_consumption import consume_rechecked_packets
from app.nutrition.application.retrieval_intent import RetrievalIntent
from app.nutrition.application.web_search_packetizer import (
    build_web_search_candidate_packet,
    build_web_search_candidate_packets,
)


_FORBIDDEN_PACKET_FIELDS = {
    "kcal_range",
    "likely_kcal",
    "final_truth",
    "exactness_posture",
    "primary_source",
}


def _intent(
    *,
    base_dish: str,
    alias: str,
    brand_hint: str | None = None,
    size_hint: str | None = None,
) -> RetrievalIntent:
    return RetrievalIntent(
        base_dish=base_dish,
        aliases=[alias],
        brand_hint=brand_hint,
        size_hint=size_hint,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )


def _candidate(
    *,
    candidate_id: str,
    title: str,
    url: str,
    query: str,
    brand_detected: str = "",
    officialness_hint: str = "official",
    source_quality_hint: str = "high",
    snippet: str = "official menu result",
    score: float = 0.93,
    serving_basis_candidate: str = "per_cup",
    identity_confidence: str = "medium",
    applicability_confidence: str = "medium",
    raw_ref: str = "raw/tavily/test.json#0",
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "source_type": "web_search",
        "source_url": url,
        "source_domain": "example.test",
        "source_title": title,
        "snippet": snippet,
        "query": query,
        "identity_target": query,
        "score": score,
        "source_quality_hint": source_quality_hint,
        "officialness_hint": officialness_hint,
        "brand_detected": brand_detected,
        "channel_detected": "handmade_foodservice",
        "serving_basis_candidate": serving_basis_candidate,
        "nutrition_fields_present": ["kcal"],
        "customization_slots_present": ["size"],
        "identity_confidence": identity_confidence,
        "applicability_confidence": applicability_confidence,
        "applicability_notes": "fixture candidate",
        "raw_ref": raw_ref,
    }


def test_exact_same_item_official_candidate_is_accepted_for_exact_evidence_usage() -> None:
    intent = _intent(
        base_dish="珍珠紅茶拿鐵",
        alias="迷客夏珍珠紅茶拿鐵",
        brand_hint="迷客夏",
    )
    candidate = _candidate(
        candidate_id="web_search_candidate:milksha_exact",
        title="迷客夏 珍珠紅茶拿鐵",
        url="https://milksha.example/menu/pearl-black-tea-latte",
        query="迷客夏珍珠紅茶拿鐵",
        brand_detected="迷客夏",
        identity_confidence="high",
        raw_ref="raw/tavily/milksha_exact.json#0",
    )

    packet = build_web_search_candidate_packet(intent, candidate)
    rechecked = add_hard_recheck_metadata(packet)
    result = consume_rechecked_packets((rechecked,))

    assert packet["packet_type"] == "SearchCandidatePacket"
    assert packet["truth_level"] == "candidate"
    assert packet["source_type"] == "web_search"
    assert packet["source_quality_label"] == "brand_menu"
    assert packet["match_type"] == "exact"
    assert packet["brand_match"] == "same"
    assert packet["matched_name"] == "迷客夏珍珠紅茶拿鐵"
    assert packet["canonical_name"] == "迷客夏 珍珠紅茶拿鐵"
    assert packet["raw_ref"] == "raw/tavily/milksha_exact.json#0"
    assert packet["query"] == "迷客夏珍珠紅茶拿鐵"
    assert _FORBIDDEN_PACKET_FIELDS.isdisjoint(packet)
    assert rechecked["hard_recheck_risks"] == []
    assert rechecked["supports_exact_claim"] is True
    assert result.rejected_candidates == ()
    assert result.accepted_packets[0]["accepted_usage"] == "exact"


def test_same_brand_nearby_variant_is_related_and_rejected_as_sibling() -> None:
    intent = _intent(
        base_dish="珍珠紅茶拿鐵",
        alias="迷客夏珍珠紅茶拿鐵",
        brand_hint="迷客夏",
    )
    candidate = _candidate(
        candidate_id="web_search_candidate:milksha_sibling",
        title="迷客夏 珍珠鮮奶茶",
        url="https://milksha.example/menu/pearl-fresh-milk-tea",
        query="迷客夏珍珠紅茶拿鐵",
        brand_detected="迷客夏",
        identity_confidence="medium",
        raw_ref="raw/tavily/milksha_sibling.json#0",
    )

    packet = build_web_search_candidate_packet(intent, candidate)
    rechecked = add_hard_recheck_metadata(packet)
    result = consume_rechecked_packets((rechecked,))

    assert packet["match_type"] == "related"
    assert packet["sibling_variant_risk"] == {"present": True, "reason": "same_brand_nearby_variant"}
    assert rechecked["supports_exact_claim"] is False
    assert "sibling_variant" in rechecked["hard_recheck_risks"]
    assert result.accepted_packets == ()
    assert result.rejected_candidates[0]["risk_type"] == "sibling_variant"


def test_official_wrong_item_candidate_is_no_match_and_rejected() -> None:
    intent = _intent(
        base_dish="珍珠紅茶拿鐵",
        alias="可可珍珠紅茶拿鐵",
        brand_hint="可可",
    )
    candidate = _candidate(
        candidate_id="web_search_candidate:coco_wrong_item",
        title="可可 珍珠奶茶",
        url="https://coco.example/menu/pearl-milk-tea",
        query="可可珍珠紅茶拿鐵",
        brand_detected="可可",
        identity_confidence="low",
        raw_ref="raw/tavily/coco_wrong_item.json#0",
    )

    packet = build_web_search_candidate_packet(intent, candidate)
    rechecked = add_hard_recheck_metadata(packet)
    result = consume_rechecked_packets((rechecked,))

    assert packet["source_quality_label"] == "brand_menu"
    assert packet["match_type"] == "no_match"
    assert packet["sibling_variant_risk"] == {"present": False, "reason": None}
    assert rechecked["supports_exact_claim"] is False
    assert "wrong_item" in rechecked["hard_recheck_risks"]
    assert result.accepted_packets == ()
    assert result.rejected_candidates[0]["risk_type"] == "wrong_item"


def test_explicit_conflicting_size_is_rejected_as_wrong_size() -> None:
    intent = _intent(
        base_dish="冰那堤",
        alias="星巴克冰那堤大杯",
        brand_hint="星巴克",
        size_hint="大杯",
    )
    candidate = _candidate(
        candidate_id="web_search_candidate:starbucks_wrong_size",
        title="星巴克 冰那堤 中杯",
        url="https://starbucks.example/menu/iced-latte-medium",
        query="星巴克冰那堤大杯",
        brand_detected="星巴克",
        identity_confidence="high",
        raw_ref="raw/tavily/starbucks_wrong_size.json#0",
    )

    packet = build_web_search_candidate_packet(intent, candidate)
    rechecked = add_hard_recheck_metadata(packet)
    result = consume_rechecked_packets((rechecked,))

    assert packet["match_type"] == "exact"
    assert packet["size_or_serving_match"] == "different"
    assert "wrong_size" in rechecked["hard_recheck_risks"]
    assert result.accepted_packets == ()
    assert result.rejected_candidates[0]["risk_type"] == "wrong_size"


def test_weak_third_party_candidate_is_rejected_not_accepted_as_anchor() -> None:
    intent = _intent(
        base_dish="珍珠紅茶拿鐵",
        alias="迷客夏珍珠紅茶拿鐵",
        brand_hint="迷客夏",
    )
    candidate = _candidate(
        candidate_id="web_search_candidate:third_party_weak",
        title="迷客夏 珍珠紅茶拿鐵",
        url="https://third-party.example/post",
        query="迷客夏珍珠紅茶拿鐵",
        brand_detected="迷客夏",
        officialness_hint="unknown",
        source_quality_hint="low",
        identity_confidence="high",
        raw_ref="raw/tavily/third_party_weak.json#0",
    )

    packet = build_web_search_candidate_packet(intent, candidate)
    rechecked = add_hard_recheck_metadata(packet)
    result = consume_rechecked_packets((rechecked,))

    assert packet["source_quality_label"] == "third_party"
    assert rechecked["hard_recheck_risks"] == []
    assert rechecked["supports_exact_claim"] is False
    assert result.accepted_packets == ()
    assert result.rejected_candidates[0]["risk_type"] == "insufficient_evidence"


def test_build_web_search_candidate_packets_preserves_order_and_metadata() -> None:
    intent = _intent(
        base_dish="珍珠紅茶拿鐵",
        alias="迷客夏珍珠紅茶拿鐵",
        brand_hint="迷客夏",
    )
    first = _candidate(
        candidate_id="web_search_candidate:first",
        title="迷客夏 珍珠紅茶拿鐵",
        url="https://milksha.example/menu/one",
        query="迷客夏珍珠紅茶拿鐵",
        brand_detected="迷客夏",
        raw_ref="raw/tavily/one.json#0",
    )
    second = _candidate(
        candidate_id="web_search_candidate:second",
        title="迷客夏 珍珠鮮奶茶",
        url="https://milksha.example/menu/two",
        query="迷客夏珍珠紅茶拿鐵",
        brand_detected="迷客夏",
        raw_ref="raw/tavily/two.json#0",
    )

    packets = build_web_search_candidate_packets(intent, (first, second))

    assert [packet["packet_id"] for packet in packets] == [
        "pkt_web_search_first",
        "pkt_web_search_second",
    ]
    assert packets[0]["query"] == "迷客夏珍珠紅茶拿鐵"
    assert packets[0]["snippet"] == "official menu result"
    assert isinstance(packets[0]["matched_terms"], list)
    assert _FORBIDDEN_PACKET_FIELDS.isdisjoint(packets[0])
