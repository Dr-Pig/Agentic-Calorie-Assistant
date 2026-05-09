from __future__ import annotations

import importlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LIVE_TOPOLOGY_MATRIX_CASE_IDS = (
    "exact_item_official_label",
    "bubble_milk_tea_refinement",
    "luwei_bare_to_listed_basket",
    "chinese_chicken_rice_correction_removal_debug",
    "explicit_item_removal_seeded",
    "today_consumed_query_only",
    "no_plan_consumed_without_budget_target",
)


@pytest.mark.parametrize("case_id", LIVE_TOPOLOGY_MATRIX_CASE_IDS)
def test_live_single_case_probe_has_expected_call_topology_matrix(
    tmp_path: Path,
    case_id: str,
) -> None:
    from app.composition.accurate_intake_call_topology_expectations import (
        EXPECTED_CALL_TOPOLOGY_BY_CASE_ID,
    )

    assert case_id in EXPECTED_CALL_TOPOLOGY_BY_CASE_ID

    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / f"{case_id}.json",
        db_path=tmp_path / f"{case_id}.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="single_case_live_probe",
        case_id=case_id,
    )

    assert report["stages"][-1]["stage_id"] == "single_case_live_probe"
    assert report["stages"][-1]["status"] == "pass"
    case = report["cases"][0]
    assert case["case_id"] == case_id

    grade = case["trace_expectation_grade"]
    assert grade["required_status"] == "pass"
    checks = {check["check_id"]: check for check in grade["checks"]}
    assert checks["call_topology_matches_expected"]["status"] == "pass"


def test_live_call_topology_rejects_no_plan_intake_execution() -> None:
    from app.composition.accurate_intake_live_trace_expectations import (
        grade_live_trace_expectations,
    )

    case = {
        "case_id": "no_plan_consumed_without_budget_target",
        "provider_invocations": [
            {"diagnostic_turn": 1, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
        ],
        "turns": [
            {
                "turn": 1,
                "workflow_effect": "answer_only",
                "state_delta": {"canonical_commit": False, "ledger_updated": False},
                "remaining_budget": {
                    "status": "onboarding_required",
                    "daily_target_kcal": None,
                    "remaining_kcal": None,
                    "consumed_kcal": 0,
                },
                "coach_message": "No daily target is configured, so only logged intake can be reported.",
            }
        ],
    }

    grade = grade_live_trace_expectations(case)

    assert grade["required_status"] == "fail"
    checks = {check["check_id"]: check for check in grade["checks"]}
    assert checks["call_topology_matches_expected"]["status"] == "fail"
