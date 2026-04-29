from __future__ import annotations

from typing import Any

import pytest

from app.nutrition.application.b2_candidate_packetizer import (
    add_hard_recheck_metadata,
    build_candidate_packet,
)
from app.nutrition.application.b2_packet_consumption import consume_rechecked_packets
from app.nutrition.application.b2_pass2_provider_bridge import (
    build_b2_manager_pass2_request_payload,
    run_b2_manager_pass2_with_provider,
)
from app.nutrition.application.packetizer_input_seed import (
    packetizer_input_seeds_from_anchor_lookup_result,
)
from app.nutrition.application.retrieval_intent import build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates


class DeterministicFakePass2Provider:
    """Test-owned seam double that only returns explicit fixture payloads."""

    def __init__(self, *, payload: object, trace: dict[str, object] | None = None) -> None:
        self._payload = payload
        self._trace = trace or {}
        self.calls: list[dict[str, object]] = []

    async def complete_with_trace(self, **kwargs: object) -> tuple[object, dict[str, object]]:
        self.calls.append(dict(kwargs))
        trace = {
            "provider": "builderspace",
            "model": "deepseek",
            "temperature": 0.0,
            "max_tokens": kwargs.get("max_tokens"),
            "response_format": {"type": "json_schema"},
            "timeout": None,
            "retry_policy": {"max_attempts": 1},
            "tool_choice": "none",
            "request_id": "fake-b2-pass2-req",
        }
        trace.update(self._trace)
        return self._payload, trace


def _tea_egg_packet_consumption():
    intent = build_retrieval_intent("我吃了茶葉蛋")
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    return intent, consume_rechecked_packets((packet,))


@pytest.mark.asyncio
async def test_b2_pass2_provider_bridge_uses_explicit_provider_item_results_without_local_fallback() -> None:
    intent, consumption = _tea_egg_packet_consumption()
    explicit_item_results = [
        {
            "interpreted_food_identity": "茶葉蛋",
            "assumed_composition": "provider fixture only",
            "kcal_range": [81, 81],
            "likely_kcal": 81,
            "exactness_posture": "estimated",
            "evidence_confidence": "moderate",
            "evidence_used": [],
            "rejected_candidates": [],
            "uncertainty_reason": "fixture_payload_only",
            "suggested_followup_question": "這是測 seam 的假資料。",
        }
    ]
    provider = DeterministicFakePass2Provider(payload={"item_results": explicit_item_results})

    manager_pass_2 = await run_b2_manager_pass2_with_provider(provider, intent, consumption)

    assert provider.calls[0]["stage"] == "intake_manager_round"
    request_payload = provider.calls[0]["user_payload"]
    assert request_payload["constraints"]["phase_b2_manager_role"] == "pass_2_synthesis"
    assert request_payload["accepted_packets"][0]["canonical_name"] == "茶葉蛋"
    assert manager_pass_2["manager_role"] == "pass_2_synthesis"
    assert manager_pass_2["item_results"] == explicit_item_results
    assert manager_pass_2["item_results_source"] == "manager_pass_2_payload"
    assert manager_pass_2["item_results_owner_class"] == "runtime_payload"
    assert manager_pass_2["provider_params"]["provider"] == "builderspace"
    assert manager_pass_2["provider_params"]["model"] == "deepseek"
    assert manager_pass_2["provider_params"]["request_id"] == "fake-b2-pass2-req"
    assert manager_pass_2["mutation_attempted"] is False
    assert manager_pass_2["mutation_authority"] is False
    assert manager_pass_2["ledger_truth_authority"] is False
    assert manager_pass_2["source_priority_authority"] is False
    assert manager_pass_2["product_semantic_authority"] is False


@pytest.mark.asyncio
async def test_b2_pass2_provider_bridge_passes_clarify_support_outside_packet_lane() -> None:
    intent = build_retrieval_intent("我吃了滷味")
    anchor_result = lookup_anchor_candidates(intent)
    consumption = consume_rechecked_packets(())
    explicit_item_results = [
        {
            "interpreted_food_identity": "滷味",
            "assumed_composition": None,
            "kcal_range": None,
            "likely_kcal": None,
            "exactness_posture": "unresolved",
            "evidence_confidence": "insufficient",
            "evidence_used": [],
            "rejected_candidates": [],
            "uncertainty_reason": "fixture_clarify_only",
            "suggested_followup_question": "請列出品項與大致份量。",
        }
    ]
    provider = DeterministicFakePass2Provider(payload={"item_results": explicit_item_results})

    manager_pass_2 = await run_b2_manager_pass2_with_provider(
        provider,
        intent,
        consumption,
        clarify_support=anchor_result.clarify_support,
    )

    request_payload = provider.calls[0]["user_payload"]
    assert request_payload["accepted_packets"] == []
    assert request_payload["clarify_support"]["canonical_name"] == "滷味"
    assert request_payload["clarify_support"]["clarify_required"] is True
    assert manager_pass_2["item_results"] == explicit_item_results
    assert manager_pass_2["item_results_source"] == "manager_pass_2_payload"
    assert manager_pass_2["item_results_owner_class"] == "runtime_payload"


@pytest.mark.asyncio
async def test_b2_pass2_provider_bridge_does_not_author_item_results_when_provider_omits_them() -> None:
    intent, consumption = _tea_egg_packet_consumption()
    provider = DeterministicFakePass2Provider(payload={"response_summary": "no item results"})

    manager_pass_2 = await run_b2_manager_pass2_with_provider(provider, intent, consumption)

    assert manager_pass_2["item_results"] == []
    assert manager_pass_2["item_results_source"] == "none"
    assert manager_pass_2["item_results_owner_class"] == "none"
    assert manager_pass_2["forbidden_mutation_fields_present"] == []


@pytest.mark.asyncio
async def test_b2_pass2_provider_bridge_flags_forbidden_mutation_fields_without_executing_them() -> None:
    intent, consumption = _tea_egg_packet_consumption()
    explicit_item_results = [
        {
            "interpreted_food_identity": "茶葉蛋",
            "assumed_composition": None,
            "kcal_range": [80, 80],
            "likely_kcal": 80,
            "exactness_posture": "estimated",
            "evidence_confidence": "strong",
            "evidence_used": [],
            "rejected_candidates": [],
            "uncertainty_reason": "fixture_payload_only",
            "suggested_followup_question": None,
        }
    ]
    provider = DeterministicFakePass2Provider(
        payload={
            "item_results": explicit_item_results,
            "mutation_result": {"ledger_item_ids": ["should-not-run"]},
        }
    )

    manager_pass_2 = await run_b2_manager_pass2_with_provider(provider, intent, consumption)

    assert manager_pass_2["item_results"] == explicit_item_results
    assert manager_pass_2["forbidden_mutation_fields_present"] == ["mutation_result"]
    assert manager_pass_2["item_results_owner_class"] == "runtime_payload"
    assert manager_pass_2["mutation_attempted"] is False


def test_b2_pass2_request_payload_keeps_packet_results_and_clarify_support_explicit() -> None:
    intent, consumption = _tea_egg_packet_consumption()
    payload = build_b2_manager_pass2_request_payload(intent, consumption)

    assert payload["intent"]["base_dish"] == "茶葉蛋"
    assert payload["accepted_packets"][0]["canonical_name"] == "茶葉蛋"
    assert payload["rejected_candidates"] == []
    assert payload["clarify_support"] is None
    assert payload["mutation_forbidden"] is True
    assert payload["constraints"]["phase_b2_manager_role"] == "pass_2_synthesis"
