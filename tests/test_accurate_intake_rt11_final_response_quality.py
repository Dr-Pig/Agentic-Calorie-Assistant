from __future__ import annotations

import json
from pathlib import Path


def test_rt11_final_response_quality_artifact_passes_fixture_wall() -> None:
    from scripts import run_accurate_intake_rt11_final_response_quality as module

    artifact = module.build_rt11_final_response_quality_artifact()

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt11_final_response_quality"
    assert artifact["pass_type"] == "fixture"
    assert artifact["runtime_backed"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["summary"]["case_count"] == 6

    by_id = {case["case_id"]: case for case in artifact["cases"]}
    assert by_id["logged_estimate_states_commit_kcal_and_uncertainty"]["status"] == "pass"
    assert by_id["optional_refinement_keeps_logged_status_and_next_question"]["status"] == "pass"
    assert by_id["blocking_clarify_states_not_logged_and_asks_question"]["status"] == "pass"
    assert by_id["macro_hidden_reply_does_not_invent_macro_numbers"]["status"] == "pass"


def test_rt11_case_evaluator_blocks_debug_leaks_and_hidden_macro_numbers() -> None:
    from scripts import run_accurate_intake_rt11_final_response_quality as module

    debug_case = module._evaluate_case(  # noqa: SLF001
        {
            "case_id": "bad-debug",
            "family": "logged_estimate",
            "reply_text": "已幫你記錄：茶葉蛋，約 70 kcal。trace id=req-1",
            "logged_status": "logged",
            "final_action": "commit",
            "expected_kcal": 70,
            "must_include_kcal": True,
            "must_include_uncertainty": True,
            "required_markers": [],
            "forbidden_markers": [],
        }
    )
    macro_case = module._evaluate_case(  # noqa: SLF001
        {
            "case_id": "bad-macro",
            "family": "macro_hidden",
            "reply_text": "已幫你記錄這餐，熱量約 520 kcal。蛋白質 20g。",
            "logged_status": "logged",
            "final_action": "commit",
            "expected_kcal": 520,
            "must_include_kcal": True,
            "must_include_uncertainty": True,
            "must_exclude_macro_visible": True,
            "required_markers": [],
            "forbidden_markers": [],
        }
    )

    assert debug_case["status"] == "fail"
    assert "debug_or_provider_leak_present" in debug_case["blockers"]
    assert macro_case["status"] == "fail"
    assert "macro_visible_claim_present_when_hidden" in macro_case["blockers"]


def test_rt11_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts import run_accurate_intake_rt11_final_response_quality as module

    output_path = tmp_path / "accurate_intake_rt11_final_response_quality.json"
    exit_code = module.main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["artifact_name"] == "accurate_intake_rt11_final_response_quality.json"
