from __future__ import annotations

from pathlib import Path

from app.shared.infra.json_artifacts import read_json_artifact
from scripts.run_accurate_intake_websearch_live_diagnostic_bundle import main


def test_websearch_live_diagnostic_bundle_fixture_mode_builds_full_bundle(tmp_path: Path) -> None:
    exit_code = main(["--output-dir", str(tmp_path)])

    assert exit_code == 0
    manifest = read_json_artifact(
        tmp_path / "accurate_intake_websearch_live_diagnostic_bundle_manifest.json"
    )
    diagnostic = read_json_artifact(tmp_path / "accurate_intake_grokfast_websearch_packet_smoke.json")
    report = read_json_artifact(tmp_path / "accurate_intake_websearch_live_diagnostic_report.json")
    readiness = read_json_artifact(
        tmp_path / "accurate_intake_websearch_live_runner_readiness_packet.json"
    )

    assert manifest["bundle_status"] == "pass"
    assert manifest["mode"] == "fixture"
    assert manifest["live_provider_used"] is False
    assert manifest["live_websearch_used"] is False
    assert manifest["runtime_truth_changed"] is False
    assert manifest["runtime_mutation_attempted"] is False
    assert manifest["readiness_claimed"] is False
    assert manifest["seam_status"] == "fixture_only_live_not_checked"
    assert diagnostic["live_provider_used"] is False
    assert report["should_run_websearch_live_tool_loop"] is False
    assert readiness["ready_for_grokfast_websearch_packet_live_diagnostic"] is True


def test_websearch_live_diagnostic_bundle_live_mode_requires_explicit_allow_live(
    tmp_path: Path,
) -> None:
    exit_code = main(["--mode", "live", "--output-dir", str(tmp_path)])

    assert exit_code == 2
    manifest = read_json_artifact(
        tmp_path / "accurate_intake_websearch_live_diagnostic_bundle_manifest.json"
    )
    diagnostic = read_json_artifact(tmp_path / "accurate_intake_grokfast_websearch_packet_smoke.json")

    assert manifest["bundle_status"] == "blocked_or_failed"
    assert manifest["mode"] == "live"
    assert manifest["allow_live"] is False
    assert manifest["live_provider_used"] is False
    assert manifest["live_websearch_used"] is False
    assert manifest["runtime_truth_changed"] is False
    assert manifest["runtime_mutation_attempted"] is False
    assert diagnostic["status"] == "blocked"
    assert diagnostic["failure_family"] == "live_mode_requires_explicit_allow_live"


def test_websearch_live_diagnostic_bundle_records_all_required_artifact_refs(
    tmp_path: Path,
) -> None:
    main(["--output-dir", str(tmp_path)])

    manifest = read_json_artifact(
        tmp_path / "accurate_intake_websearch_live_diagnostic_bundle_manifest.json"
    )
    required_refs = {
        "case_matrix",
        "selected_extract",
        "extract_result",
        "review_packet",
        "preflight",
        "chain_status",
        "readiness",
        "diagnostic",
        "report",
    }

    assert set(manifest["artifacts"]) == required_refs
    for artifact_path in manifest["artifacts"].values():
        assert Path(artifact_path).exists()
