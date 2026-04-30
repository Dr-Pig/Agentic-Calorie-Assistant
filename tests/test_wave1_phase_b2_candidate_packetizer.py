from __future__ import annotations

from app.nutrition.application.evidence_candidate_packetizer import (
    add_hard_recheck_metadata,
    add_hard_recheck_metadata_many,
    build_candidate_packet,
    build_candidate_packets,
)
from app.nutrition.application.exact_item_card_lookup import lookup_exact_item_card_candidates
from app.nutrition.application.packetizer_input_seed import (
    packetizer_input_seeds_from_anchor_lookup_result,
    packetizer_input_seeds_from_exact_item_lookup_result,
)
from app.nutrition.application.retrieval_intent import RetrievalIntent, build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates


def test_build_candidate_packet_maps_generic_anchor_seed_to_generic_db_packet() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u5403\u4e86\u8336\u8449\u86cb"))
    seed = packetizer_input_seeds_from_anchor_lookup_result(result)[0]

    packet = build_candidate_packet(seed)

    assert packet["packet_id"] == "pkt_generic_anchor_single_item_tea_egg"
    assert packet["packet_type"] == "GenericDbCandidatePacket"
    assert packet["truth_level"] == "candidate"
    assert packet["source_type"] == "generic_db"
    assert packet["source_quality_label"] == "internal_generic"
    assert packet["match_type"] == "generic"
    assert packet["brand_match"] == "not_applicable"
    assert packet["size_or_serving_match"] == "generic_serving"
    assert packet["modifier_match"] == "not_applicable"
    assert packet["serving_basis"] == "common_serving"
    assert packet["sibling_variant_risk"] == {"present": False, "reason": None}


def test_build_candidate_packet_maps_exact_item_title_seed_to_exact_db_packet() -> None:
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
    seed = packetizer_input_seeds_from_exact_item_lookup_result(result)[0]

    packet = build_candidate_packet(seed)

    assert packet["packet_id"] == "pkt_exact_item_exact_matsuya_tokumori_gyudon"
    assert packet["packet_type"] == "ExactDbCandidatePacket"
    assert packet["source_type"] == "exact_db"
    assert packet["source_quality_label"] == "internal_exact"
    assert packet["match_type"] == "exact"
    assert packet["brand_match"] == "same"
    assert packet["size_or_serving_match"] == "same"
    assert packet["modifier_match"] == "unknown"


def test_build_candidate_packet_maps_exact_item_alias_seed_to_alias_exact_packet() -> None:
    result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))
    seed = packetizer_input_seeds_from_exact_item_lookup_result(result)[0]

    packet = build_candidate_packet(seed)

    assert packet["match_type"] == "alias_exact"
    assert packet["canonical_name"] == "\u661f\u5df4\u514b \u90a3\u5802(\u51b0) \u5927\u676f"


def test_build_candidate_packets_preserves_order() -> None:
    anchor_result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336"))
    exact_result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))
    seeds = (
        *packetizer_input_seeds_from_anchor_lookup_result(anchor_result),
        *packetizer_input_seeds_from_exact_item_lookup_result(exact_result),
    )

    packets = build_candidate_packets(seeds)

    assert [packet["packet_type"] for packet in packets] == ["GenericDbCandidatePacket", "ExactDbCandidatePacket"]


def test_add_hard_recheck_metadata_marks_generic_anchor_as_not_supporting_exact_claim() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u5403\u4e86\u8336\u8449\u86cb"))
    seed = packetizer_input_seeds_from_anchor_lookup_result(result)[0]

    packet = add_hard_recheck_metadata(build_candidate_packet(seed))

    assert packet["hard_recheck_risks"] == []
    assert packet["supports_exact_claim"] is False


def test_add_hard_recheck_metadata_marks_valid_exact_item_as_supporting_exact_claim() -> None:
    result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))
    seed = packetizer_input_seeds_from_exact_item_lookup_result(result)[0]

    packet = add_hard_recheck_metadata(build_candidate_packet(seed))

    assert packet["hard_recheck_risks"] == []
    assert packet["supports_exact_claim"] is True


def test_blank_serving_basis_yields_insufficient_evidence_risk() -> None:
    result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))
    seed = packetizer_input_seeds_from_exact_item_lookup_result(result)[0]
    packet = build_candidate_packet(seed)
    packet["serving_basis"] = ""

    enriched = add_hard_recheck_metadata(packet)

    assert enriched["hard_recheck_risks"] == ["insufficient_evidence"]
    assert enriched["supports_exact_claim"] is False


def test_add_hard_recheck_metadata_many_does_not_drop_packets() -> None:
    anchor_result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336"))
    exact_result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))
    seeds = (
        *packetizer_input_seeds_from_anchor_lookup_result(anchor_result),
        *packetizer_input_seeds_from_exact_item_lookup_result(exact_result),
    )

    packets = add_hard_recheck_metadata_many(build_candidate_packets(seeds))

    assert len(packets) == 2
