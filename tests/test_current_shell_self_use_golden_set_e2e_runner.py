from __future__ import annotations

from pathlib import Path

from scripts.run_current_shell_self_use_golden_set_e2e import (
    _select_cases,
    build_current_shell_golden_set_e2e_report,
)
from app.composition.current_shell_golden_set_grader import load_golden_set_manifest


def test_golden_set_e2e_runner_can_select_websearch_extension_cases() -> None:
    selected = _select_cases(load_golden_set_manifest(), ["GSW1", "GSW3"])

    assert [case["case_id"] for case in selected] == ["GSW1", "GSW3"]


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


def test_golden_set_e2e_runner_seeds_gs9_recent_committed_meal_as_context_only(
    tmp_path: Path,
) -> None:
    report = build_current_shell_golden_set_e2e_report(
        case_ids=["GS9"],
        db_path=tmp_path / "gs9-e2e.sqlite3",
        output_path=tmp_path / "gs9-e2e-report.json",
        trace_artifact_path=tmp_path / "gs9-e2e-trace.json",
        replay_output_path=tmp_path / "gs9-e2e-replay.json",
        provider_mode="scripted",
        local_date="2026-05-14",
    )

    case_trace = report["trace_artifact"]["cases"][0]
    context_packet = case_trace["current_turn_context_packet"]
    runtime_summary = context_packet["current_turn_runtime_summary"]

    assert report["runner_inferred_semantics"] is False
    assert report["semantic_keyword_oracle_used"] is False
    assert runtime_summary["recent_committed_meal_count"] == 1
    assert context_packet["active_meal_thread_ref"]["mutation_authority"] is False
    assert context_packet["active_meal_thread_ref"]["read_only"] is True
    assert context_packet["recent_committed_meal_refs"][0]["mutation_authority"] is False
    assert context_packet["recent_committed_meal_refs"][0]["read_only"] is True
    assert "intent_type" not in context_packet["active_meal_thread_ref"]
    assert "final_action" not in context_packet["active_meal_thread_ref"]
    assert "workflow_effect" not in context_packet["active_meal_thread_ref"]


def test_golden_set_e2e_runner_seeds_gs12_current_day_meals_as_context_only(
    tmp_path: Path,
) -> None:
    report = build_current_shell_golden_set_e2e_report(
        case_ids=["GS12"],
        db_path=tmp_path / "gs12-e2e.sqlite3",
        output_path=tmp_path / "gs12-e2e-report.json",
        trace_artifact_path=tmp_path / "gs12-e2e-trace.json",
        replay_output_path=tmp_path / "gs12-e2e-replay.json",
        provider_mode="scripted",
        local_date="2026-05-14",
    )

    case_trace = report["trace_artifact"]["cases"][0]
    context_packet = case_trace["current_turn_context_packet"]
    runtime_summary = context_packet["current_turn_runtime_summary"]
    budget_snapshot = context_packet["current_budget_snapshot"]

    assert report["runner_inferred_semantics"] is False
    assert report["semantic_keyword_oracle_used"] is False
    assert runtime_summary["recent_committed_meal_count"] >= 2
    assert runtime_summary["recent_item_target_count"] >= 2
    assert budget_snapshot["active_meal_count"] >= 2
    assert budget_snapshot["consumed_kcal"] > 0
    assert context_packet["recent_committed_meal_refs"][0]["mutation_authority"] is False
    assert context_packet["recent_committed_meal_refs"][0]["read_only"] is True
    for forbidden_key in ("intent_type", "final_action", "workflow_effect"):
        assert forbidden_key not in context_packet["recent_committed_meal_refs"][0]
