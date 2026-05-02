from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.nutrition.application.evidence_candidate_packetizer import (
    add_hard_recheck_metadata,
    build_candidate_packet,
)
from app.nutrition.application.evidence_packet_consumption import consume_rechecked_packets
from app.nutrition.application.exact_item_card_lookup import lookup_exact_item_card_candidates
from app.nutrition.application.final_mapping import map_final_item_result
from app.nutrition.application.local_synthesis import synthesize_local_manager_pass
from app.nutrition.application.packetizer_input_seed import (
    packetizer_input_seeds_from_anchor_lookup_result,
    packetizer_input_seeds_from_exact_item_lookup_result,
)
from app.nutrition.application.retrieval_intent import RetrievalIntent, build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates
from app.nutrition.infrastructure.local_seed_evidence_store import LocalSeedNutritionEvidenceStore


ROOT = Path(__file__).resolve().parents[1]
COVERAGE_MAP_PATH = ROOT / "docs" / "quality" / "food_knowledge_mvp_coverage_map.json"
FORBIDDEN_SEED_AUTHORITY_FIELDS = {
    "logged",
    "draft",
    "no_mutation",
    "workflow_effect",
    "final_action",
    "mutation_authority",
    "decides_logged_or_draft",
    "disposition",
    "external_outcome",
    "canonical_write_allowed",
    "ledger_mutation_allowed",
    "ledger_status",
    "mutation_result",
}


class _RecordingLocalSeedStore:
    def __init__(self) -> None:
        self._delegate = LocalSeedNutritionEvidenceStore()
        self.calls: list[str] = []

    def load_small_anchor_records(self) -> list[dict[str, Any]]:
        self.calls.append("small_anchor")
        return self._delegate.load_small_anchor_records()

    def load_exact_item_card_records(self) -> list[dict[str, Any]]:
        self.calls.append("exact_item_card")
        return self._delegate.load_exact_item_card_records()


def _load_coverage_map() -> dict[str, Any]:
    return json.loads(COVERAGE_MAP_PATH.read_text(encoding="utf-8"))


def _iter_mapping_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(str(key) for key in value)
        for nested in value.values():
            keys.update(_iter_mapping_keys(nested))
    elif isinstance(value, list):
        for item in value:
            keys.update(_iter_mapping_keys(item))
    return keys


def test_food_knowledge_mvp_map_declares_packet_guard_policy() -> None:
    coverage = _load_coverage_map()

    assert coverage["packet_guard_policy"] == {
        "seed_authority": "candidate_evidence_only",
        "seed_can_decide_logged_draft_or_no_mutation": False,
        "accepted_packet_required_for_synthesis": True,
        "rejected_candidate_citable_as_evidence": False,
        "no_accepted_packet_outcome": "insufficiency_or_clarify",
        "final_disposition_owner": "b2_final_mapping",
    }


def test_local_seed_records_do_not_contain_disposition_or_mutation_authority_fields() -> None:
    store = LocalSeedNutritionEvidenceStore()
    records = [
        *store.load_small_anchor_records(),
        *store.load_exact_item_card_records(),
    ]

    assert records
    for record in records:
        assert FORBIDDEN_SEED_AUTHORITY_FIELDS.isdisjoint(_iter_mapping_keys(record))


def test_mvp_foods_flow_through_evidence_store_port_before_packet_consumption() -> None:
    store = _RecordingLocalSeedStore()
    anchor_inputs = (
        "\u6211\u5403\u4e86\u8336\u8449\u86cb",
        "\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336",
        "\u6211\u5403\u4e86\u96de\u817f\u4fbf\u7576",
        "\u6211\u5403\u4e86\u9ebb\u8fa3\u81ed\u8c46\u8150",
    )

    for raw_input in anchor_inputs:
        anchor_result = lookup_anchor_candidates(
            build_retrieval_intent(raw_input),
            evidence_store=store,
        )
        seeds = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)
        packets = tuple(add_hard_recheck_metadata(build_candidate_packet(seed)) for seed in seeds)
        consumption = consume_rechecked_packets(packets)

        assert seeds
        assert consumption.accepted_packets
        assert all(packet["accepted_usage"] == "anchor" for packet in consumption.accepted_packets)

    exact_result = lookup_exact_item_card_candidates(
        RetrievalIntent(
            base_dish="\u725b\u4e3c",
            aliases=["\u677e\u5c4b\u7279\u76db\u725b\u4e3c"],
            brand_hint="\u677e\u5c4b",
            size_hint="\u7279\u76db",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        ),
        evidence_store=store,
    )
    exact_seeds = packetizer_input_seeds_from_exact_item_lookup_result(exact_result)
    exact_packets = tuple(add_hard_recheck_metadata(build_candidate_packet(seed)) for seed in exact_seeds)
    exact_consumption = consume_rechecked_packets(exact_packets)

    assert exact_seeds
    assert exact_consumption.accepted_packets
    assert exact_consumption.accepted_packets[0]["accepted_usage"] == "exact"
    assert "small_anchor" in store.calls
    assert "exact_item_card" in store.calls


def test_rejected_exact_candidate_is_not_cited_and_maps_to_draft() -> None:
    intent = build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f")
    exact_result = lookup_exact_item_card_candidates(intent)
    seed = packetizer_input_seeds_from_exact_item_lookup_result(exact_result)[0]
    packet = build_candidate_packet(seed)
    packet["serving_basis"] = ""
    rechecked = add_hard_recheck_metadata(packet)
    consumption = consume_rechecked_packets((rechecked,))

    manager_pass = synthesize_local_manager_pass(intent, consumption)
    item = manager_pass["item_results"][0]
    final_mapping = map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )

    assert consumption.accepted_packets == ()
    assert item["exactness_posture"] == "unresolved"
    assert item["likely_kcal"] is None
    assert item["evidence_used"] == []
    assert item["rejected_candidates"][0]["packet_id"] == "pkt_exact_item_exact_starbucks_latte_iced_large"
    assert final_mapping["external_outcome"] == "draft"
    assert final_mapping["mutation_allowed"] is False


def test_semantic_only_no_accepted_packet_clarifies_without_seed_disposition() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u6ef7\u5473")
    anchor_result = lookup_anchor_candidates(intent)
    consumption = consume_rechecked_packets(())

    manager_pass = synthesize_local_manager_pass(
        intent,
        consumption,
        clarify_support=anchor_result.clarify_support,
    )
    item = manager_pass["item_results"][0]
    final_mapping = map_final_item_result(
        item,
        canonical_write_decision={"can_write_canonical": True},
        interaction_type="food_logging",
    )

    assert anchor_result.clarify_support is not None
    assert item["exactness_posture"] == "unresolved"
    assert item["likely_kcal"] is None
    assert item["evidence_used"] == []
    assert item["suggested_followup_question"]
    assert final_mapping["external_outcome"] == "draft"
    assert final_mapping["mutation_allowed"] is False
