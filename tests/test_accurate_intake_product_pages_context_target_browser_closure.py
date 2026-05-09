from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import yaml

from app.composition.accurate_intake_product_pages_context_target_browser_closure import (
    build_context_target_browser_closure_artifact,
)


def _manager_gate_ledger() -> dict[str, object]:
    return yaml.safe_load(Path("docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml").read_text(encoding="utf-8"))


def _short_term_report() -> dict[str, object]:
    return {
        "smoke_id": "accurate_intake_product_pages_short_term_context_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "browser_reload_checked": True,
        "pending_followup_created": True,
        "pending_followup_reloaded": True,
        "context_policy_version_present": True,
        "loaded_context_summary_present": True,
        "omitted_context_summary_present": True,
        "pending_pins_present_after_followup": True,
        "chat_history_context_fields_reloaded": True,
        "chat_context_status_ui_rendered": True,
        "assistant_followup_bubble_rendered": True,
        "assistant_commit_bubble_rendered": True,
        "today_no_meal_before_followup_answer": True,
        "today_consumed_zero_before_followup_answer": True,
        "today_same_day_meal_rendered": True,
        "today_summary_rendered": True,
        "product_pages_no_debug_trace": True,
        "fake_provider_calls": [
            {
                "context_policy_version_present": True,
                "loaded_context_summary_present": True,
                "omitted_context_summary_present": True,
                "pending_followup_pin_present": True,
                "raw_user_input_used_for_fixture_selection": False,
            }
        ],
    }


def _target_candidate_report() -> dict[str, object]:
    return {
        "smoke_id": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "browser_reload_checked": True,
        "chat_history_reloaded": True,
        "target_candidate_surface_checked": True,
        "target_candidate_count_rendered": 2,
        "target_candidate_names_rendered": ["luwei", "milk tea"],
        "target_candidate_list_read_only": True,
        "context_strip_read_only": True,
        "product_pages_no_debug_trace": True,
        "manager_provider_call_count": 0,
    }


def test_context_target_browser_closure_requires_both_browser_reports_and_manager_context_gates() -> None:
    artifact = build_context_target_browser_closure_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger(),
        short_term_context_report=_short_term_report(),
        target_candidate_report=_target_candidate_report(),
    )

    assert artifact["artifact_type"] == "accurate_intake_product_pages_context_target_browser_closure"
    assert artifact["status"] == "context_target_browser_closure_ready_for_self_use_flow_gate"
    assert artifact["pass_type"] == "browser_executed"
    assert artifact["browser_executed"] is True
    assert artifact["blockers"] == []
    assert artifact["upstream_manager_gates"] == {
        "rt4_context_packet_acceptance": "green",
        "rt7b_blocking_clarify_pending_followup_boundary": "green",
        "rt7d_optional_refinement_attach_boundary": "green",
        "rt14_limited_live_ladder": "green",
    }
    assert artifact["browser_reports_checked"] == [
        "accurate_intake_product_pages_short_term_context_smoke_v1",
        "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
    ]
    assert artifact["context_engineering_present"] is True
    assert artifact["target_candidate_list_read_only"] is True
    assert artifact["frontend_selects_target"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["product_readiness_claimed"] is False


def test_context_target_browser_closure_blocks_if_context_browser_report_did_not_execute() -> None:
    report = _short_term_report()
    report["browser_executed"] = False

    artifact = build_context_target_browser_closure_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger(),
        short_term_context_report=report,
        target_candidate_report=_target_candidate_report(),
    )

    assert artifact["status"] == "blocked"
    assert "short_term_context_report.browser_not_executed" in artifact["blockers"]


def test_context_target_browser_closure_blocks_if_target_candidates_are_not_read_only() -> None:
    report = _target_candidate_report()
    report["target_candidate_list_read_only"] = False

    artifact = build_context_target_browser_closure_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger(),
        short_term_context_report=_short_term_report(),
        target_candidate_report=report,
    )

    assert artifact["status"] == "blocked"
    assert "target_candidate_report.target_candidate_list_not_read_only" in artifact["blockers"]


def test_context_target_browser_closure_blocks_when_manager_context_gate_is_not_green() -> None:
    ledger = deepcopy(_manager_gate_ledger())
    for gate in ledger["gates"]:
        if gate["gate_id"] == "rt4_context_packet_acceptance":
            gate["status"] = "pending"

    artifact = build_context_target_browser_closure_artifact(
        manager_gate_ledger_artifact=ledger,
        short_term_context_report=_short_term_report(),
        target_candidate_report=_target_candidate_report(),
    )

    assert artifact["status"] == "blocked"
    assert "manager_runtime_gate.rt4_context_packet_acceptance_not_green:pending" in artifact["blockers"]


def test_context_target_browser_closure_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_product_pages_context_target_browser_closure import main

    short_term_path = tmp_path / "short-term-context.json"
    target_path = tmp_path / "target-candidate.json"
    output_path = tmp_path / "context-target-closure.json"
    short_term_path.write_text(json.dumps(_short_term_report()), encoding="utf-8")
    target_path.write_text(json.dumps(_target_candidate_report()), encoding="utf-8")

    exit_code = main(
        [
            "--short-term-context-json",
            str(short_term_path),
            "--target-candidate-json",
            str(target_path),
            "--output",
            str(output_path),
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "context_target_browser_closure_ready_for_self_use_flow_gate"


def test_ci_builds_context_target_browser_closure_after_both_browser_reports() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "build_accurate_intake_product_pages_context_target_browser_closure.py" in workflow
    assert "accurate_intake_product_pages_context_target_browser_closure_ci.json" in workflow
