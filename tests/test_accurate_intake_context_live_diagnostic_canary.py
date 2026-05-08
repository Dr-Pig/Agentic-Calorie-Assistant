from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_canary import (
    DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID,
    build_context_live_diagnostic_canary_report,
    build_missing_token_report,
    build_provider_request_payload,
    provider_profile,
)
from app.composition.accurate_intake_context_live_provider_input_preflight import (
    build_context_live_provider_input_preflight_artifact,
)
from scripts.run_accurate_intake_context_live_diagnostic_canary import (
    run_context_live_diagnostic_canary,
)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _fixture_response(provider_input: dict[str, Any]) -> dict[str, Any]:
    expected = _dict(provider_input.get("expected_semantic_contract"))
    sidecar = _dict(provider_input.get("manager_context_sidecar"))
    prior_context = _dict(sidecar.get("prior_context"))
    candidates = prior_context.get("target_candidates") if isinstance(prior_context.get("target_candidates"), list) else []
    if sidecar.get("ambiguity_expected") is True:
        target_resolution = {"status": "ambiguous", "candidate_ids": candidates}
        clarification_question = "Which item should I change?"
    elif sidecar.get("target_candidates_expected") is True:
        target_resolution = {"status": "candidates_available", "candidate_ids": candidates}
        clarification_question = None
    else:
        target_resolution = {"status": "not_applicable", "candidate_ids": []}
        clarification_question = None
    return {
        "case_id": provider_input.get("case_id"),
        "manager_intent": expected.get("manager_intent"),
        "workflow_effect": expected.get("workflow_effect"),
        "target_resolution": target_resolution,
        "mutation_request": {"requested": False, "reason": "context_only_live_diagnostic"},
        "clarification_question": clarification_question,
        "confidence_notes": "fake async client output for canary contract test",
    }


class _FakeResponse:
    status_code = 200

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "choices": [{"message": {"content": json.dumps(self._payload, ensure_ascii=False)}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }


class _FakeAsyncClient:
    requests: list[dict[str, Any]] = []

    def __init__(self, **_: Any) -> None:
        self.requests = []
        _FakeAsyncClient.requests = self.requests

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> _FakeResponse:
        user_content = json["messages"][1]["content"]
        request_payload = __import__("json").loads(user_content)
        response = _fixture_response(request_payload)
        self.requests.append({"url": url, "headers": headers, "json": json, "request_payload": request_payload})
        return _FakeResponse(response)


def test_context_live_canary_provider_profile_is_grokfast_diagnostic_only() -> None:
    profile = provider_profile()

    assert profile["provider_profile_id"] == DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID
    assert profile["model"] == "grok-4-fast"
    assert profile["provider_profile_role"] == "accurate_intake_context_live_diagnostic"
    assert profile["production_selected"] is False
    assert profile["readiness_owner"] is False
    assert profile["schema_mode"] == "json_object"


def test_context_live_canary_missing_token_report_does_not_claim_readiness() -> None:
    report = build_missing_token_report()

    assert report["artifact_type"] == "accurate_intake_context_live_diagnostic_canary"
    assert report["status"] == "not_invoked"
    assert report["provider_mode"] == "not_invoked"
    assert report["live_llm_invoked"] is False
    assert report["live_provider_invoked"] is False
    assert report["fooddb_used"] is False
    assert report["web_tavily_used"] is False
    assert report["mutation_changed"] is False
    assert report["manager_context_packet_schema_changed"] is False
    assert "readiness_claimed" not in report
    assert "product_readiness_claimed" not in report
    assert "private_self_use_approved" not in report
    assert report["blockers"] == ["missing_provider_token"]


def test_context_live_canary_builds_provider_payload_without_truth_or_mutation_authority() -> None:
    preflight = build_context_live_provider_input_preflight_artifact()
    provider_input = preflight["provider_inputs"][3]
    payload = build_provider_request_payload(provider_input)

    assert payload["diagnostic_scope"] == "current_shell_compatibility_context_only_live_intent_probe"
    assert payload["case_id"] == provider_input["case_id"]
    assert payload["authority"]["semantic_owner"] == "live_manager_provider"
    assert payload["authority"]["deterministic_layer_may_select_intent"] is False
    assert payload["authority"]["frontend_may_select_target"] is False
    assert payload["authority"]["mutation_authority"] is False
    assert payload["authority"]["fooddb_truth_authority"] is False
    assert payload["non_claims"]["fooddb_used"] is False
    assert payload["non_claims"]["manager_context_packet_schema_changed"] is False


async def test_context_live_canary_runs_fake_async_client_as_live_contract_probe() -> None:
    preflight = build_context_live_provider_input_preflight_artifact()

    report = await run_context_live_diagnostic_canary(
        context_live_provider_input_preflight=preflight,
        token="fake-token",
        async_client_factory=_FakeAsyncClient,
    )

    assert report["status"] == "live_diagnostic_pass"
    assert report["provider_mode"] == "live"
    assert report["live_llm_invoked"] is True
    assert report["live_provider_invoked"] is True
    assert report["provider_profile_model"] == "grok-4-fast"
    assert report["fooddb_used"] is False
    assert report["web_tavily_used"] is False
    assert report["mutation_changed"] is False
    assert report["manager_context_packet_schema_changed"] is False
    assert "product_readiness_claimed" not in report
    assert "private_self_use_approved" not in report
    assert report["response_contract_status"] == "pass"
    assert report["summary"]["provider_output_count"] == len(preflight["provider_inputs"])
    assert report["summary"]["blocked_response_count"] == 0
    assert len(_FakeAsyncClient.requests) == len(preflight["provider_inputs"])
    assert all(
        request["request_payload"]["tool_policy"]["tools_available"] == []
        for request in _FakeAsyncClient.requests
    )


def test_context_live_canary_blocks_provider_mutation_and_wrong_intent() -> None:
    preflight = build_context_live_provider_input_preflight_artifact()
    provider_outputs = [_fixture_response(row) for row in preflight["provider_inputs"]]
    provider_outputs[0] = {
        **provider_outputs[0],
        "manager_intent": "food_log_candidate",
        "mutation_request": {"requested": True, "reason": "bad_live_output"},
    }

    report = build_context_live_diagnostic_canary_report(
        context_live_provider_input_preflight=preflight,
        provider_outputs=provider_outputs,
        live_invoked=True,
    )

    case_id = str(provider_outputs[0]["case_id"])
    assert report["status"] == "blocked"
    assert report["failure_family"] == "context_live_response_contract_blocked"
    assert f"{case_id}.manager_intent_mismatch" in report["blockers"]
    assert f"{case_id}.mutation_requested" in report["blockers"]
    assert "product_readiness_claimed" not in report
    assert "private_self_use_approved" not in report


def test_context_live_canary_accepts_live_manager_resolved_target_status() -> None:
    preflight = build_context_live_provider_input_preflight_artifact()
    provider_outputs = [_fixture_response(row) for row in preflight["provider_inputs"]]
    target_case = next(
        index
        for index, row in enumerate(provider_outputs)
        if row["case_id"] == "context_live_004_remove_previous_item"
    )
    provider_outputs[target_case] = {
        **dict(provider_outputs[target_case]),
        "target_resolution": {"status": "resolved", "candidate_ids": ["boba"]},
    }

    report = build_context_live_diagnostic_canary_report(
        context_live_provider_input_preflight=preflight,
        provider_outputs=provider_outputs,
        live_invoked=True,
    )

    assert report["status"] == "live_diagnostic_pass"
    assert report["response_contract_status"] == "pass"


def test_context_live_canary_cli_writes_not_invoked_artifact_without_token(tmp_path: Path, monkeypatch: Any) -> None:
    from scripts.run_accurate_intake_context_live_diagnostic_canary import main

    output_path = tmp_path / "context-live-canary.json"
    monkeypatch.delenv("AI_BUILDER_TOKEN", raising=False)

    assert main(["--output", str(output_path)]) == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["status"] == "not_invoked"
    assert artifact["failure_family"] == "missing_provider_token"
    assert "readiness_claimed" not in artifact


def test_context_live_canary_cli_rejects_unknown_case_id(tmp_path: Path, monkeypatch: Any) -> None:
    from scripts.run_accurate_intake_context_live_diagnostic_canary import main

    output_path = tmp_path / "context-live-canary.json"
    monkeypatch.delenv("AI_BUILDER_TOKEN", raising=False)

    try:
        main(["--case-id", "ad_hoc_easy_case", "--output", str(output_path)])
    except ValueError as exc:
        assert "Unsupported context live diagnostic case_id=ad_hoc_easy_case" in str(exc)
    else:
        raise AssertionError("unknown case id should fail fast")


def test_context_live_canary_source_stays_out_of_fooddb_and_shared_contracts() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_context_live_diagnostic_canary.py"),
        Path("scripts/run_accurate_intake_context_live_diagnostic_canary.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "from app.nutrition",
        "import app.nutrition",
        "fooddb_used = True",
        "web_tavily_used = True",
        "mutation_changed = True",
        "manager_context_packet_schema_changed = True",
        "private_self_use_approved = True",
    ]

    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source
