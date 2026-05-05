from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_cache_rate_license_wall import (
    build_websearch_cache_rate_license_wall,
)
from app.nutrition.application.websearch_source_adapter_preflight import (
    build_websearch_source_adapter_preflight,
)


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


def test_websearch_source_adapter_preflight_blocks_without_websearch_status() -> None:
    artifact = build_websearch_source_adapter_preflight()

    assert artifact["artifact_type"] == "accurate_intake_websearch_source_adapter_preflight_v1"
    assert artifact["status"] == "blocked"
    assert artifact["ready_for_live_search_diagnostic"] is False
    assert "websearch_status_not_clear:inspect_websearch_status_packet" in artifact["blockers"]
    assert artifact["live_websearch_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["readiness_claimed"] is False


def test_websearch_source_adapter_preflight_passes_after_status_and_cache_wall_clear() -> None:
    artifact = build_websearch_source_adapter_preflight(
        websearch_status_packet=_websearch_status_clear(),
        cache_rate_license_artifact=build_websearch_cache_rate_license_wall(),
    )

    assert artifact["status"] == "pass"
    assert artifact["ready_for_live_search_diagnostic"] is True
    assert artifact["ready_for_runtime_truth"] is False
    assert artifact["next_required_slice"] == "websearch_live_search_diagnostic_canary"
    assert artifact["summary"]["adapter_case_count"] == 2
    assert artifact["summary"]["fail_count"] == 0
    assert artifact["source_adapter_contract"]["dependency"] == "WebSearchPort"
    assert artifact["source_adapter_contract"]["manager_packet_role"] == (
        "compact_candidate_packet_only"
    )
    assert artifact["diagnostic_contract"]["live_call_allowed_by_this_artifact"] is False
    assert artifact["diagnostic_contract"]["requires_explicit_live_permission"] is True
    assert artifact["diagnostic_contract"]["cache_required"] is True
    assert artifact["diagnostic_contract"]["max_search_results"] == 5
    for case in artifact["adapter_cases"]:
        request = case["request"]
        assert request["auto_parameters"] is False
        assert request["include_answer"] is False
        assert request["include_raw_content"] is False
        assert request["runtime_truth_allowed"] is False
        assert case["cache_key"].startswith("websearch_candidate_v1:")


def test_websearch_source_adapter_preflight_blocks_unsafe_websearch_status() -> None:
    for unsafe_key in (
        "live_websearch_used",
        "runtime_truth_changed",
        "mutation_changed",
        "shared_contract_changed",
        "readiness_claimed",
    ):
        status = _websearch_status_clear()
        status[unsafe_key] = True
        artifact = build_websearch_source_adapter_preflight(
            websearch_status_packet=status,
            cache_rate_license_artifact=build_websearch_cache_rate_license_wall(),
        )
        assert artifact["status"] == "blocked"
        assert "websearch_status_not_clear:inspect_websearch_status_packet" in artifact["blockers"]


def test_websearch_source_adapter_preflight_blocks_if_live_diagnostic_gate_not_pass() -> None:
    status = _websearch_status_clear()
    status["live_diagnostic_gate"]["status"] = "candidate_boundary_blocked"
    status["live_diagnostic_gate"]["blocked"] = True
    status["live_diagnostic_gate"]["can_expand"] = False
    status["next_required_slices"] = ["narrow_websearch_packet_boundary_or_prompt_probe"]

    artifact = build_websearch_source_adapter_preflight(
        websearch_status_packet=status,
        cache_rate_license_artifact=build_websearch_cache_rate_license_wall(),
    )

    assert artifact["status"] == "blocked"
    assert (
        "websearch_status_not_clear:narrow_websearch_packet_boundary_or_prompt_probe"
        in artifact["blockers"]
    )


def test_websearch_source_adapter_preflight_blocks_cache_wall_drift() -> None:
    cache_wall = build_websearch_cache_rate_license_wall()
    cache_wall["live_websearch_used"] = True

    artifact = build_websearch_source_adapter_preflight(
        websearch_status_packet=_websearch_status_clear(),
        cache_rate_license_artifact=cache_wall,
    )

    assert artifact["status"] == "blocked"
    assert "cache_rate_license_wall_not_clear:inspect_websearch_cache_rate_license_wall" in artifact["blockers"]
    assert artifact["ready_for_live_search_diagnostic"] is False


def test_websearch_source_adapter_preflight_rejects_unexpected_artifacts() -> None:
    try:
        build_websearch_source_adapter_preflight(websearch_status_packet={"artifact_type": "wrong"})
    except ValueError as exc:
        assert "unsupported_websearch_source_adapter_status_packet" in str(exc)
    else:
        raise AssertionError("unexpected WebSearch status artifact type must fail")

    try:
        build_websearch_source_adapter_preflight(
            websearch_status_packet=_websearch_status_clear(),
            cache_rate_license_artifact={"artifact_type": "wrong"},
        )
    except ValueError as exc:
        assert "unsupported_websearch_source_adapter_cache_wall" in str(exc)
    else:
        raise AssertionError("unexpected cache wall artifact type must fail")


def test_websearch_source_adapter_preflight_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_source_adapter_preflight import main

    status_path = tmp_path / "websearch_status.json"
    cache_wall_path = tmp_path / "cache_wall.json"
    output = tmp_path / "source_adapter_preflight.json"
    write_json_artifact(status_path, _websearch_status_clear())
    write_json_artifact(cache_wall_path, build_websearch_cache_rate_license_wall())

    assert (
        main(
            [
                "--websearch-status-packet",
                str(status_path),
                "--cache-rate-license-artifact",
                str(cache_wall_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_source_adapter_preflight_v1"
    assert artifact["status"] == "pass"
    assert artifact["next_required_slice"] == "websearch_live_search_diagnostic_canary"


def test_websearch_source_adapter_preflight_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_source_adapter_preflight.py"),
        Path("scripts/build_accurate_intake_websearch_source_adapter_preflight.py"),
    ]
    forbidden = [
        "Tavily",
        "BuilderSpaceAdapter",
        "requests.",
        "httpx.",
        "allow_live",
        "run_live",
        "ManagerContextPacket",
        "NutritionEvidenceStorePort",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
