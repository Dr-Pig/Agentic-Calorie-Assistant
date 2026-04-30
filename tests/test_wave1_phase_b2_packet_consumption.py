from __future__ import annotations

from app.nutrition.application.evidence_candidate_packetizer import (
    add_hard_recheck_metadata,
    build_candidate_packet,
)
from app.nutrition.application.exact_item_card_lookup import lookup_exact_item_card_candidates
from app.nutrition.application.packetizer_input_seed import (
    packetizer_input_seeds_from_anchor_lookup_result,
    packetizer_input_seeds_from_exact_item_lookup_result,
)
from app.nutrition.application.retrieval_intent import RetrievalIntent, build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates
from app.nutrition.application.evidence_packet_consumption import consume_rechecked_packets


def test_packet_consumption_accepts_generic_anchor_as_anchor_evidence_only() -> None:
    anchor_result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u5403\u4e86\u8336\u8449\u86cb"))
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))

    result = consume_rechecked_packets((packet,))

    assert result.consumed_packet_ids == ("pkt_generic_anchor_single_item_tea_egg",)
    assert result.rejected_candidates == ()
    assert len(result.accepted_packets) == 1
    assert result.accepted_packets[0]["accepted_usage"] == "anchor"
    assert result.accepted_packets[0]["dish_type"] == "single_item"


def test_packet_consumption_accepts_exact_item_only_when_exact_claim_supported() -> None:
    exact_result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))
    seed = packetizer_input_seeds_from_exact_item_lookup_result(exact_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))

    result = consume_rechecked_packets((packet,))

    assert result.rejected_candidates == ()
    assert len(result.accepted_packets) == 1
    assert result.accepted_packets[0]["accepted_usage"] == "exact"
    assert result.accepted_packets[0]["packet_id"] == "pkt_exact_item_exact_starbucks_latte_iced_large"


def test_packet_consumption_rejects_exact_item_with_insufficient_evidence() -> None:
    exact_result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))
    seed = packetizer_input_seeds_from_exact_item_lookup_result(exact_result)[0]
    packet = build_candidate_packet(seed)
    packet["serving_basis"] = ""
    rechecked = add_hard_recheck_metadata(packet)

    result = consume_rechecked_packets((rechecked,))

    assert result.accepted_packets == ()
    assert len(result.rejected_candidates) == 1
    assert result.rejected_candidates[0]["packet_id"] == "pkt_exact_item_exact_starbucks_latte_iced_large"
    assert result.rejected_candidates[0]["risk_type"] == "insufficient_evidence"


def test_packet_consumption_rejects_exact_item_with_sibling_or_size_risk() -> None:
    exact_result = lookup_exact_item_card_candidates(
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
    seed = packetizer_input_seeds_from_exact_item_lookup_result(exact_result)[0]
    packet = build_candidate_packet(seed)
    packet["size_or_serving_match"] = "different"
    rechecked = add_hard_recheck_metadata(packet)

    result = consume_rechecked_packets((rechecked,))

    assert result.accepted_packets == ()
    assert len(result.rejected_candidates) == 1
    assert result.rejected_candidates[0]["risk_type"] == "wrong_size"
    assert result.rejected_candidates[0]["usable_as_evidence"] is False
    assert result.rejected_candidates[0]["exact_claim_blocked"] is True
    assert result.rejected_candidates[0]["estimability_blocked"] is False


def test_packet_consumption_does_not_silently_drop_packets() -> None:
    anchor_result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336"))
    anchor_seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    anchor_packet = add_hard_recheck_metadata(build_candidate_packet(anchor_seed))

    exact_result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))
    exact_seed = packetizer_input_seeds_from_exact_item_lookup_result(exact_result)[0]
    exact_packet = build_candidate_packet(exact_seed)
    exact_packet["sibling_variant_risk"] = {"present": True, "reason": "manual sibling test"}
    exact_rechecked = add_hard_recheck_metadata(exact_packet)

    result = consume_rechecked_packets((anchor_packet, exact_rechecked))

    assert result.consumed_packet_ids == (
        "pkt_generic_anchor_custom_drink_boba_milk_tea",
        "pkt_exact_item_exact_starbucks_latte_iced_large",
    )
    assert len(result.accepted_packets) == 1
    assert len(result.rejected_candidates) == 1


def test_packet_consumption_accepts_web_search_exact_support_only_as_exact_evidence() -> None:
    packet = add_hard_recheck_metadata(
        {
            "packet_id": "pkt_web_search_exact",
            "packet_type": "SearchCandidatePacket",
            "truth_level": "candidate",
            "source_type": "web_search",
            "source_quality_label": "brand_menu",
            "raw_ref": "raw/tavily/exact.json#0",
            "title": "\u8ff7\u5ba2\u590f \u73cd\u73e0\u7d05\u8336\u62ff\u9435",
            "url": "https://milksha.example/menu/pearl-black-tea-latte",
            "snippet": "official menu result",
            "tavily_score": 0.93,
            "query": "\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
            "matched_terms": ["\u8ff7\u5ba2\u590f", "\u73cd\u73e0\u7d05\u8336\u62ff\u9435"],
            "matched_name": "\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
            "canonical_name": "\u8ff7\u5ba2\u590f \u73cd\u73e0\u7d05\u8336\u62ff\u9435",
            "match_type": "exact",
            "brand_match": "same",
            "size_or_serving_match": "not_applicable",
            "modifier_match": "not_applicable",
            "serving_basis": "per_cup",
            "sibling_variant_risk": {"present": False, "reason": None},
        }
    )

    result = consume_rechecked_packets((packet,))

    assert result.rejected_candidates == ()
    assert len(result.accepted_packets) == 1
    assert result.accepted_packets[0]["accepted_usage"] == "exact"


def test_packet_consumption_rejects_web_search_sibling_packet() -> None:
    packet = add_hard_recheck_metadata(
        {
            "packet_id": "pkt_web_search_sibling",
            "packet_type": "SearchCandidatePacket",
            "truth_level": "candidate",
            "source_type": "web_search",
            "source_quality_label": "brand_menu",
            "raw_ref": "raw/tavily/sibling.json#0",
            "title": "\u8ff7\u5ba2\u590f \u73cd\u73e0\u9bae\u5976\u8336",
            "url": "https://milksha.example/menu/pearl-fresh-milk-tea",
            "snippet": "official menu result",
            "tavily_score": 0.91,
            "query": "\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
            "matched_terms": ["\u8ff7\u5ba2\u590f", "\u73cd\u73e0"],
            "matched_name": "\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
            "canonical_name": "\u8ff7\u5ba2\u590f \u73cd\u73e0\u9bae\u5976\u8336",
            "match_type": "related",
            "brand_match": "same",
            "size_or_serving_match": "not_applicable",
            "modifier_match": "not_applicable",
            "serving_basis": "per_cup",
            "sibling_variant_risk": {"present": True, "reason": "same_brand_nearby_variant"},
        }
    )

    result = consume_rechecked_packets((packet,))

    assert result.accepted_packets == ()
    assert len(result.rejected_candidates) == 1
    assert result.rejected_candidates[0]["risk_type"] == "sibling_variant"


def test_packet_consumption_rejects_web_search_wrong_item_packet() -> None:
    packet = add_hard_recheck_metadata(
        {
            "packet_id": "pkt_web_search_wrong_item",
            "packet_type": "SearchCandidatePacket",
            "truth_level": "candidate",
            "source_type": "web_search",
            "source_quality_label": "brand_menu",
            "raw_ref": "raw/tavily/wrong_item.json#0",
            "title": "\u53ef\u53ef \u73cd\u73e0\u5976\u8336",
            "url": "https://coco.example/menu/pearl-milk-tea",
            "snippet": "official menu result",
            "tavily_score": 0.89,
            "query": "\u53ef\u53ef\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
            "matched_terms": ["\u53ef\u53ef", "\u73cd\u73e0"],
            "matched_name": "\u53ef\u53ef\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
            "canonical_name": "\u53ef\u53ef \u73cd\u73e0\u5976\u8336",
            "match_type": "no_match",
            "brand_match": "same",
            "size_or_serving_match": "not_applicable",
            "modifier_match": "not_applicable",
            "serving_basis": "per_cup",
            "sibling_variant_risk": {"present": False, "reason": None},
        }
    )

    result = consume_rechecked_packets((packet,))

    assert result.accepted_packets == ()
    assert len(result.rejected_candidates) == 1
    assert result.rejected_candidates[0]["risk_type"] == "wrong_item"
    assert result.rejected_candidates[0]["usable_as_evidence"] is False


def test_packet_consumption_rejects_exact_item_with_wrong_modifier_without_blocking_estimation_policy() -> None:
    exact_result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))
    seed = packetizer_input_seeds_from_exact_item_lookup_result(exact_result)[0]
    packet = build_candidate_packet(seed)
    packet["modifier_match"] = "different"
    rechecked = add_hard_recheck_metadata(packet)

    result = consume_rechecked_packets((rechecked,))

    assert result.accepted_packets == ()
    assert len(result.rejected_candidates) == 1
    rejected = result.rejected_candidates[0]
    assert rejected["risk_type"] == "wrong_modifier"
    assert rejected["reason"] == "deterministic_hard_recheck_failed:wrong_modifier"
    assert rejected["exact_claim_blocked"] is True
    assert rejected["estimability_blocked"] is False
