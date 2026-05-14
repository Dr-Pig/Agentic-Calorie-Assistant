from __future__ import annotations

from pathlib import Path

from scripts.run_current_shell_self_use_golden_set_e2e import (
    build_current_shell_golden_set_e2e_report,
)


def test_golden_set_e2e_runner_uses_real_estimate_entrypoint_and_request_trace(
    tmp_path: Path,
) -> None:
    report = build_current_shell_golden_set_e2e_report(
        case_ids=["GS5"],
        db_path=tmp_path / "gs-e2e.sqlite3",
        output_path=tmp_path / "gs-e2e-report.json",
        trace_artifact_path=tmp_path / "gs-e2e-trace.json",
        replay_output_path=tmp_path / "gs-e2e-replay.json",
        provider_mode="scripted",
        local_date="2026-05-14",
    )

    assert report["artifact_type"] == "current_shell_self_use_golden_set_e2e_report"
    assert report["claim_scope"] == "real_entrypoint_runtime_projection"
    assert report["runner_inferred_semantics"] is False
    assert report["semantic_keyword_oracle_used"] is False
    assert report["live_invoked_by_runner"] is False
    assert report["summary"]["selected_case_count"] == 1
    assert report["summary"]["request_trace_case_count"] == 1
    assert report["trace_artifact"]["claim_scope"] == "real_request_trace_projection"
    assert report["trace_artifact"]["cases"][0]["case_id"] == "GS5"
    assert report["case_runs"][0]["entrypoint"] == "/estimate"
    assert report["case_runs"][0]["turns"][0]["request_trace_exists"] is True
    assert Path(report["case_runs"][0]["turns"][0]["request_trace_path"]).exists()
    assert report["replay"]["summary"]["source_case_count"] == 1
    assert report["replay"]["summary"]["strict_golden_set_replay_passed"] is False
    gs5 = next(case for case in report["replay"]["cases"] if case["case_id"] == "GS5")
    assert gs5["status"] == "blocked"
    assert any(blocker.startswith("fixture_decisions.") for blocker in gs5["blockers"])
