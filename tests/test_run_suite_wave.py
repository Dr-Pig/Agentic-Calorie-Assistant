from __future__ import annotations

import subprocess

from scripts import run_suite_wave


def test_build_suite_plan_filters_and_categorizes_intake_workflow() -> None:
    plan = run_suite_wave.build_suite_plan(
        filters=run_suite_wave.SuiteFilters(
            authority_tiers=("Official Golden",),
            workflow_families=("intake",),
        )
    )

    runnable_ids = {item.suite_id for item in plan["runnable"]}
    fixture_only_ids = {item.suite_id for item in plan["fixture_only"]}

    assert "intake_founder_fit_primary_golden_v1" in runnable_ids
    assert "intake_turn2_hybrid_replay_golden_v1" in runnable_ids
    assert "intake_task_meal_link_golden_v1" in fixture_only_ids
    assert "rescue_accept_action_golden_v1" not in runnable_ids | fixture_only_ids


def test_turn2_runner_expands_fixture_cases_into_commands() -> None:
    plan = run_suite_wave.build_suite_plan(
        filters=run_suite_wave.SuiteFilters(
            suite_ids=("intake_turn2_hybrid_replay_golden_v1",),
        )
    )

    suite_plan = plan["runnable"][0]
    assert len(suite_plan.commands) == 9
    assert all(command.command[2] == "--case-id" for command in suite_plan.commands)
    assert all(command.command[-2:] == ("--mode", "full") for command in suite_plan.commands)


def test_unknown_runner_is_reported_as_unsupported(monkeypatch) -> None:
    monkeypatch.setattr(
        run_suite_wave,
        "_load_registry",
        lambda path: (
            [
                {
                    "path": "scripts/run_unknown_audit.py",
                    "audit_name": "unknown_audit",
                    "suite_id": "custom_suite_v1",
                    "authority_tier": "Smoke / Infra",
                    "workflow_family": "intake",
                    "capability_family": "intake_runtime",
                    "validation_layer": "smoke_infra",
                }
            ]
            if path == run_suite_wave.RUNNER_REGISTRY_PATH
            else [
                {
                    "path": "docs/quality/benchmarks/custom_suite_v1.json",
                    "type": "json",
                    "suite_id": "custom_suite_v1",
                    "authority_tier": "Smoke / Infra",
                    "workflow_family": "intake",
                    "capability_family": "intake_runtime",
                    "validation_layer": "smoke_infra",
                }
            ]
        ),
    )

    plan = run_suite_wave.build_suite_plan(filters=run_suite_wave.SuiteFilters())

    assert not plan["runnable"]
    assert len(plan["unsupported"]) == 1
    assert plan["unsupported"][0].issues == ("unsupported_runner:scripts/run_unknown_audit.py",)


def test_main_execute_prints_plan_and_results(monkeypatch, capsys) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=kwargs.get("args") or args[0],
            returncode=0,
            stdout="runner ok\n",
            stderr="",
        )

    monkeypatch.setattr(run_suite_wave.subprocess, "run", fake_run)

    exit_code = run_suite_wave.main(
        [
            "--suite-id",
            "intake_founder_fit_primary_golden_v1",
            "--execute",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Plan summary:" in captured.out
    assert "Execution results:" in captured.out
    assert "[PASS] intake_founder_fit_primary_golden_v1" in captured.out


def test_rescue_executable_runner_is_planned_as_runnable_suite() -> None:
    plan = run_suite_wave.build_suite_plan(
        filters=run_suite_wave.SuiteFilters(
            suite_ids=("rescue_runtime_smoke_v1",),
        )
    )

    assert len(plan["runnable"]) == 1
    suite_plan = plan["runnable"][0]
    assert suite_plan.suite_id == "rescue_runtime_smoke_v1"
    assert len(suite_plan.commands) == 1
    assert suite_plan.commands[0].runner_path == "scripts/run_rescue_executable_pack.py"


def test_agent_allowed_capability_suites_are_classified_as_fixture_only() -> None:
    plan = run_suite_wave.build_suite_plan(
        filters=run_suite_wave.SuiteFilters(
            validation_layers=("capability_service", "degraded_or_fallback"),
        )
    )

    fixture_only_ids = {item.suite_id for item in plan["fixture_only"]}

    assert "retrieval_candidate_selection_golden_v1" in fixture_only_ids
    assert "context_packing_sufficiency_golden_v1" in fixture_only_ids
    assert "bounded_repair_gate_golden_v1" in fixture_only_ids
    assert not plan["runnable"]


def test_general_chat_official_runner_is_planned_as_runnable_suite() -> None:
    plan = run_suite_wave.build_suite_plan(
        filters=run_suite_wave.SuiteFilters(
            suite_ids=("general_chat_budget_query_golden_v1",),
        )
    )

    assert len(plan["runnable"]) == 1
    suite_plan = plan["runnable"][0]
    assert suite_plan.suite_id == "general_chat_budget_query_golden_v1"
    assert len(suite_plan.commands) == 1
    assert suite_plan.commands[0].runner_path == "scripts/run_general_chat_official_pack.py"
