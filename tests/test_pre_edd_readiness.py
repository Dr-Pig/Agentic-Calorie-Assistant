from __future__ import annotations

import sys

from scripts.pre_edd_readiness import (
    COMMAND_PLAN,
    classify_fat_audit,
    run_pre_edd_readiness,
    summarize_status,
)


def test_pre_edd_command_plan_excludes_business_eval_suites() -> None:
    command_text = "\n".join(" ".join(item.command) for item in COMMAND_PLAN)
    old_bundle1_runner = "run_v2_" + "bundle1" + "_live_eval.py"
    old_bundle2_runner = "run_v2_" + "bundle2" + "_live_eval.py"
    old_blocking_runner = "run_v2_" + "benchmark_blocking_eval.py"

    assert old_bundle1_runner not in command_text
    assert old_bundle2_runner not in command_text
    assert "run_v2_founder_realism_eval.py" not in command_text
    assert old_blocking_runner not in command_text
    assert "scripts/audit_readiness_claim_integrity.py" in command_text
    assert "scripts/audit_architecture_dependency_debt.py" in command_text


def test_docs_encoding_policy_is_windows_only_auxiliary_check() -> None:
    command_names = {item.name for item in COMMAND_PLAN}

    if sys.platform.startswith("win"):
        assert "docs_encoding_policy" in command_names
    else:
        assert "docs_encoding_policy" not in command_names


def test_fat_audit_classifier_blocks_protected_overage_but_not_watchlist_overage() -> None:
    stdout = "\n".join(
        [
            "[OK] app/intake/application/intake_execution_orchestrator.py lines=162 threshold=400 kind=application-service",
            "[OVER] app/nutrition/agent/exact_item_packets.py lines=254 watch=186 kind=nutrition-agent-watchlist",
        ]
    )

    assert classify_fat_audit(stdout=stdout, exit_code=0)["status"] == "pass"

    protected_stdout = "[OVER] app/intake/application/intake_execution_orchestrator.py lines=450 threshold=400 kind=application-service"
    result = classify_fat_audit(stdout=protected_stdout, exit_code=0)

    assert result["status"] == "fail"
    assert "intake_execution_orchestrator.py" in result["details"][0]


def test_fat_audit_classifier_blocks_freeze_growth_overage() -> None:
    freeze_stdout = "[OVER] app/providers/builderspace_adapter.py lines=1081 freeze=760 kind=provider-freeze"
    result = classify_fat_audit(stdout=freeze_stdout, exit_code=0)

    assert result["status"] == "fail"
    assert "builderspace_adapter.py" in result["details"][0]


def test_summarize_status_returns_not_ready_on_any_failure() -> None:
    summary = summarize_status(
        {
            "fat_file_status": {"status": "pass"},
            "single_manager_status": {"status": "fail"},
            "encoding_status": {"status": "pass"},
        }
    )

    assert summary["status"] == "not_ready_for_edd"


def test_pre_edd_readiness_report_includes_single_manager_guardrail_statuses(monkeypatch) -> None:
    def fake_run_command(*args, **kwargs):
        return {
            "name": "fake",
            "command": ["fake"],
            "exit_code": 0,
            "stdout": "",
            "status": "pass",
            "details": [],
        }

    monkeypatch.setattr("scripts.pre_edd_readiness._run_command", fake_run_command)

    report = run_pre_edd_readiness(timeout_seconds=1)
    statuses = report["statuses"]

    assert statuses["single_manager_contract_status"]["status"] == "pass"
    assert statuses["domain_tool_surface_status"]["status"] == "pass"
    assert statuses["guard_invariant_status"]["status"] == "pass"
    assert statuses["fat_service_status"]["status"] == "pass"
    assert statuses["latency_trace_status"]["status"] == "pass"
    assert statuses["product_truth_alignment_status"]["status"] == "pass"
    assert statuses["anti_overfit_status"]["status"] == "pass"
    assert statuses["readiness_claim_status"]["status"] == "pass"
