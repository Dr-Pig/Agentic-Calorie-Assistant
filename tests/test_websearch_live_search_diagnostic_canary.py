from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.nutrition.application.websearch_live_search_diagnostic_canary import (
    build_websearch_live_search_diagnostic_canary,
)
from app.nutrition.application.websearch_source_adapter_preflight import (
    build_websearch_source_adapter_preflight,
)
from app.nutrition.application.websearch_cache_rate_license_wall import (
    build_websearch_cache_rate_license_wall,
)


class _FakeSearchPort:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self._hits = hits
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"provider": "fixture", "configured": True}

    async def search_hits(self, *, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        self.calls.append({"query": query, "max_results": max_results})
        return list(self._hits)


class _FakeExtractPort:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"provider": "fixture", "configured": True}

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        self.calls.append({"urls": list(urls), "query": query})
        return list(self._rows)


class _ReadinessRaisesSearchPort(_FakeSearchPort):
    def readiness(self) -> dict[str, Any]:
        raise AssertionError("readiness must not run before gates are clear")


class _ReadinessRaisesExtractPort(_FakeExtractPort):
    def readiness(self) -> dict[str, Any]:
        raise AssertionError("readiness must not run before gates are clear")


class _NoCallsAttributeSearchPort:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self._hits = hits

    def readiness(self) -> dict[str, Any]:
        return {"provider": "fixture", "configured": True}

    async def search_hits(self, *, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        return list(self._hits)


class _NoCallsAttributeExtractPort:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def readiness(self) -> dict[str, Any]:
        return {"provider": "fixture", "configured": True}

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        return list(self._rows)


def _websearch_status_clear() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
        "live_websearch_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "readiness_claimed": False,
        "upstream_gate": {
            "status": "clear_for_websearch_lane",
            "blocked": False,
            "next_required_slice": "grokfast_websearch_packet_live_diagnostic",
        },
        "live_diagnostic_gate": {
            "status": "live_diagnostic_pass",
            "blocked": False,
            "can_expand": True,
            "next_required_slice": "websearch_live_search_preflight_or_candidate_source_adapter",
        },
        "next_required_slices": ["websearch_live_search_preflight_or_candidate_source_adapter"],
    }


def _preflight_pass() -> dict:
    return build_websearch_source_adapter_preflight(
        websearch_status_packet=_websearch_status_clear(),
        cache_rate_license_artifact=build_websearch_cache_rate_license_wall(),
    )


def _search_hits() -> list[dict[str, Any]]:
    return [
        {
            "title": "Test Brand Matcha Latte",
            "url": "https://brand.example/products/matcha-latte",
            "snippet": "deterministic official result",
            "score": 0.92,
            "officialness": "official",
            "brand_detected": "Test Brand",
            "serving_basis": "per_cup",
            "identity_confidence": "high",
            "license_status": "public_menu_page",
            "robots_status": "allowed",
            "nutrition_fields_present": ["kcal"],
            "raw_ref": "raw:search:fixture",
        }
    ]


def _extract_rows() -> list[dict[str, Any]]:
    return [
        {
            "url": "https://brand.example/products/matcha-latte",
            "title": "Test Brand Matcha Latte",
            "source_type": "official",
            "officialness": "official",
            "serving_basis": "per_cup",
            "brand_detected": "Test Brand",
            "raw_content": "400 kcal",
            "raw_ref": "raw:extract:fixture",
        }
    ]


@pytest.mark.asyncio
async def test_websearch_live_search_canary_blocks_without_preflight() -> None:
    artifact = await build_websearch_live_search_diagnostic_canary(
        preflight_artifact=None,
        live_permission_granted=True,
        search_port=_ReadinessRaisesSearchPort(_search_hits()),
        extract_port=_ReadinessRaisesExtractPort(_extract_rows()),
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_live_search_diagnostic_canary_v1"
    assert artifact["status"] == "blocked"
    assert artifact["live_websearch_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["blockers"] == ["preflight_not_clear:inspect_websearch_source_adapter_preflight"]


@pytest.mark.asyncio
async def test_websearch_live_search_canary_requires_explicit_permission() -> None:
    search_port = _FakeSearchPort(_search_hits())
    extract_port = _FakeExtractPort(_extract_rows())

    artifact = await build_websearch_live_search_diagnostic_canary(
        preflight_artifact=_preflight_pass(),
        live_permission_granted=False,
        search_port=search_port,
        extract_port=extract_port,
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["live_search_permission_required"]
    assert artifact["summary"]["search_port_call_count"] == 0
    assert artifact["summary"]["extract_port_call_count"] == 0
    assert search_port.calls == []
    assert extract_port.calls == []


@pytest.mark.asyncio
async def test_websearch_live_search_canary_does_not_call_port_readiness_before_permission() -> None:
    artifact = await build_websearch_live_search_diagnostic_canary(
        preflight_artifact=_preflight_pass(),
        live_permission_granted=False,
        search_port=_ReadinessRaisesSearchPort(_search_hits()),
        extract_port=_ReadinessRaisesExtractPort(_extract_rows()),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["live_search_permission_required"]
    assert artifact["summary"]["search_port_call_count"] == 0
    assert artifact["summary"]["extract_port_call_count"] == 0


@pytest.mark.asyncio
async def test_websearch_live_search_canary_runs_trace_only_with_injected_ports() -> None:
    search_port = _FakeSearchPort(_search_hits())
    extract_port = _FakeExtractPort(_extract_rows())

    artifact = await build_websearch_live_search_diagnostic_canary(
        preflight_artifact=_preflight_pass(),
        live_permission_granted=True,
        search_port=search_port,
        extract_port=extract_port,
    )

    assert artifact["status"] == "pass"
    assert artifact["classification"] == "diagnostic_canary_harness_only"
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["search_port_used"] is True
    assert artifact["extract_port_used"] is True
    assert artifact["ready_for_runtime_truth"] is False
    assert artifact["next_required_slice"] == "websearch_live_search_diagnostic_report"
    assert artifact["summary"]["case_count"] == 1
    assert artifact["summary"]["pass_count"] == 1
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert search_port.calls == [{"query": "Test BrandMatcha Latte", "max_results": 5}]
    assert extract_port.calls == [
        {
            "urls": ["https://brand.example/products/matcha-latte"],
            "query": "Test BrandMatcha Latte",
        }
    ]
    case = artifact["cases"][0]
    assert case["status"] == "pass"
    assert case["trace"]["attempted"] is True
    assert case["trace"]["accepted_extract_packet_id"].startswith("pkt_web_extract_")
    assert case["trace"]["truth_boundary"]["web_candidate_truth_authority"] is False
    assert case["trace"]["truth_boundary"]["accepted_extract_packet_truth_authority"] is False
    assert case["runtime_truth_allowed"] is False
    assert case["runtime_mutation_allowed"] is False


@pytest.mark.asyncio
async def test_websearch_live_search_canary_counts_port_calls_with_owned_meter() -> None:
    artifact = await build_websearch_live_search_diagnostic_canary(
        preflight_artifact=_preflight_pass(),
        live_permission_granted=True,
        search_port=_NoCallsAttributeSearchPort(_search_hits()),
        extract_port=_NoCallsAttributeExtractPort(_extract_rows()),
    )

    assert artifact["status"] == "pass"
    assert artifact["search_port_used"] is True
    assert artifact["extract_port_used"] is True
    assert artifact["summary"]["search_port_call_count"] == 1
    assert artifact["summary"]["extract_port_call_count"] == 1


@pytest.mark.asyncio
async def test_websearch_live_search_canary_blocks_preflight_truth_or_readiness_drift() -> None:
    for unsafe_key in (
        "live_websearch_used",
        "runtime_truth_changed",
        "runtime_mutation_allowed",
        "readiness_claimed",
    ):
        preflight = _preflight_pass()
        preflight[unsafe_key] = True
        artifact = await build_websearch_live_search_diagnostic_canary(
            preflight_artifact=preflight,
            live_permission_granted=True,
            search_port=_ReadinessRaisesSearchPort(_search_hits()),
            extract_port=_ReadinessRaisesExtractPort(_extract_rows()),
        )
        assert artifact["status"] == "blocked"
        assert artifact["blockers"] == [
            "preflight_not_clear:inspect_websearch_source_adapter_preflight"
        ]


@pytest.mark.asyncio
async def test_websearch_live_search_canary_blocks_without_ports() -> None:
    artifact = await build_websearch_live_search_diagnostic_canary(
        preflight_artifact=_preflight_pass(),
        live_permission_granted=True,
        search_port=None,
        extract_port=None,
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["extract_port_unavailable", "search_port_unavailable"]


def test_websearch_live_search_canary_script_roundtrip_blocks_without_permission(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_websearch_live_search_diagnostic_canary import main

    preflight_path = tmp_path / "preflight.json"
    output = tmp_path / "canary.json"
    write_json_artifact(preflight_path, _preflight_pass())

    assert (
        main(
            [
                "--preflight-artifact",
                str(preflight_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_live_search_diagnostic_canary_v1"
    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["live_search_permission_required"]


def test_websearch_live_search_canary_script_roundtrip_runs_fixture_when_permissioned(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_websearch_live_search_diagnostic_canary import main

    preflight_path = tmp_path / "preflight.json"
    output = tmp_path / "canary.json"
    write_json_artifact(preflight_path, _preflight_pass())

    assert (
        main(
            [
                "--preflight-artifact",
                str(preflight_path),
                "--live-permission-granted",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["status"] == "pass"
    assert artifact["summary"]["pass_count"] == 1
    assert artifact["live_websearch_used"] is False
    assert "api_key" not in output.read_text(encoding="utf-8")


def test_websearch_live_search_canary_has_no_external_provider_imports_or_shared_contract_changes() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_live_search_diagnostic_canary.py"),
        Path("scripts/run_accurate_intake_websearch_live_search_diagnostic_canary.py"),
    ]
    forbidden = [
        "Tavily",
        "BuilderSpaceAdapter",
        "requests.",
        "httpx.",
        "ManagerContextPacket",
        "NutritionEvidenceStorePort",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
