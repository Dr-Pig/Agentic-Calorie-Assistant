from __future__ import annotations

from pathlib import Path

from app.shared.infra.json_artifacts import read_json_artifact


def test_evidence_track_live_diagnostic_bundle_runner_fixture_mode(
    tmp_path: Path,
) -> None:
    from scripts.run_accurate_intake_evidence_track_live_diagnostic_bundle import main

    output_dir = tmp_path.parent / "etl-fixture"

    assert main(["--mode", "fixture", "--output-dir", str(output_dir)]) == 0

    manifest = read_json_artifact(output_dir / "evidence_track_live_manifest.json")
    handoff = read_json_artifact(output_dir / "evidence_track_live_handoff.json")

    assert manifest["artifact_type"] == "accurate_intake_evidence_track_live_manifest_v1"
    assert manifest["bundle_status"] == "pass"
    assert manifest["mode"] == "fixture"
    assert manifest["runtime_truth_changed"] is False
    assert manifest["runtime_mutation_attempted"] is False
    assert manifest["readiness_claimed"] is False
    assert manifest["next_recommended_slice"] == "grokfast_fooddb_packet_live_diagnostic"
    assert Path(manifest["artifacts"]["fooddb_manifest"]).exists()
    assert Path(manifest["artifacts"]["websearch_manifest"]).exists()
    assert Path(manifest["artifacts"]["handoff"]).exists()

    assert handoff["artifact_type"] == "accurate_intake_evidence_track_live_handoff_v1"
    assert handoff["status"] == "fixture_only_live_not_checked"
    assert handoff["selected_next_step"] == "grokfast_fooddb_packet_live_diagnostic"


def test_evidence_track_live_diagnostic_bundle_runner_live_requires_allow_live(
    tmp_path: Path,
) -> None:
    from scripts.run_accurate_intake_evidence_track_live_diagnostic_bundle import main

    output_dir = tmp_path.parent / "etl-live"

    assert main(["--mode", "live", "--output-dir", str(output_dir)]) == 2

    manifest = read_json_artifact(output_dir / "evidence_track_live_manifest.json")
    handoff = read_json_artifact(output_dir / "evidence_track_live_handoff.json")

    assert manifest["bundle_status"] == "blocked_or_failed"
    assert manifest["mode"] == "live"
    assert manifest["allow_live"] is False
    assert manifest["next_recommended_slice"] == "grokfast_fooddb_packet_live_diagnostic"
    assert handoff["status"] == "blocked"
    assert "fooddb_bundle_not_pass" in handoff["blockers"]
