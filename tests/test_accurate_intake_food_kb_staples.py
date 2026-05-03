from __future__ import annotations

import json
from pathlib import Path

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


ROOT = Path(__file__).resolve().parents[1]
SMALL_ANCHOR_PATH = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"


@pytest.mark.parametrize(
    ("message", "expected_name", "required_followup"),
    [
        ("\u6211\u5403\u4e86\u4e00\u4efd\u86cb\u9905", "\u86cb\u9905", "ask_add_ons"),
        ("\u6211\u5403\u4e86\u4e00\u500b\u98ef\u7cf0", "\u98ef\u7cf0", "ask_filling"),
        ("\u6211\u5403\u4e86\u4e09\u660e\u6cbb", "\u4e09\u660e\u6cbb", "ask_filling"),
        ("\u6211\u5403\u4e86\u4e00\u4efd\u6ef7\u8089\u98ef", "\u6ef7\u8089\u98ef", "ask_rice_portion"),
        ("\u6211\u5403\u4e86\u6c34\u9903", "\u6c34\u9903", "ask_piece_count"),
        ("\u6211\u5403\u4e86\u4e00\u4efd\u934b\u8cbc", "\u934b\u8cbc", "ask_piece_count"),
        ("\u6211\u5403\u4e86\u4e00\u689d\u5730\u74dc", "\u5730\u74dc", "ask_size"),
    ],
)
def test_practical_staple_anchors_are_lookup_support_only(
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


def test_practical_staple_query_lookup_stays_non_authoritative() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u6ef7\u8089\u98ef\u591a\u5c11\u71b1\u91cf\uff1f"))

    assert result.defer_reason is None
    assert result.retrieval_context == "query_only_support"
    assert result.mutation_authority == "none"
    assert [candidate.canonical_name for candidate in result.candidates] == ["\u6ef7\u8089\u98ef"]
    assert result.candidates[0].support_role == "lookup_support_only"


@pytest.mark.parametrize(
    ("message", "expected_name", "expected_question"),
    [
        (
            "\u6211\u5403\u4e86\u86cb\u9905",
            "\u86cb\u9905",
            "\u8acb\u88dc\u5145\u52a0\u6599\u6216\u91ac\u6599\u3002",
        ),
        (
            "\u6211\u5403\u4e86\u98ef\u7cf0",
            "\u98ef\u7cf0",
            "\u8acb\u88dc\u5145\u5167\u9921\u6216\u5927\u5c0f\u3002",
        ),
        (
            "\u6211\u5403\u4e86\u4e09\u660e\u6cbb",
            "\u4e09\u660e\u6cbb",
            "\u8acb\u88dc\u5145\u5167\u9921\u6216\u91ac\u6599\u3002",
        ),
        (
            "\u6211\u5403\u4e86\u6ef7\u8089\u98ef",
            "\u6ef7\u8089\u98ef",
            "\u8acb\u88dc\u5145\u98ef\u91cf\u3001\u7897\u578b\u6216\u52a0\u6599\u3002",
        ),
        (
            "\u6211\u5403\u4e86\u6c34\u9903",
            "\u6c34\u9903",
            "\u8acb\u88dc\u5145\u9846\u6578\u6216\u5167\u9921\u3002",
        ),
        (
            "\u6211\u5403\u4e86\u934b\u8cbc",
            "\u934b\u8cbc",
            "\u8acb\u88dc\u5145\u9846\u6578\u6216\u5167\u9921\u3002",
        ),
        (
            "\u6211\u5403\u4e86\u5730\u74dc",
            "\u5730\u74dc",
            "\u8acb\u88dc\u5145\u5927\u5c0f\u6216\u4efd\u91cf\u3002",
        ),
    ],
)
def test_practical_staple_packets_synthesize_to_logged_optional_refinement(
    message: str,
    expected_name: str,
    expected_question: str,
) -> None:
    intent = build_retrieval_intent(message)
    anchor_result = lookup_anchor_candidates(intent)
    seeds = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)
    packets = tuple(add_hard_recheck_metadata(build_candidate_packet(seed)) for seed in seeds)
    consumption = consume_rechecked_packets(packets)

    manager_pass = synthesize_local_manager_pass(intent, consumption)

    assert len(consumption.accepted_packets) == 1
    assert consumption.accepted_packets[0]["accepted_usage"] == "anchor"
    item = manager_pass["item_results"][0]
    assert item["interpreted_food_identity"] == expected_name
    assert item["exactness_posture"] == "estimated"
    assert item["evidence_confidence"] == "moderate"
    assert item["evidence_used"][0]["usage"] == "anchor"
    assert item["suggested_followup_question"] == expected_question

    mapping = map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )

    assert mapping["external_outcome"] == "logged"
    assert mapping["ledger_status"] == "included"
    assert mapping["mutation_allowed"] is True
    assert mapping["followup_role"] == "precision_refinement"


def test_practical_staple_final_mapping_respects_write_owner_block() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u6ef7\u8089\u98ef")
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


def test_practical_staple_query_final_mapping_never_mutates() -> None:
    intent = build_retrieval_intent("\u6ef7\u8089\u98ef\u591a\u5c11\u71b1\u91cf\uff1f")
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


def test_small_anchor_seed_rows_do_not_encode_workflow_or_mutation_authority() -> None:
    rows = json.loads(SMALL_ANCHOR_PATH.read_text(encoding="utf-8-sig"))["anchors"]
    forbidden_fields = {
        "logged",
        "draft",
        "no_mutation",
        "workflow_effect",
        "final_action",
        "target_attachment",
        "mutation_authority",
        "decides_logged_or_draft",
    }

    for row in rows:
        assert forbidden_fields.isdisjoint(row), row.get("canonical_name")
