from __future__ import annotations

"""B2 manager contract parity gate.

This module is test-owned only. It must not be imported by runtime code or by
producer fallback paths.

The first live provider pilot may start only after this suite is green, and it
must stay limited to:
- 茶葉蛋
- bare 滷味

That later pilot must still call the LLM only after packet consumption and
before final logged/draft mapping.
"""

from typing import Any

import pytest

from app.nutrition.application.b2_candidate_packetizer import (
    add_hard_recheck_metadata,
    build_candidate_packet,
)
from app.nutrition.application.b2_local_synthesis import synthesize_b2_local_manager_pass2
from app.nutrition.application.b2_packet_consumption import consume_rechecked_packets
from app.nutrition.application.b2_manager_provider_bridge import (
    run_b2_manager_pass2_with_provider,
)
from app.nutrition.application.exact_item_card_lookup import lookup_exact_item_card_candidates
from app.nutrition.application.packetizer_input_seed import (
    packetizer_input_seeds_from_anchor_lookup_result,
    packetizer_input_seeds_from_exact_item_lookup_result,
)
from app.nutrition.application.retrieval_intent import build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates


class DeterministicFixturePass2Provider:
    """Test-owned fake provider. It only returns explicit fixture payloads."""

    def __init__(self, *, payload: object, trace: dict[str, object] | None = None) -> None:
        self._payload = payload
        self._trace = trace or {}

    async def complete_with_trace(self, **kwargs: object) -> tuple[object, dict[str, object]]:
        trace = {
            "provider": "builderspace",
            "model": "deepseek",
            "temperature": 0.0,
            "max_tokens": kwargs.get("max_tokens"),
            "response_format": {"type": "json_schema"},
            "timeout": None,
            "retry_policy": {"max_attempts": 1},
            "tool_choice": "none",
            "request_id": "fake-b2-parity-req",
        }
        trace.update(self._trace)
        return self._payload, trace


def _assert_b2_provider_contract_parity(
    local_result: dict[str, object],
    provider_result: dict[str, object],
) -> None:
    local_items = _normalize_item_results(local_result.get("item_results") or [])
    provider_items = _normalize_item_results(provider_result.get("item_results") or [])

    assert provider_result.get("item_results_source") == "manager_pass_2_payload"
    assert provider_result.get("item_results_owner_class") == "runtime_payload"
    assert provider_result.get("forbidden_mutation_fields_present") == []
    assert local_items == provider_items


def _normalize_item_results(item_results: object) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in item_results or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "interpreted_food_identity": item.get("interpreted_food_identity"),
                "assumed_composition": item.get("assumed_composition"),
                "kcal_range": item.get("kcal_range"),
                "likely_kcal": item.get("likely_kcal"),
                "exactness_posture": item.get("exactness_posture"),
                "evidence_confidence": item.get("evidence_confidence"),
                "suggested_followup_question": item.get("suggested_followup_question"),
                "uncertainty_reason": item.get("uncertainty_reason"),
                "evidence_used": _normalize_evidence_used(item.get("evidence_used")),
                "rejected_candidates": _normalize_rejected_candidates(item.get("rejected_candidates")),
            }
        )
    return normalized


def _normalize_evidence_used(evidence_used: object) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in evidence_used or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "packet_id": item.get("packet_id"),
                "source_type": item.get("source_type"),
                "usage": item.get("usage"),
            }
        )
    return normalized


def _normalize_rejected_candidates(rejected_candidates: object) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in rejected_candidates or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "packet_id": item.get("packet_id"),
                "risk_type": item.get("risk_type"),
                "reason": item.get("reason"),
                "canonical_name": item.get("canonical_name"),
            }
        )
    return normalized


def _generic_anchor_case(message: str) -> tuple[Any, Any, Any]:
    intent = build_retrieval_intent(message)
    anchor_result = lookup_anchor_candidates(intent)
    seed = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)[0]
    packet = add_hard_recheck_metadata(build_candidate_packet(seed))
    consumption = consume_rechecked_packets((packet,))
    return intent, consumption, None


def _clarify_only_case() -> tuple[Any, Any, Any]:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u6ef7\u5473")
    anchor_result = lookup_anchor_candidates(intent)
    consumption = consume_rechecked_packets(())
    return intent, consumption, anchor_result.clarify_support


def _rejected_exact_case() -> tuple[Any, Any, Any]:
    intent = build_retrieval_intent("\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f")
    exact_result = lookup_exact_item_card_candidates(intent)
    seed = packetizer_input_seeds_from_exact_item_lookup_result(exact_result)[0]
    packet = build_candidate_packet(seed)
    packet["serving_basis"] = ""
    rechecked = add_hard_recheck_metadata(packet)
    consumption = consume_rechecked_packets((rechecked,))
    return intent, consumption, None


async def _provider_result_from_local_reference(
    intent: Any,
    consumption: Any,
    *,
    clarify_support: Any = None,
    provider_payload: dict[str, object] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    local_result = synthesize_b2_local_manager_pass2(
        intent,
        consumption,
        clarify_support=clarify_support,
    )
    payload = provider_payload or {"item_results": local_result["item_results"]}
    provider = DeterministicFixturePass2Provider(payload=payload)
    provider_result = await run_b2_manager_pass2_with_provider(
        provider,
        intent,
        consumption,
        clarify_support=clarify_support,
    )
    return local_result, provider_result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case_factory",
    (
        lambda: _generic_anchor_case("\u6211\u5403\u4e86\u8336\u8449\u86cb"),
        lambda: _generic_anchor_case("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336"),
        lambda: _generic_anchor_case("\u6211\u5403\u4e86\u96de\u817f\u4fbf\u7576"),
        _clarify_only_case,
        _rejected_exact_case,
    ),
)
async def test_b2_manager_contract_parity_matches_local_reference(case_factory) -> None:
    intent, consumption, clarify_support = case_factory()
    local_result, provider_result = await _provider_result_from_local_reference(
        intent,
        consumption,
        clarify_support=clarify_support,
    )

    _assert_b2_provider_contract_parity(local_result, provider_result)


@pytest.mark.asyncio
async def test_b2_manager_contract_parity_fails_on_wrong_exactness_posture() -> None:
    intent, consumption, clarify_support = _generic_anchor_case("\u6211\u5403\u4e86\u8336\u8449\u86cb")
    local_result = synthesize_b2_local_manager_pass2(intent, consumption, clarify_support=clarify_support)
    bad_payload = {"item_results": [dict(local_result["item_results"][0], exactness_posture="provisional")]}
    _, provider_result = await _provider_result_from_local_reference(
        intent,
        consumption,
        clarify_support=clarify_support,
        provider_payload=bad_payload,
    )

    with pytest.raises(AssertionError):
        _assert_b2_provider_contract_parity(local_result, provider_result)


@pytest.mark.asyncio
async def test_b2_manager_contract_parity_fails_on_wrong_likely_kcal() -> None:
    intent, consumption, clarify_support = _generic_anchor_case("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336")
    local_result = synthesize_b2_local_manager_pass2(intent, consumption, clarify_support=clarify_support)
    bad_payload = {"item_results": [dict(local_result["item_results"][0], likely_kcal=999)]}
    _, provider_result = await _provider_result_from_local_reference(
        intent,
        consumption,
        clarify_support=clarify_support,
        provider_payload=bad_payload,
    )

    with pytest.raises(AssertionError):
        _assert_b2_provider_contract_parity(local_result, provider_result)


@pytest.mark.asyncio
async def test_b2_manager_contract_parity_fails_on_wrong_followup_output() -> None:
    intent, consumption, clarify_support = _clarify_only_case()
    local_result = synthesize_b2_local_manager_pass2(intent, consumption, clarify_support=clarify_support)
    bad_payload = {
        "item_results": [dict(local_result["item_results"][0], suggested_followup_question="\u4e0d\u6b63\u78ba\u7684\u8ffd\u554f")]
    }
    _, provider_result = await _provider_result_from_local_reference(
        intent,
        consumption,
        clarify_support=clarify_support,
        provider_payload=bad_payload,
    )

    with pytest.raises(AssertionError):
        _assert_b2_provider_contract_parity(local_result, provider_result)


@pytest.mark.asyncio
async def test_b2_manager_contract_parity_fails_when_forbidden_mutation_field_is_present() -> None:
    intent, consumption, clarify_support = _generic_anchor_case("\u6211\u5403\u4e86\u8336\u8449\u86cb")
    local_result = synthesize_b2_local_manager_pass2(intent, consumption, clarify_support=clarify_support)
    bad_payload = {
        "item_results": local_result["item_results"],
        "mutation_result": {"ledger_item_ids": ["should-not-run"]},
    }
    _, provider_result = await _provider_result_from_local_reference(
        intent,
        consumption,
        clarify_support=clarify_support,
        provider_payload=bad_payload,
    )

    with pytest.raises(AssertionError):
        _assert_b2_provider_contract_parity(local_result, provider_result)
