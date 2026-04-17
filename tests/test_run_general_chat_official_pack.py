from __future__ import annotations

import json

from scripts import run_general_chat_official_pack


def test_run_pack_executes_all_general_chat_official_cases(tmp_path) -> None:
    report_path, summary_path, report = run_general_chat_official_pack.run_pack(output_dir=tmp_path)

    assert report_path.exists()
    assert summary_path.exists()
    assert report["summary"]["total_cases"] == 3
    assert report["summary"]["failed_cases"] == 0
    assert {case["suite_id"] for case in report["cases"]} == {
        "general_chat_budget_query_golden_v1",
        "general_chat_goal_query_golden_v1",
        "general_chat_open_workflow_boundary_golden_v1",
    }

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_payload["passed_cases"] == 3


def test_run_pack_can_filter_single_case(tmp_path) -> None:
    _, _, report = run_general_chat_official_pack.run_pack(
        case_id="general_chat_budget_official_001",
        output_dir=tmp_path,
    )

    assert report["summary"]["total_cases"] == 1
    assert report["cases"][0]["suite_id"] == "general_chat_budget_query_golden_v1"
    assert report["cases"][0]["checks"]["passed"] is True
