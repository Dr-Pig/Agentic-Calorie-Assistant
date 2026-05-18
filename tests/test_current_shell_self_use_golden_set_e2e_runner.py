from __future__ import annotations

import asyncio
from pathlib import Path

from scripts.run_current_shell_self_use_golden_set_e2e import (
    _aggregate_runtime,
    _browser_macro_visibility_matches_read_model,
    _browser_meal_list_matches_read_model,
    _browser_read_model_matches_ui,
    _browser_today_kcal_matches_read_model,
    _recorded_websearch_ports_for_case,
    _select_cases,
    build_current_shell_golden_set_e2e_report,
)
from app.composition.current_shell_golden_set_grader import load_golden_set_manifest


def test_golden_set_e2e_runner_default_scope_is_core_only() -> None:
    selected = _select_cases(load_golden_set_manifest(), None)

    assert [case["case_id"] for case in selected] == [f"GS{index}" for index in range(1, 20)]


def test_golden_set_e2e_runner_explicit_suite_scopes_are_disjoint() -> None:
    manifest = load_golden_set_manifest()

    closeout = _select_cases(manifest, None, suite_scope="closeout")
    websearch = _select_cases(manifest, None, suite_scope="websearch")

    assert [case["case_id"] for case in closeout] == [
        *[f"GS{index}" for index in range(1, 20)],
        *[f"GSH{index}" for index in range(1, 7)],
    ]
    assert [case["case_id"] for case in websearch] == [f"GSW{index}" for index in range(1, 5)]


def test_golden_set_e2e_runner_can_select_websearch_extension_cases() -> None:
    selected = _select_cases(load_golden_set_manifest(), ["GSW1", "GSW3"])

    assert [case["case_id"] for case in selected] == ["GSW1", "GSW3"]


def test_golden_set_e2e_runner_can_select_holdout_extension_cases() -> None:
    selected = _select_cases(load_golden_set_manifest(), ["GSH1", "GSH6"])

    assert [case["case_id"] for case in selected] == ["GSH1", "GSH6"]


def test_golden_set_recorded_websearch_ports_are_tool_data_only() -> None:
    search_port, extract_port = _recorded_websearch_ports_for_case("GSW2")

    assert search_port is not None
    assert extract_port is not None
    assert search_port.readiness()["semantic_owner"] == "manager"
    hits = asyncio.run(search_port.search_hits(query="manager-owned query", max_results=5))
    assert hits
    for forbidden in ("workflow_effect", "final_action", "mutation_allowed", "runtime_truth_allowed"):
        assert forbidden not in hits[0]
    rows = asyncio.run(
        extract_port.extract_rows(urls=[str(hits[0]["url"])], query="manager-owned query")
    )
    assert rows
    for forbidden in ("workflow_effect", "final_action", "mutation_allowed", "runtime_truth_allowed"):
        assert forbidden not in rows[0]


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


def test_golden_set_e2e_runner_executes_gs17_feedback_route_not_estimate(
    tmp_path: Path,
) -> None:
    report = build_current_shell_golden_set_e2e_report(
        case_ids=["GS17"],
        db_path=tmp_path / "gs17-e2e.sqlite3",
        output_path=tmp_path / "gs17-e2e-report.json",
        trace_artifact_path=tmp_path / "gs17-e2e-trace.json",
        replay_output_path=tmp_path / "gs17-e2e-replay.json",
        provider_mode="scripted",
        local_date="2026-05-14",
    )

    case_run = report["case_runs"][0]
    case_trace = report["trace_artifact"]["cases"][0]

    assert case_run["entrypoint"] == "/accurate-intake/feedback"
    assert case_run["turns"][0]["entrypoint"] == "/accurate-intake/feedback"
    assert case_run["turns"][0]["status_code"] == 200
    assert case_run["turns"][0]["user_entered_trace_id"] is False
    assert case_trace["runtime"]["workflow_effect"] == "feedback_capture"
    assert case_trace["runtime"]["feedback_is_product_truth"] is False
    assert case_trace["runtime"]["review_record_created"] is True
    assert case_trace["ui"]["user_enters_trace_id"] is False
    assert case_trace["dogfood_trace"]["feedback_links_to_trace"] is True
    assert case_trace["dogfood_trace"]["feedback_record_id"]
    assert case_trace["dogfood_trace"]["feedback_linkage_source"] == "feedback_record"
    assert case_trace["dogfood_trace"]["auto_attaches_recent_messages"] is True
    assert case_trace["dogfood_trace"]["auto_attaches_read_model_snapshot"] is True
    assert report["replay"]["summary"]["strict_golden_set_replay_passed"] is False
    gs17 = next(case for case in report["replay"]["cases"] if case["case_id"] == "GS17")
    assert "ui.browser_executed_not_true_for_browser_case" in gs17["blockers"]


def test_golden_set_browser_same_truth_normalizes_remaining_text_units() -> None:
    assert _browser_read_model_matches_ui(
        {
            "today_after": {"consumed_kcal": "520", "remaining_kcal": "792"},
            "current_budget": {"consumed_kcal": 520, "remaining_kcal": 792},
            "body_after": {"remaining_kcal": "792 kcal"},
        }
    )
    assert not _browser_read_model_matches_ui(
        {
            "today_after": {"consumed_kcal": "520", "remaining_kcal": "792"},
            "current_budget": {"consumed_kcal": 520, "remaining_kcal": 792},
            "body_after": {"remaining_kcal": "793 kcal"},
        }
    )


def test_golden_set_browser_today_meal_and_macro_match_read_model() -> None:
    browser_result = {
        "today_after": {
            "consumed_kcal": "520",
            "remaining_kcal": "792",
            "meal_text": "早餐鐵板麵\n520 kcal",
            "macro_state": "visible",
            "protein_g": "28",
            "carbs_g": "62",
            "fat_g": "16",
        },
        "current_budget": {
            "consumed_kcal": 520,
            "remaining_kcal": 792,
            "show_macro": True,
            "consumed_protein": 28,
            "consumed_carbs": 62,
            "consumed_fat": 16,
            "meals": [{"meal_title": "早餐鐵板麵", "total_kcal": 520}],
        },
    }

    assert _browser_today_kcal_matches_read_model(browser_result)
    assert _browser_meal_list_matches_read_model(browser_result)
    assert _browser_macro_visibility_matches_read_model(browser_result)

    browser_result["today_after"]["meal_text"] = "No meals logged for this day."
    assert not _browser_meal_list_matches_read_model(browser_result)


def test_golden_set_e2e_runner_aggregates_gs18_long_session_turns(
    tmp_path: Path,
) -> None:
    report = build_current_shell_golden_set_e2e_report(
        case_ids=["GS18"],
        db_path=tmp_path / "gs18-e2e.sqlite3",
        output_path=tmp_path / "gs18-e2e-report.json",
        trace_artifact_path=tmp_path / "gs18-e2e-trace.json",
        replay_output_path=tmp_path / "gs18-e2e-replay.json",
        provider_mode="scripted",
        local_date="2026-05-14",
    )

    case_run = report["case_runs"][0]
    case_trace = report["trace_artifact"]["cases"][0]

    assert case_run["request_trace_selected"] == "aggregate_turns"
    assert len(case_run["turns"]) == 5
    assert case_trace["runtime"]["workflow_effect"] == "multi_turn_mixed_actions"
    assert case_trace["runtime"]["turn_count"] == 5
    assert case_trace["runtime"]["source"] == "aggregated_real_turn_traces"
    assert case_trace["react_trace"]["manager_pass_1"]["aggregate_source"] == "per_turn_manager_pass_1"
    assert case_trace["react_trace"]["manager_pass_final"]["aggregate_source"] == "per_turn_manager_pass_final"
    assert len(case_trace["turn_traces"]) == 5
    assert all(turn_trace["trace_id"] for turn_trace in case_trace["turn_traces"])
    assert case_trace["manager_provider"]["semantic_source"] == "fixture_provider"
    assert report["replay"]["summary"]["strict_golden_set_replay_passed"] is False
    gs18 = next(case for case in report["replay"]["cases"] if case["case_id"] == "GS18")
    assert any(blocker.startswith("fixture_decisions.") for blocker in gs18["blockers"])


def test_golden_set_e2e_runner_gs18_chain_uses_manager_semantics_not_case_text() -> None:
    turn_traces = [
        {
            "runtime": {"workflow_effect": "ask_followup", "final_action": "ask_followup"},
            "final_response_basis": {
                "semantic_decision": {"final_action_candidate": "ask_followup"}
            },
        },
        {
            "runtime": {"workflow_effect": "answer_only", "final_action": "answer_only"},
            "final_response_basis": {
                "semantic_decision": {"current_turn_intent": "answer_query"}
            },
        },
        {
            "runtime": {"workflow_effect": "commit", "final_action": "commit"},
            "final_response_basis": {
                "semantic_decision": {
                    "final_action_candidate": "commit",
                    "mutation_intent_candidate": "canonical_write",
                }
            },
        },
        {
            "runtime": {"workflow_effect": "correction", "final_action": "correction_applied"},
            "final_response_basis": {
                "semantic_decision": {
                    "current_turn_intent": "correct_meal",
                    "final_action_candidate": "correction_applied",
                }
            },
        },
        {
            "runtime": {"workflow_effect": "answer_only", "final_action": "answer_only"},
            "final_response_basis": {
                "semantic_decision": {"current_turn_intent": "answer_remaining_budget"}
            },
        },
    ]

    runtime = _aggregate_runtime(turn_traces)

    assert runtime["pending_then_commit_then_correction_then_budget_query"] is True
