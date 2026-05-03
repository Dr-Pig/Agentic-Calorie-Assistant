from __future__ import annotations

import pytest

from app.nutrition.application.evidence_candidate_packetizer import (
    add_hard_recheck_metadata,
    build_candidate_packet,
)
from app.nutrition.application.evidence_packet_consumption import consume_rechecked_packets
from app.nutrition.application.final_mapping import map_final_item_result
from app.nutrition.application.local_synthesis import synthesize_local_manager_pass
from app.nutrition.application.packetizer_input_seed import packetizer_input_seeds_from_anchor_lookup_result
from app.nutrition.application.retrieval_intent import build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates


@pytest.mark.parametrize(
    ("message", "expected_name", "required_followup"),
    [
        ("\u6211\u559d\u4e86\u62ff\u9435", "\u62ff\u9435", "ask_milk_type"),
        ("\u6211\u559d\u4e86\u7f8e\u5f0f\u5496\u5561", "\u7f8e\u5f0f\u5496\u5561", "ask_cup_size"),
        ("\u6211\u559d\u4e86\u8c46\u6f3f", "\u8c46\u6f3f", "ask_sugar_level"),
        ("\u6211\u559d\u4e86\u9bae\u5976\u8336", "\u9bae\u5976\u8336", "ask_sugar_level"),
        ("\u6211\u559d\u4e86\u7121\u7cd6\u7da0\u8336", "\u7121\u7cd6\u7da0\u8336", "ask_cup_size"),
        ("\u6211\u559d\u4e86\u53ef\u6a02", "\u53ef\u6a02", "ask_size"),
    ],
)
def test_practical_drink_anchors_are_lookup_support_only(
    message: str,
    expected_name: str,
    required_followup: str,
) -> None:
    result = lookup_anchor_candidates(build_retrieval_intent(message))

    assert result.defer_reason is None
    assert result.clarify_support is None
    assert result.retrieval_context == "logging_support"
    assert result.mutation_authority == "none"
    assert [candidate.canonical_name for candidate in result.candidates] == [expected_name]

    candidate = result.candidates[0]
    assert candidate.support_role == "lookup_support_only"
    assert candidate.truth_level == "anchor"
    assert candidate.source_posture == "generic_anchor_seed"
    assert required_followup in candidate.followup_hints


@pytest.mark.parametrize(
    ("message", "expected_name", "expected_question"),
    [
        (
            "\u6211\u559d\u4e86\u62ff\u9435",
            "\u62ff\u9435",
            "\u8acb\u88dc\u5145\u676f\u578b\u6216\u5976\u985e\u3002",
        ),
        (
            "\u6211\u559d\u4e86\u7f8e\u5f0f\u5496\u5561",
            "\u7f8e\u5f0f\u5496\u5561",
            "\u8acb\u88dc\u5145\u676f\u578b\u6216\u4efd\u91cf\u3002",
        ),
        (
            "\u6211\u559d\u4e86\u8c46\u6f3f",
            "\u8c46\u6f3f",
            "\u8acb\u88dc\u5145\u7cd6\u5ea6\u548c\u676f\u578b\u3002",
        ),
        (
            "\u6211\u559d\u4e86\u9bae\u5976\u8336",
            "\u9bae\u5976\u8336",
            "\u8acb\u88dc\u5145\u7cd6\u5ea6\u548c\u676f\u578b\u3002",
        ),
        (
            "\u6211\u559d\u4e86\u7121\u7cd6\u7da0\u8336",
            "\u7121\u7cd6\u7da0\u8336",
            "\u8acb\u88dc\u5145\u676f\u578b\u6216\u4efd\u91cf\u3002",
        ),
        (
            "\u6211\u559d\u4e86\u53ef\u6a02",
            "\u53ef\u6a02",
            "\u8acb\u88dc\u5145\u5927\u5c0f\u6216\u4efd\u91cf\u3002",
        ),
    ],
)
def test_practical_drink_packets_synthesize_to_anchor_estimate_with_refinement_metadata(
    message: str,
    expected_name: str,
    expected_question: str,
) -> None:
    intent = build_retrieval_intent(message)
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))

    manager_pass = synthesize_local_manager_pass(intent, consumption)

    assert consumption.accepted_packets[0]["accepted_usage"] == "anchor"
    item = manager_pass["item_results"][0]
    assert item["interpreted_food_identity"] == expected_name
    assert item["exactness_posture"] == "estimated"
    assert item["evidence_confidence"] == "moderate"
    assert item["evidence_used"][0]["usage"] == "anchor"
    assert item["suggested_followup_question"] == expected_question


def test_practical_drink_final_mapping_respects_write_owner_block() -> None:
    intent = build_retrieval_intent("\u6211\u559d\u4e86\u62ff\u9435")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))
    item = synthesize_local_manager_pass(intent, consumption)["item_results"][0]

    mapping = map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": False},
        interaction_type="food_logging",
    )

    assert mapping["external_outcome"] == "draft"
    assert mapping["ledger_status"] == "excluded_pending_info"
    assert mapping["mutation_allowed"] is False
    assert mapping["reason"] == "canonical_write_owner_blocked"


def test_practical_drink_query_final_mapping_never_mutates() -> None:
    intent = build_retrieval_intent("\u62ff\u9435\u591a\u5c11\u71b1\u91cf\uff1f")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))
    item = synthesize_local_manager_pass(intent, consumption)["item_results"][0]

    mapping = map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="nutrition_info_query",
    )

    assert mapping["external_outcome"] == "no_mutation_query"
    assert mapping["ledger_status"] == "not_applicable"
    assert mapping["mutation_allowed"] is False


def test_brand_mentioned_drink_does_not_fall_through_to_generic_anchor_as_exact_claim() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u661f\u5df4\u514b\u62ff\u9435"))

    assert result.candidates == ()
    assert result.defer_reason == "exact_brand_lookup_deferred_to_b2_005"
    assert result.mutation_authority == "none"
