from __future__ import annotations

from app.nutrition.application.evidence_candidate_packetizer import (
    add_hard_recheck_metadata,
    add_hard_recheck_metadata_many,
    build_candidate_packet,
)
from app.nutrition.application.local_synthesis import synthesize_local_manager_pass
from app.nutrition.application.evidence_packet_consumption import consume_rechecked_packets
from app.nutrition.application.exact_item_card_lookup import lookup_exact_item_card_candidates
from app.nutrition.application.packetizer_input_seed import (
    packetizer_input_seeds_from_anchor_lookup_result,
    packetizer_input_seeds_from_exact_item_lookup_result,
)
from app.nutrition.application.retrieval_intent import RetrievalIntent, build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates
from app.nutrition.application.web_search_candidate_producer import produce_web_search_candidates
from app.nutrition.application.web_search_packetizer import build_web_search_candidate_packets


def test_local_synthesis_turns_exact_item_into_exact_item_result() -> None:
    intent = build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f")
    exact_result = lookup_exact_item_card_candidates(intent)
    seed = packetizer_input_seeds_from_exact_item_lookup_result(exact_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["interpreted_food_identity"] == "\u661f\u5df4\u514b \u90a3\u5802(\u51b0) \u5927\u676f"
    assert item["assumed_composition"] is None
    assert item["kcal_range"] == [154.0, 154.0]
    assert item["likely_kcal"] == 154.0
    assert item["exactness_posture"] == "exact"
    assert item["evidence_confidence"] == "exact"
    assert item["evidence_used"][0]["usage"] == "exact"
    assert item["rejected_candidates"] == []
    assert item["suggested_followup_question"] is None


def test_local_synthesis_turns_generic_single_item_into_estimated_item_result() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u8336\u8449\u86cb")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["interpreted_food_identity"] == "\u8336\u8449\u86cb"
    assert item["assumed_composition"] == "single item"
    assert item["exactness_posture"] == "estimated"
    assert item["evidence_confidence"] == "strong"
    assert item["evidence_used"][0]["usage"] == "anchor"
    assert item["suggested_followup_question"] is None


def test_local_synthesis_metadata_first_clarify_required_overrides_estimable_dish_type() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u8336\u8449\u86cb")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    packet["clarify_required"] = True
    packet["followup_hints"] = ["ask_listed_items", "ask_portion"]
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["exactness_posture"] == "unresolved"
    assert item["evidence_confidence"] == "insufficient"
    assert item["kcal_range"] is None
    assert item["likely_kcal"] is None
    assert item["evidence_used"] == []
    assert item["suggested_followup_question"] == "\u8acb\u5217\u51fa\u54c1\u9805\u8207\u5927\u81f4\u4efd\u91cf\u3002"


def test_local_synthesis_metadata_first_uses_composition_posture_over_dish_type() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u8336\u8449\u86cb")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    packet["composition_posture"] = "estimable_generic_meal"
    packet["variance_level"] = "moderate"
    packet["followup_hints"] = ["ask_main_style", "ask_rice_portion"]
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["assumed_composition"] == "generic meal"
    assert item["exactness_posture"] == "provisional"
    assert item["evidence_confidence"] == "moderate"
    assert item["suggested_followup_question"] == "\u8acb\u88dc\u5145\u4e3b\u83dc\u505a\u6cd5\u6216\u767d\u98ef\u4efd\u91cf\u3002"


def test_local_synthesis_metadata_first_uses_variance_level_for_single_item_confidence() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u8336\u8449\u86cb")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    packet["variance_level"] = "moderate"
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["exactness_posture"] == "estimated"
    assert item["evidence_confidence"] == "moderate"


def test_local_synthesis_metadata_first_turns_listed_item_component_into_strong_estimate() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u8c46\u5e72\u7684\u6ef7\u5473")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["assumed_composition"] == "listed item"
    assert item["exactness_posture"] == "estimated"
    assert item["evidence_confidence"] == "strong"


def test_local_synthesis_turns_generic_meal_into_provisional_item_result() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u96de\u817f\u4fbf\u7576")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["exactness_posture"] == "provisional"
    assert item["evidence_confidence"] == "moderate"
    assert item["suggested_followup_question"] == "\u8acb\u88dc\u5145\u4e3b\u83dc\u505a\u6cd5\u6216\u767d\u98ef\u4efd\u91cf\u3002"


def test_local_synthesis_metadata_first_turns_refinement_anchor_into_estimated_moderate() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u725b\u8089\u9eb5")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["assumed_composition"] == "stable-base dish"
    assert item["exactness_posture"] == "estimated"
    assert item["evidence_confidence"] == "moderate"
    assert item["suggested_followup_question"] == "\u8acb\u88dc\u5145\u9eb5\u91cf\u3001\u52a0\u6599\u6216\u4efd\u91cf\u3002"


def test_local_synthesis_turns_customizable_drink_into_estimated_item_result_with_followup() -> None:
    intent = build_retrieval_intent("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["exactness_posture"] == "estimated"
    assert item["evidence_confidence"] == "moderate"
    assert item["suggested_followup_question"] == "\u8acb\u88dc\u5145\u7cd6\u5ea6\u548c\u676f\u578b\u3002"


def test_local_synthesis_handles_approved_b2_case_law_from_accepted_packets_only() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u9ebb\u8fa3\u81ed\u8c46\u8150")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["interpreted_food_identity"] == "\u9ebb\u8fa3\u81ed\u8c46\u8150"
    assert item["exactness_posture"] == "estimated"
    assert item["evidence_confidence"] == "moderate"
    assert item["evidence_used"][0]["packet_id"] == packet["packet_id"]
    assert item["suggested_followup_question"] == "\u8acb\u88dc\u5145\u9eb5\u91cf\u3001\u52a0\u6599\u6216\u4efd\u91cf\u3002"


def test_local_synthesis_keeps_composition_unknown_cases_unresolved_without_packets() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u9ebb\u8fa3\u71d9")
    anchor_result = lookup_anchor_candidates(intent)
    consumption = consume_rechecked_packets(())

    manager_pass_2 = synthesize_local_manager_pass(
        intent,
        consumption,
        clarify_support=anchor_result.clarify_support,
    )

    item = manager_pass_2["item_results"][0]
    assert item["interpreted_food_identity"] == "\u9ebb\u8fa3\u71d9"
    assert item["exactness_posture"] == "unresolved"
    assert item["kcal_range"] is None
    assert item["likely_kcal"] is None
    assert item["evidence_used"] == []
    assert item["suggested_followup_question"] == "\u8acb\u5217\u51fa\u54c1\u9805\u8207\u5927\u81f4\u4efd\u91cf\u3002"


def test_local_synthesis_missing_metadata_falls_back_to_dish_type_behavior() -> None:
    intent = build_retrieval_intent("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    packet.pop("composition_posture", None)
    packet.pop("variance_level", None)
    packet.pop("followup_hints", None)
    packet.pop("clarify_required", None)
    consumption = consume_rechecked_packets((packet,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["exactness_posture"] == "estimated"
    assert item["evidence_confidence"] == "moderate"
    assert item["suggested_followup_question"] == "\u8acb\u88dc\u5145\u7cd6\u5ea6\u548c\u676f\u578b\u3002"


def test_local_synthesis_turns_rejected_exact_item_into_unresolved_item_result() -> None:
    intent = build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f")
    exact_result = lookup_exact_item_card_candidates(intent)
    seed = packetizer_input_seeds_from_exact_item_lookup_result(exact_result)[0]
    packet = build_candidate_packet(seed)
    packet["serving_basis"] = ""
    rechecked = add_hard_recheck_metadata(packet)
    consumption = consume_rechecked_packets((rechecked,))

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["interpreted_food_identity"] == "\u661f\u5df4\u514b \u90a3\u5802(\u51b0) \u5927\u676f"
    assert item["exactness_posture"] == "unresolved"
    assert item["likely_kcal"] is None
    assert item["evidence_used"] == []
    assert item["rejected_candidates"][0]["risk_type"] == "insufficient_evidence"
    assert item["suggested_followup_question"] == "\u8acb\u78ba\u8a8d\u5177\u9ad4\u54c1\u9805\u8207\u5c3a\u5bf8\u6216\u4efd\u91cf\u3002"


def test_local_synthesis_turns_semantic_only_luwei_into_clarify_output_without_packets() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u6ef7\u5473")
    anchor_result = lookup_anchor_candidates(intent)
    consumption = consume_rechecked_packets(())

    manager_pass_2 = synthesize_local_manager_pass(
        intent,
        consumption,
        clarify_support=anchor_result.clarify_support,
    )

    item = manager_pass_2["item_results"][0]
    assert item["interpreted_food_identity"] == "\u6ef7\u5473"
    assert item["assumed_composition"] == "composition unknown basket"
    assert item["kcal_range"] is None
    assert item["likely_kcal"] is None
    assert item["exactness_posture"] == "unresolved"
    assert item["evidence_confidence"] == "insufficient"
    assert item["evidence_used"] == []
    assert item["rejected_candidates"] == []
    assert item["suggested_followup_question"] == "\u8acb\u5217\u51fa\u54c1\u9805\u8207\u5927\u81f4\u4efd\u91cf\u3002"


def test_local_synthesis_rejected_web_search_keeps_requested_identity_in_unresolved_output() -> None:
    intent = RetrievalIntent(
        base_dish="珍珠紅茶拿鐵",
        aliases=["迷客夏珍珠紅茶拿鐵"],
        brand_hint="迷客夏",
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )
    candidates = produce_web_search_candidates(
        query="迷客夏珍珠紅茶拿鐵",
        identity_target="迷客夏珍珠紅茶拿鐵",
        raw_hits=[
            {
                "title": "迷客夏珍珠鮮奶茶",
                "url": "https://example.test/milkshop-fresh-milk-tea",
                "snippet": "迷客夏珍珠鮮奶茶 menu",
                "score": 0.91,
                "officialness": "official",
                "brand_detected": "迷客夏",
                "identity_confidence": "high",
                "source_quality_label": "high",
            }
        ],
    )
    packets = build_web_search_candidate_packets(intent, candidates)
    rechecked = add_hard_recheck_metadata_many(packets)
    consumption = consume_rechecked_packets(rechecked)

    manager_pass_2 = synthesize_local_manager_pass(intent, consumption)

    item = manager_pass_2["item_results"][0]
    assert item["interpreted_food_identity"] == "迷客夏珍珠紅茶拿鐵"
    assert item["exactness_posture"] == "unresolved"
    assert item["evidence_used"] == []
    assert item["rejected_candidates"][0]["risk_type"] == "sibling_variant"
