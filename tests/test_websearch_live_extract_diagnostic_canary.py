from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.nutrition.application.websearch_live_extract_diagnostic_canary import (
    build_websearch_live_extract_diagnostic_canary,
)


class _FixtureExtractPort:
    def __init__(
        self,
        *,
        provider: str | None = "fixture",
        configured: bool | None = True,
        rows: list[Any] | None = None,
    ) -> None:
        self.provider = provider
        self.configured = configured
        self.rows = rows
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        profile: dict[str, Any] = {}
        if self.provider is not None:
            profile["provider"] = self.provider
        if self.configured is not None:
            profile["configured"] = self.configured
        return profile

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        self.calls.append({"urls": urls, "query": query})
        if self.rows is not None:
            return self.rows
        return [
            {
                "source_url": urls[0],
                "canonical_name": query,
                "matched_name": query,
                "serving_basis_candidate": "per_serving",
                "kcal_value_candidate": 400,
                "kcal_text_present": True,
                "identity_text_present": True,
                "raw_extract_ref": f"fixture_extract:{urls[0]}",
            }
        ]


def _gate() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_extract_diagnostic_gate_v1",
        "status": "pass",
        "blockers": [],
        "ready_for_trace_only_live_extract_diagnostic": True,
        "ready_for_runtime_truth": False,
        "ready_for_runtime_mutation": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_web_activation_approved": False,
        "runtime_web_activation_recommended": False,
        "readiness_claimed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "shared_contract_changed": False,
        "next_required_slice": "websearch_live_extract_diagnostic_canary_harness",
        "review_packet_refs": [
            {
                "packet_id": "pkt_exact_card_review_abc",
                "source_url": "https://example.test/menu",
                "canonical_name": "Test Brand Latte",
                "packet_digest": "digest123",
            }
        ],
    }


@pytest.mark.asyncio
async def test_live_extract_diagnostic_canary_runs_fixture_port_trace_only() -> None:
    port = _FixtureExtractPort()

    artifact = await build_websearch_live_extract_diagnostic_canary(
        diagnostic_gate_artifact=_gate(),
        live_permission_granted=True,
        extract_port=port,
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_live_extract_diagnostic_canary_v1"
    assert artifact["status"] == "pass"
    assert artifact["extract_port_used"] is True
    assert artifact["live_extract_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["case_count"] == 1
    assert artifact["summary"]["pass_count"] == 1
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["cases"][0]["extract_result_role"] == "review_candidate_only"
    assert artifact["cases"][0]["runtime_truth_allowed"] is False
    assert artifact["cases"][0]["raw_content_in_manager_context"] is False
    assert artifact["next_required_slice"] == "websearch_live_extract_diagnostic_report"
    assert len(port.calls) == 1


@pytest.mark.asyncio
async def test_live_extract_diagnostic_canary_blocks_without_permission_or_gate() -> None:
    port = _FixtureExtractPort()

    artifact = await build_websearch_live_extract_diagnostic_canary(
        diagnostic_gate_artifact=_gate(),
        live_permission_granted=False,
        extract_port=port,
    )

    assert artifact["status"] == "blocked"
    assert "live_extract_permission_required" in artifact["blockers"]
    assert artifact["extract_port_used"] is False
    assert port.calls == []

    blocked_gate = _gate()
    blocked_gate["status"] = "blocked"
    artifact = await build_websearch_live_extract_diagnostic_canary(
        diagnostic_gate_artifact=blocked_gate,
        live_permission_granted=True,
        extract_port=port,
    )
    assert artifact["status"] == "blocked"
    assert "diagnostic_gate_not_clear:inspect_websearch_live_extract_diagnostic_gate" in artifact["blockers"]


@pytest.mark.asyncio
async def test_live_extract_diagnostic_canary_blocks_missing_gate_without_crash() -> None:
    port = _FixtureExtractPort()

    artifact = await build_websearch_live_extract_diagnostic_canary(
        diagnostic_gate_artifact=None,
        live_permission_granted=True,
        extract_port=port,
    )

    assert artifact["status"] == "blocked"
    assert "diagnostic_gate_not_clear:inspect_websearch_live_extract_diagnostic_gate" in artifact["blockers"]
    assert "diagnostic_gate:artifact_missing" in artifact["blockers"]
    assert artifact["extract_port_used"] is False
    assert port.calls == []


@pytest.mark.asyncio
async def test_live_extract_diagnostic_canary_reports_external_extract_usage_without_truth() -> None:
    artifact = await build_websearch_live_extract_diagnostic_canary(
        diagnostic_gate_artifact=_gate(),
        live_permission_granted=True,
        extract_port=_FixtureExtractPort(provider="external_extract_fixture"),
    )

    assert artifact["status"] == "pass"
    assert artifact["extract_port_used"] is True
    assert artifact["live_extract_used"] is True
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["ready_for_runtime_truth"] is False


@pytest.mark.asyncio
async def test_live_extract_diagnostic_canary_treats_unknown_provider_as_live_usage() -> None:
    artifact = await build_websearch_live_extract_diagnostic_canary(
        diagnostic_gate_artifact=_gate(),
        live_permission_granted=True,
        extract_port=_FixtureExtractPort(provider=None, configured=True),
    )

    assert artifact["status"] == "pass"
    assert artifact["extract_port_used"] is True
    assert artifact["live_extract_used"] is True
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False


@pytest.mark.asyncio
async def test_live_extract_diagnostic_canary_blocks_unconfigured_port_before_call() -> None:
    port = _FixtureExtractPort(provider="fixture", configured=False)

    artifact = await build_websearch_live_extract_diagnostic_canary(
        diagnostic_gate_artifact=_gate(),
        live_permission_granted=True,
        extract_port=port,
    )

    assert artifact["status"] == "blocked"
    assert "extract_port_not_configured" in artifact["blockers"]
    assert artifact["extract_port_used"] is False
    assert port.calls == []


@pytest.mark.asyncio
async def test_live_extract_diagnostic_canary_blocks_unusable_extract_rows() -> None:
    artifact = await build_websearch_live_extract_diagnostic_canary(
        diagnostic_gate_artifact=_gate(),
        live_permission_granted=True,
        extract_port=_FixtureExtractPort(
            rows=[
                {
                    "source_url": "https://example.test/menu",
                    "serving_basis_candidate": "per_serving",
                    "identity_text_present": True,
                    "raw_content": "full page body must not enter Manager context",
                }
            ]
        ),
    )

    assert artifact["status"] == "blocked"
    assert "canary_case_failed:live_extract_review_candidate:pkt_exact_card_review_abc" in artifact["blockers"]
    assert artifact["cases"][0]["usable_review_candidate_count"] == 0
    assert artifact["cases"][0]["candidate_rows"][0]["raw_content_included"] is True
    assert artifact["websearch_runtime_truth_allowed"] is False


@pytest.mark.asyncio
async def test_live_extract_diagnostic_canary_blocks_malformed_extract_rows_without_crash() -> None:
    artifact = await build_websearch_live_extract_diagnostic_canary(
        diagnostic_gate_artifact=_gate(),
        live_permission_granted=True,
        extract_port=_FixtureExtractPort(rows=[None, "bad-row"]),
    )

    assert artifact["status"] == "blocked"
    assert "canary_case_failed:live_extract_review_candidate:pkt_exact_card_review_abc" in artifact["blockers"]
    assert artifact["cases"][0]["candidate_rows"][0]["malformed_row_type"] == "NoneType"
    assert artifact["cases"][0]["candidate_rows"][1]["malformed_row_type"] == "str"
    assert artifact["websearch_runtime_truth_allowed"] is False


@pytest.mark.asyncio
async def test_live_extract_diagnostic_canary_blocks_top_level_none_extract_rows_without_crash() -> None:
    class _MalformedRowsPort:
        def __init__(self, rows: Any) -> None:
            self.rows = rows

        def readiness(self) -> dict[str, Any]:
            return {"provider": "fixture", "configured": True}

        async def extract_rows(self, *, urls: list[str], query: str) -> Any:
            return self.rows

    for malformed_rows, expected_type in (
        (None, "NoneType"),
        (
            (
                {
                    "source_url": "https://example.test/menu",
                    "serving_basis_candidate": "per_serving",
                    "kcal_value_candidate": 400,
                    "identity_text_present": True,
                },
            ),
            "tuple",
        ),
        (
            {
                "source_url": "https://example.test/menu",
                "serving_basis_candidate": "per_serving",
                "kcal_value_candidate": 400,
                "identity_text_present": True,
            },
            "dict",
        ),
        ("bad-top-level", "str"),
    ):
        artifact = await build_websearch_live_extract_diagnostic_canary(
            diagnostic_gate_artifact=_gate(),
            live_permission_granted=True,
            extract_port=_MalformedRowsPort(malformed_rows),
        )

        assert artifact["status"] == "blocked"
        assert (
            "canary_case_failed:live_extract_review_candidate:pkt_exact_card_review_abc"
            in artifact["blockers"]
        )
        assert artifact["cases"][0]["candidate_rows"][0]["malformed_row_type"] == expected_type


@pytest.mark.asyncio
async def test_live_extract_diagnostic_canary_blocks_gate_runtime_or_readiness_overclaims() -> None:
    for key in (
        "live_provider_used",
        "live_websearch_used",
        "source_live_websearch_used",
        "live_extract_used",
        "runtime_truth_changed",
        "mutation_changed",
        "runtime_mutation_allowed",
        "websearch_runtime_truth_allowed",
        "runtime_web_activation_recommended",
        "ready_for_runtime_truth",
        "ready_for_runtime_mutation",
        "readiness_claimed",
        "manager_context_changed",
        "manager_context_packet_changed",
        "manager_context_packet_schema_changed",
        "packetizer_format_changed",
        "packetizer_changed",
        "shared_contract_changed",
        "nutrition_evidence_store_port_changed",
        "basket_semantics_changed",
        "product_loop_activated",
        "product_loop_integration_claimed",
        "ce_activated",
        "context_engineering_changed",
        "webshell_activated",
        "webshell_changed",
        "exact_card_created",
    ):
        gate = _gate()
        gate[key] = True
        port = _FixtureExtractPort()
        artifact = await build_websearch_live_extract_diagnostic_canary(
            diagnostic_gate_artifact=gate,
            live_permission_granted=True,
            extract_port=port,
        )
        assert artifact["status"] == "blocked"
        assert artifact["extract_port_used"] is False
        assert port.calls == []
        assert any(item.startswith("diagnostic_gate:") for item in artifact["blockers"])


def test_live_extract_diagnostic_canary_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_websearch_live_extract_diagnostic_canary import main

    gate_path = tmp_path / "gate.json"
    output = tmp_path / "canary.json"
    write_json_artifact(gate_path, _gate())

    assert (
        main(
            [
                "--diagnostic-gate",
                str(gate_path),
                "--live-permission-granted",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_live_extract_diagnostic_canary_v1"
    assert artifact["status"] == "pass"
    assert artifact["live_extract_used"] is False


def test_live_extract_diagnostic_canary_has_no_concrete_live_provider_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_live_extract_diagnostic_canary.py"),
        Path("scripts/run_accurate_intake_websearch_live_extract_diagnostic_canary.py"),
    ]
    forbidden = [
        "Tavily",
        "tavily",
        "OpenAI",
        "openai",
        "BuilderSpaceAdapter",
        "import requests",
        "from requests",
        "requests.",
        "import httpx",
        "from httpx",
        "httpx.",
        "ManagerContextPacket",
        "NutritionEvidenceStorePort",
        "PacketReadyAnchor",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
