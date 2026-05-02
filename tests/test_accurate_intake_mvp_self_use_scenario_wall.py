from __future__ import annotations

from pathlib import Path

from scripts.run_accurate_intake_mvp_self_use_smoke import build_self_use_scenario_wall_report


def _scenario(report: dict[str, object], scenario_id: str) -> dict[str, object]:
    scenarios = {str(item["scenario_id"]): item for item in report["scenarios"]}  # type: ignore[index]
    return scenarios[scenario_id]


def _debug_model(scenario: dict[str, object]) -> dict[str, object]:
    return scenario["final_debug_surface"]["model"]  # type: ignore[index]


def test_self_use_scenario_wall_v2_closes_five_local_chinese_product_loop_flows(tmp_path: Path) -> None:
    report = build_self_use_scenario_wall_report(db_path=tmp_path / "self_use_wall.sqlite3")

    assert report["scenario_wall_id"] == "accurate_intake_mvp_self_use_scenario_wall_v2"
    assert report["claim_scope"] == "local_deterministic_mvp_gate"
    assert report["status"] == "pass"
    assert report["blockers"] == []
    assert report["live_llm_invoked"] is False
    assert report["web_tavily_invoked"] is False
    assert report["production_db_used"] is False
    assert report["user_facing_rollout"] is False
    assert report["product_readiness_claimed"] is False

    assert [scenario["scenario_id"] for scenario in report["scenarios"]] == [
        "chinese_chicken_rice_correction_removal_debug",
        "bubble_milk_tea_refinement",
        "luwei_draft_to_listed_basket",
        "query_only_today_consumed",
        "no_plan_consumed_without_target_or_remaining",
    ]
    assert report["summary"] == {
        "scenario_count": 5,
        "pass_count": 5,
        "fail_count": 0,
        "runner_inferred_semantics": False,
    }
    for scenario in report["scenarios"]:
        assert "state_before" in scenario
        assert "state_after" in scenario
        assert scenario["state_after"]["same_truth_status"] == scenario["final_debug_surface"]["model"]["same_truth"]["status"]


def test_self_use_scenario_wall_records_manager_owned_semantics_not_raw_text_routing(tmp_path: Path) -> None:
    report = build_self_use_scenario_wall_report(db_path=tmp_path / "self_use_wall.sqlite3")

    for scenario in report["scenarios"]:
        for turn in scenario["turns"]:
            assert turn["runner_inferred_semantics"] is False
            assert turn["manager_decision"]["source"] == "deterministic_manager_structured_fixture"
            assert "raw_text_keyword_route" not in turn["runtime_validation"]["accepted_authorities"]
            assert turn["runtime_validation"]["deterministic_role"] in {
                "validate_reject_or_compute_state_truth",
                "read_canonical_state_only",
            }


def test_self_use_scenario_wall_exposes_compact_operator_transcript_without_new_truth(tmp_path: Path) -> None:
    report = build_self_use_scenario_wall_report(db_path=tmp_path / "self_use_wall.sqlite3")

    transcript = report["operator_transcript"]
    assert transcript["view_id"] == "accurate_intake_mvp_operator_transcript_v1"
    assert transcript["read_only"] is True
    assert transcript["truth_source"] == "scenario_wall_v2_existing_evidence"
    assert transcript["runner_inferred_semantics"] is False
    assert transcript["scenario_count"] == 5
    assert transcript["not_claiming"] == report["not_claiming"]

    summaries = {item["scenario_id"]: item for item in transcript["scenario_summaries"]}
    chicken = summaries["chinese_chicken_rice_correction_removal_debug"]
    assert chicken["turn_count"] == 4
    assert chicken["same_truth_status"] == "pass"
    assert chicken["state_before"]["meal_thread_count"] == 0
    assert chicken["state_after"]["today_summary"]["consumed_kcal"] == 320
    assert chicken["turns"][2] == {
        "turn": 3,
        "raw_user_input": "把湯拿掉",
        "manager_intent": "correct_meal",
        "workflow_effect": "correction_remove_item",
        "final_action": "commit_correction",
        "target_attachment": {"attachment_kind": "explicit_item_target", "canonical_name": "湯"},
        "deterministic_role": "validate_reject_or_compute_state_truth",
        "runner_inferred_semantics": False,
        "mutation_applied": True,
        "consumed_kcal": 320,
    }

    no_plan = summaries["no_plan_consumed_without_target_or_remaining"]
    assert no_plan["answer_contract"] == {
        "status": "onboarding_required",
        "consumed_kcal": 420,
        "daily_target_kcal": None,
        "remaining_kcal": None,
    }
    assert "final_debug_surface" not in chicken


def test_self_use_scenario_wall_preserves_same_truth_for_correction_removal_and_read_only_queries(
    tmp_path: Path,
) -> None:
    report = build_self_use_scenario_wall_report(db_path=tmp_path / "self_use_wall.sqlite3")

    chicken = _debug_model(_scenario(report, "chinese_chicken_rice_correction_removal_debug"))
    assert chicken["today_summary"]["consumed_kcal"] == 320
    assert chicken["today_summary"]["remaining_kcal"] == 1480
    assert chicken["meal_threads"][0]["active_version"]["items"][0]["name"] == "雞肉飯"
    assert chicken["correction_history"][-1]["removed_item_names"] == ["湯"]
    assert chicken["same_truth"]["status"] == "pass"

    query = _scenario(report, "query_only_today_consumed")
    query_model = _debug_model(query)
    assert query["state_delta"]["mutation_applied"] is False
    assert query["state_delta"]["ledger_event_count_before"] == query["state_delta"]["ledger_event_count_after"]
    assert query_model["today_summary"]["consumed_kcal"] == 500
    assert query_model["same_truth"]["status"] == "pass"


def test_self_use_scenario_wall_covers_refinement_draft_and_no_plan_postures(tmp_path: Path) -> None:
    report = build_self_use_scenario_wall_report(db_path=tmp_path / "self_use_wall.sqlite3")

    bubble = _scenario(report, "bubble_milk_tea_refinement")
    bubble_model = _debug_model(bubble)
    assert bubble["turns"][0]["manager_decision"]["follow_up_posture"] == "ask_size_sugar_after_logging"
    assert bubble["turns"][1]["manager_decision"]["target_attachment"]["attachment_kind"] == "same_item_refinement"
    assert bubble_model["today_summary"]["consumed_kcal"] == 520
    assert bubble_model["same_truth"]["status"] == "pass"

    luwei = _scenario(report, "luwei_draft_to_listed_basket")
    assert luwei["turns"][0]["manager_decision"]["workflow_effect"] == "draft_clarify_no_mutation"
    assert luwei["turns"][0]["commit_result"]["mutation_applied"] is False
    luwei_model = _debug_model(luwei)
    assert luwei_model["today_summary"]["consumed_kcal"] == 420
    assert [item["name"] for item in luwei_model["meal_threads"][0]["active_version"]["items"]] == [
        "豆干",
        "海帶",
        "貢丸",
    ]

    no_plan = _scenario(report, "no_plan_consumed_without_target_or_remaining")
    no_plan_model = _debug_model(no_plan)
    assert no_plan["answer_contract"]["status"] == "onboarding_required"
    assert no_plan["answer_contract"]["consumed_kcal"] == 420
    assert no_plan["answer_contract"]["daily_target_kcal"] is None
    assert no_plan["answer_contract"]["remaining_kcal"] is None
    assert no_plan_model["today_summary"]["status"] == "onboarding_required"
    assert no_plan_model["today_summary"]["consumed_kcal"] == 420
    assert no_plan_model["today_summary"]["remaining_kcal"] is None
