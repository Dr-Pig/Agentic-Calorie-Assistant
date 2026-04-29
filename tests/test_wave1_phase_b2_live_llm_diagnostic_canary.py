from __future__ import annotations

import json
from pathlib import Path
import asyncio

import pytest

from scripts.build_wave1_phase_b2_evidence_synthesis_smoke import build_phase_b2_synthetic_smoke_report
from scripts.live_diagnostic_decision_pack import VERDICT_DIAGNOSTIC_OBSERVATION, VERDICT_READINESS_BLOCKER
from scripts.run_wave1_phase_b2_live_llm_diagnostic_canary import (
    DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID,
    build_missing_token_report,
    build_provider_request_payload_for_case,
    provider_profile,
    run_b2_live_llm_diagnostic_canary,
)


class _FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *, timeout: int | None = None) -> None:
        self.timeout = timeout
        self.requests: list[dict[str, object]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]) -> _FakeResponse:
        self.requests.append({"url": url, "headers": headers, "json": json})
        content = {
            "item_results": [
                {
                    "interpreted_food_identity": "diagnostic item",
                    "exactness_posture": "estimated",
                    "likely_kcal": 450,
                    "kcal_range": [350, 550],
                    "evidence_used": [{"packet_id": "pkt_generic_anchor_custom_drink_boba_milk_tea"}],
                    "uncertainty_reason": "fake live diagnostic response",
                    "suggested_followup_question": "請補充糖度和杯型。",
                }
            ]
        }
        return _FakeResponse(
            {
                "choices": [{"message": {"content": json_module_dumps(content)}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            }
        )


def json_module_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _b1_green_handoff_snapshot() -> dict[str, object]:
    return {
        "b1_gate_scope": "Phase B-1 minimal tool-loop full natural-probe",
        "smoke_artifact": "artifacts/phase_b1_full_smoke.json",
        "readiness_artifact": "artifacts/phase_b1_readiness.json",
        "ready_for_phase_b1_implementation": True,
        "blockers": [],
        "not_claiming": "whole Wave 1 completion",
    }


def _phase_b2_report() -> dict[str, object]:
    return build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())


def _case_by_id(report: dict[str, object], case_id: str) -> dict[str, object]:
    return next(case for case in report["cases"] if case["case_id"] == case_id)


def test_b2_live_diagnostic_default_profile_is_grokfast_primary_not_selection() -> None:
    profile = provider_profile(DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)

    assert profile["provider_profile_id"] == "builderspace-grok-4-fast-b2-diagnostic"
    assert profile["model"] == "grok-4-fast"
    assert profile["provider_profile_role"] == "b2_live_diagnostic_primary"
    assert profile["production_selected"] is False
    assert profile["not_production_selection"] is True
    assert profile["not_readiness_evidence"] is True
    assert profile["allow_expensive_model_probe"] is False


def test_missing_token_report_does_not_fallback_to_fake_or_claim_live() -> None:
    report = build_missing_token_report(
        phase_b2_report=_phase_b2_report(),
        provider_profile_id=DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID,
        payload_artifact_id="artifact-x",
    )

    assert report["provider_mode"] == "not_invoked"
    assert report["live_invoked"] is False
    assert report["failure_family"] == "missing_provider_token"
    assert report["verdict_category"] == VERDICT_READINESS_BLOCKER
    assert report["readiness_claimed"] is False
    assert report["diagnostic_scope"] == "b2_packet_synthesis_only"
    assert report["readiness_scope"] == "none"
    assert report["user_facing_enabled"] is False
    assert report["mutation_enabled"] is False


def test_provider_request_payload_uses_deterministic_packet_contract_without_mapping() -> None:
    phase_b2_report = _phase_b2_report()
    payload = build_provider_request_payload_for_case(_case_by_id(phase_b2_report, "B2-009"))

    assert payload["case_id"] == "B2-009"
    assert payload["diagnostic_scope"] == "b2_packet_synthesis_only"
    assert payload["mutation_forbidden"] is True
    assert payload["authority"] == {
        "mutation_authority": False,
        "ledger_truth_authority": False,
        "product_semantic_authority": False,
        "source_priority_authority": False,
    }
    assert payload["accepted_packets"] == []
    assert payload["rejected_candidates"][0]["packet_id"] == _case_by_id(phase_b2_report, "B2-009")["packets"][0]["packet_id"]
    assert payload["final_mapping"] == "not_provided_to_live_diagnostic"


def test_provider_request_payload_uses_clarify_only_contract_for_bare_self_selected_basket() -> None:
    phase_b2_report = _phase_b2_report()
    payload = build_provider_request_payload_for_case(_case_by_id(phase_b2_report, "B2-004"))

    assert payload["case_id"] == "B2-004"
    assert payload["contract_type"] == "clarify_only"
    assert payload["ask_first_required"] is True
    assert payload["synthesis_allowed"] is False
    assert payload["item_results_allowed"] is False
    assert payload["estimate_allowed"] is False
    assert payload["kcal_range_allowed"] is False
    assert payload["expected_output"] == "ask_followup_for_items_and_portions"
    assert payload["required_output"]["item_results_allowed"] is False
    assert payload["required_output"]["estimate_allowed"] is False
    assert payload["required_output"]["kcal_range_allowed"] is False
    assert payload["required_output"]["expected_output"] == "ask_followup_for_items_and_portions"
    assert payload["final_mapping"] == "not_provided_to_live_diagnostic"


def test_live_canary_fake_http_response_is_validated_by_contract_harness(tmp_path: Path) -> None:
    report = asyncio.run(run_b2_live_llm_diagnostic_canary(
        phase_b2_report=_phase_b2_report(),
        token="test-token",
        provider_profile_id=DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID,
        async_client_factory=_FakeAsyncClient,
        selected_case_ids=("B2-002",),
        payload_artifact_id="artifact-y",
    ))

    assert report["provider_mode"] == "live"
    assert report["live_invoked"] is True
    assert report["live_provider_diagnostic_complete"] is True
    assert report["readiness_claimed"] is False
    assert report["provider_profile_id"] == DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID
    assert report["provider_profile_model"] == "grok-4-fast"
    assert report["provider_profile_role"] == "b2_live_diagnostic_primary"
    assert report["diagnostic_scope"] == "b2_packet_synthesis_only"
    assert report["readiness_scope"] == "none"
    assert report["user_facing_enabled"] is False
    assert report["mutation_enabled"] is False
    assert report["case_results"][0]["schema_status"] == "strict_pass"
    assert report["case_results"][0]["usage"] == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    assert report["verdict_category"] == VERDICT_DIAGNOSTIC_OBSERVATION


def test_live_canary_runner_source_does_not_import_final_mapping_or_semantic_register() -> None:
    source = Path("scripts/run_wave1_phase_b2_live_llm_diagnostic_canary.py").read_text(encoding="utf-8")

    assert "b2_final_mapping" not in source
    assert "WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER" not in source
