from __future__ import annotations

from app.nutrition.application.exact_item_card_lookup import lookup_exact_item_card_candidates
from app.nutrition.application.retrieval_intent import RetrievalIntent, build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates
from app.nutrition.application.packetizer_input_seed import (
    PacketizerInputSeed,
    packetizer_input_seeds_from_anchor_lookup_result,
    packetizer_input_seeds_from_exact_item_lookup_result,
)


def test_anchor_candidate_maps_to_generic_packet_seed() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u5403\u4e86\u8336\u8449\u86cb"))

    seeds = packetizer_input_seeds_from_anchor_lookup_result(result)

    assert len(seeds) == 1
    seed = seeds[0]
    assert isinstance(seed, PacketizerInputSeed)
    assert seed.candidate_kind == "generic_anchor"
    assert seed.packet_type == "GenericDbCandidatePacket"
    assert seed.source_type == "generic_db"
    assert seed.match_type == "generic"
    assert seed.canonical_name == "\u8336\u8449\u86cb"
    assert seed.serving_basis == "common_serving"
    assert seed.kcal_range == (70, 90)
    assert seed.likely_kcal == 80
    assert seed.kcal is None
    assert seed.kcal_band is None


def test_exact_item_title_match_maps_to_exact_packet_seed() -> None:
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

    seeds = packetizer_input_seeds_from_exact_item_lookup_result(result)

    assert len(seeds) == 1
    seed = seeds[0]
    assert seed.candidate_kind == "exact_item_card"
    assert seed.packet_type == "ExactDbCandidatePacket"
    assert seed.source_type == "exact_db"
    assert seed.match_type == "exact"
    assert seed.canonical_name == "\u677e\u5c4b\u7279\u76db\u725b\u4e3c"
    assert seed.serving_basis == "\u7279\u76db"
    assert seed.kcal == 1350.0
    assert seed.kcal_range is None
    assert seed.likely_kcal is None


def test_exact_item_alias_match_maps_to_alias_exact_packet_seed() -> None:
    result = lookup_exact_item_card_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f"))

    seeds = packetizer_input_seeds_from_exact_item_lookup_result(result)

    assert len(seeds) == 1
    assert seeds[0].match_type == "alias_exact"
    assert seeds[0].canonical_name == "\u661f\u5df4\u514b \u90a3\u5802(\u51b0) \u5927\u676f"


def test_anchor_lane_never_upgrades_into_exact_match_type() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336"))

    seeds = packetizer_input_seeds_from_anchor_lookup_result(result)

    assert seeds
    assert all(seed.match_type == "generic" for seed in seeds)


def test_anchor_defer_result_produces_no_packetizer_input_seed() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u5403\u4e86\u6ef7\u5473"))

    assert packetizer_input_seeds_from_anchor_lookup_result(result) == ()
    assert result.clarify_support is not None


def test_exact_item_no_match_result_produces_no_packetizer_input_seed() -> None:
    result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="\u8d85\u7d1a\u62b9\u8336\u6b50\u857e",
            aliases=["\u8d85\u7d1a\u62b9\u8336\u6b50\u857e"],
            brand_hint="\u7d71\u4e00",
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        )
    )

    assert packetizer_input_seeds_from_exact_item_lookup_result(result) == ()
