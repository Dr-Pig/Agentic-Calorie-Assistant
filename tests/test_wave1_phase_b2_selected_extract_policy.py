from __future__ import annotations

from app.nutrition.application.b2_candidate_packetizer import add_hard_recheck_metadata
from app.nutrition.application.selected_extract_policy import choose_selected_extract_packet


def _search_packet(
    *,
    packet_id: str,
    source_quality_label: str = "brand_menu",
    match_type: str = "exact",
    supports_exact_claim: bool = True,
    hard_recheck_risks: list[str] | None = None,
    sibling_present: bool = False,
    size_or_serving_match: str = "same",
    modifier_match: str = "same",
) -> dict[str, object]:
    packet = {
        "packet_id": packet_id,
        "packet_type": "SearchCandidatePacket",
        "truth_level": "candidate",
        "source_type": "web_search",
        "source_quality_label": source_quality_label,
        "raw_ref": f"raw/tavily/{packet_id}.json#0",
        "title": "迷客夏 珍珠紅茶拿鐵",
        "url": "https://milksha.example/menu/pearl-black-tea-latte",
        "snippet": "official menu result",
        "tavily_score": 0.93,
        "query": "迷客夏珍珠紅茶拿鐵",
        "matched_terms": ["迷客夏", "珍珠紅茶拿鐵"],
        "matched_name": "迷客夏珍珠紅茶拿鐵",
        "canonical_name": "迷客夏 珍珠紅茶拿鐵",
        "match_type": match_type,
        "brand_match": "same",
        "size_or_serving_match": size_or_serving_match,
        "modifier_match": modifier_match,
        "serving_basis": "per_cup",
        "sibling_variant_risk": {"present": sibling_present, "reason": "same_brand_nearby_variant" if sibling_present else None},
    }
    if hard_recheck_risks is not None:
        packet["hard_recheck_risks"] = hard_recheck_risks
        packet["supports_exact_claim"] = supports_exact_claim
        return packet
    return add_hard_recheck_metadata(packet)


def test_selected_extract_policy_picks_one_qualifying_same_item_packet() -> None:
    exact_packet = _search_packet(packet_id="pkt_web_search_exact")
    decision = choose_selected_extract_packet((exact_packet,))

    assert decision.selected_search_packet_id == "pkt_web_search_exact"
    assert decision.selected_urls == ["https://milksha.example/menu/pearl-black-tea-latte"]
    assert decision.extract_allowed_by_policy is True
    assert decision.extract_reason == "selected_same_item_official_candidate"
    assert decision.max_extract_urls == 1
    assert decision.extract_count == 1


def test_selected_extract_policy_rejects_related_or_wrong_item_packets() -> None:
    related = _search_packet(packet_id="pkt_web_search_related", match_type="related")

    decision = choose_selected_extract_packet((related,))

    assert decision.selected_search_packet_id is None
    assert decision.selected_urls == []
    assert decision.extract_allowed_by_policy is False
    assert decision.extract_reason == "no_exact_same_item_search_packet"
    assert decision.extract_count == 0


def test_selected_extract_policy_rejects_sibling_and_modifier_or_size_mismatch() -> None:
    sibling = _search_packet(packet_id="pkt_web_search_sibling", sibling_present=True)
    wrong_size = _search_packet(packet_id="pkt_web_search_wrong_size", size_or_serving_match="different")
    wrong_modifier = _search_packet(packet_id="pkt_web_search_wrong_modifier", modifier_match="different")

    for packet in (sibling, wrong_size, wrong_modifier):
        decision = choose_selected_extract_packet((packet,))
        assert decision.extract_allowed_by_policy is False
        assert decision.selected_search_packet_id is None
        assert decision.selected_urls == []


def test_selected_extract_policy_rejects_non_official_or_identity_unsafe_packets() -> None:
    third_party = _search_packet(packet_id="pkt_web_search_third_party", source_quality_label="third_party")
    wrong_item = _search_packet(packet_id="pkt_web_search_wrong_item", match_type="no_match")

    assert choose_selected_extract_packet((third_party,)).extract_allowed_by_policy is False
    assert choose_selected_extract_packet((wrong_item,)).extract_allowed_by_policy is False


def test_selected_extract_policy_allows_identity_safe_official_candidate_for_extract_even_before_serving_evidence() -> None:
    official_search_only = _search_packet(
        packet_id="pkt_web_search_identity_safe",
        hard_recheck_risks=["insufficient_evidence"],
        supports_exact_claim=False,
    )

    decision = choose_selected_extract_packet((official_search_only,))

    assert decision.extract_allowed_by_policy is True
    assert decision.selected_search_packet_id == "pkt_web_search_identity_safe"
    assert decision.extract_reason == "selected_same_item_official_candidate"
