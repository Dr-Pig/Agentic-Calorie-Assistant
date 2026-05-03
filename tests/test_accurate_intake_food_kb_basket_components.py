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
from app.nutrition.application.retrieval_intent import RetrievalIntent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates


@pytest.mark.parametrize(
    ("item_name", "expected_hints"),
    [
        ("\u767e\u9801\u8c46\u8150", {"luwei_component", "malatang_component"}),
        ("\u9b77\u9b5a", {"luwei_component", "fried_snack_component"}),
        ("\u7c73\u8178", {"luwei_component", "fried_snack_component"}),
        ("\u9ed1\u8f2a", {"luwei_component", "oden_component"}),
        ("\u9ad8\u9e97\u83dc", {"luwei_component", "malatang_component"}),
        ("\u9d28\u8840", {"malatang_component", "spicy_hotpot_component"}),
        ("\u51ac\u7c89", {"malatang_component", "hotpot_component"}),
        ("\u9999\u83c7", {"luwei_component", "malatang_component"}),
    ],
)
def test_practical_basket_components_are_lookup_support_only(
    item_name: str,
    expected_hints: set[str],
) -> None:
    result = lookup_anchor_candidates(_listed_item_intent(item_name))

    assert result.defer_reason is None
    assert result.clarify_support is None
    assert result.retrieval_context == "logging_support"
    assert result.mutation_authority == "none"
    assert [candidate.canonical_name for candidate in result.candidates] == [item_name]

    candidate = result.candidates[0]
    assert candidate.dish_type == "listed_item"
    assert candidate.composition_posture == "listed_item_component"
    assert candidate.support_role == "lookup_support_only"
    assert candidate.truth_level == "anchor"
    assert candidate.source_posture == "generic_anchor_seed"
    assert set(candidate.semantic_hints) >= expected_hints


@pytest.mark.parametrize(
    "item_name",
    [
        "\u767e\u9801\u8c46\u8150",
        "\u9b77\u9b5a",
        "\u7c73\u8178",
        "\u9ed1\u8f2a",
        "\u9ad8\u9e97\u83dc",
        "\u9d28\u8840",
        "\u51ac\u7c89",
        "\u9999\u83c7",
    ],
)
def test_practical_basket_component_packets_can_log_when_write_owner_allows(item_name: str) -> None:
    intent = _listed_item_intent(item_name)
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))

    manager_pass = synthesize_local_manager_pass(intent, consumption)

    assert consumption.accepted_packets[0]["accepted_usage"] == "anchor"
    item = manager_pass["item_results"][0]
    assert item["interpreted_food_identity"] == item_name
    assert item["assumed_composition"] == "listed item"
    assert item["exactness_posture"] == "estimated"
    assert item["evidence_used"][0]["usage"] == "anchor"

    mapping = map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )

    assert mapping["external_outcome"] == "logged"
    assert mapping["ledger_status"] == "included"
    assert mapping["mutation_allowed"] is True


def test_practical_basket_component_query_final_mapping_never_mutates() -> None:
    intent = RetrievalIntent(
        base_dish="\u6ef7\u5473",
        aliases=[],
        brand_hint=None,
        size_hint=None,
        modifier_hints=[],
        listed_items=["\u767e\u9801\u8c46\u8150"],
        retrieval_goal="listed_item_lookup",
    )
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


def _listed_item_intent(item_name: str) -> RetrievalIntent:
    return RetrievalIntent(
        base_dish="\u6ef7\u5473",
        aliases=[],
        brand_hint=None,
        size_hint=None,
        modifier_hints=[],
        listed_items=[item_name],
        retrieval_goal="listed_item_lookup",
    )
