from __future__ import annotations

import json
from pathlib import Path

from scripts import build_accurate_intake_rt11b_final_response_quality_live_wall as module


def _artifact(case_id: str, turns: list[dict[str, object]]) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "provider_mode": "live",
        "live_invoked": True,
        "live_llm_invoked": True,
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "live_provider_used_as_truth": False,
        "runtime_web_activation_approved": False,
        "stages": [
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": [case_id],
            }
        ],
        "cases": [
            {
                "case_id": case_id,
                "case_contract_status": "strict_pass",
                "verdict": "pass",
                "failure_layer": None,
                "turns": turns,
            }
        ],
    }


def _exact_artifact() -> dict[str, object]:
    return _artifact(
        "exact_item_official_label",
        [
            {
                "turn": 1,
                "coach_message": "Logged. 星巴克 那堂(冰) 大杯 154 kcal. (Meal total: 154 kcal). Remaining about 1158 kcal today.",
                "manager_final_action": "commit",
                "remaining_budget": {"consumed_kcal": 154},
            }
        ],
    )


def _bubble_artifact() -> dict[str, object]:
    return _artifact(
        "bubble_milk_tea_refinement",
        [
            {
                "turn": 1,
                "coach_message": "Logged. 珍珠奶茶 400 kcal. (Meal total: 400 kcal). Remaining about 912 kcal today.",
                "manager_final_action": "commit",
                "remaining_budget": {"consumed_kcal": 400},
            },
            {
                "turn": 2,
                "coach_message": "Logged. 半糖大杯 400 kcal. (Meal total: 400 kcal). Remaining about 912 kcal today.",
                "manager_final_action": "commit",
                "remaining_budget": {"consumed_kcal": 400},
            },
        ],
    )


def _luwei_artifact() -> dict[str, object]:
    return _artifact(
        "luwei_bare_to_listed_basket",
        [
            {
                "turn": 1,
                "coach_message": "滷味是自選的組合餐嗎？請列出你吃了哪些具體食材或項目，以及大約的份量。",
                "manager_final_action": "ask_followup",
            },
            {
                "turn": 2,
                "coach_message": "Logged. 有豆干、海帶、貢丸 400 kcal. (Meal total: 400 kcal). Remaining about 912 kcal today.",
                "manager_final_action": "commit",
                "remaining_budget": {"consumed_kcal": 400},
            },
        ],
    )


def _no_plan_artifact() -> dict[str, object]:
    return _artifact(
        "no_plan_consumed_without_budget_target",
        [
            {
                "turn": 1,
                "coach_message": "Onboarding is required before I can answer remaining budget.",
                "manager_final_action": None,
            }
        ],
    )


def _correction_artifact() -> dict[str, object]:
    return _artifact(
        "chinese_chicken_rice_correction_removal_debug",
        [
            {
                "turn": 1,
                "coach_message": "Logged. 雞肉飯 500 kcal; 湯 150 kcal. (Meal total: 650 kcal). Remaining about 662 kcal today.",
                "manager_final_action": "commit",
                "remaining_budget": {"consumed_kcal": 650},
            },
            {
                "turn": 2,
                "coach_message": "Updated. 雞肉飯 320 kcal. Total 320 kcal. Remaining about 992 kcal today.",
                "manager_final_action": "correction_applied",
                "remaining_budget": {"consumed_kcal": 320},
            },
            {
                "turn": 3,
                "coach_message": "Removed the selected item.",
                "manager_final_action": "correction_applied",
                "remaining_budget": {"consumed_kcal": 320},
            },
        ],
    )


def test_rt11b_final_response_quality_live_wall_passes() -> None:
    artifact = module.build_rt11b_final_response_quality_live_wall(
        exact_item_artifact=_exact_artifact(),
        bubble_artifact=_bubble_artifact(),
        luwei_artifact=_luwei_artifact(),
        no_plan_artifact=_no_plan_artifact(),
        correction_artifact=_correction_artifact(),
    )

    assert artifact["artifact_type"] == "accurate_intake_rt11b_final_response_quality_live_wall"
    assert artifact["target_manager_runtime_gate"] == "rt11b_final_response_quality_live_wall"
    assert artifact["status"] == "pass"
    assert artifact["supports_journeys"] == ["B", "C", "D", "J", "K"]


def test_rt11b_live_wall_blocks_missing_blocking_question() -> None:
    bad = _luwei_artifact()
    bad["cases"][0]["turns"][0]["coach_message"] = "滷味內容不清楚，請補充內容"

    artifact = module.build_rt11b_final_response_quality_live_wall(
        exact_item_artifact=_exact_artifact(),
        bubble_artifact=_bubble_artifact(),
        luwei_artifact=bad,
        no_plan_artifact=_no_plan_artifact(),
        correction_artifact=_correction_artifact(),
    )

    assert artifact["status"] == "fail"
    assert "blocking_clarify_live.followup_question_not_explicit" in artifact["blockers"]


def test_rt11b_live_wall_blocks_debug_leak() -> None:
    bad = _exact_artifact()
    bad["cases"][0]["turns"][0]["coach_message"] = "Logged. 154 kcal. trace=request-1"

    artifact = module.build_rt11b_final_response_quality_live_wall(
        exact_item_artifact=bad,
        bubble_artifact=_bubble_artifact(),
        luwei_artifact=_luwei_artifact(),
        no_plan_artifact=_no_plan_artifact(),
        correction_artifact=_correction_artifact(),
    )

    assert artifact["status"] == "fail"
    assert "exact_item_logged_live.debug_or_provider_leak_present" in artifact["blockers"]


def test_rt11b_live_wall_cli_writes_artifact(tmp_path: Path) -> None:
    files = {
        "exact": tmp_path / "exact.json",
        "bubble": tmp_path / "bubble.json",
        "luwei": tmp_path / "luwei.json",
        "no_plan": tmp_path / "no_plan.json",
        "correction": tmp_path / "correction.json",
    }
    files["exact"].write_text(json.dumps(_exact_artifact(), ensure_ascii=False), encoding="utf-8")
    files["bubble"].write_text(json.dumps(_bubble_artifact(), ensure_ascii=False), encoding="utf-8")
    files["luwei"].write_text(json.dumps(_luwei_artifact(), ensure_ascii=False), encoding="utf-8")
    files["no_plan"].write_text(json.dumps(_no_plan_artifact(), ensure_ascii=False), encoding="utf-8")
    files["correction"].write_text(json.dumps(_correction_artifact(), ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "accurate_intake_rt11b_final_response_quality_live_wall.json"

    rc = module.main(
        [
            "--exact-item-artifact",
            str(files["exact"]),
            "--bubble-artifact",
            str(files["bubble"]),
            "--luwei-artifact",
            str(files["luwei"]),
            "--no-plan-artifact",
            str(files["no_plan"]),
            "--correction-artifact",
            str(files["correction"]),
            "--output",
            str(output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "accurate_intake_rt11b_final_response_quality_live_wall"
