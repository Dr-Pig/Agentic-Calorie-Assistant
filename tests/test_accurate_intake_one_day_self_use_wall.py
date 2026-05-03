from __future__ import annotations

import json
from pathlib import Path

from scripts.run_accurate_intake_mvp_self_use_smoke import (
    build_one_day_self_use_scenario_wall_report,
    build_one_day_self_use_reopen_report,
    main,
)


def _turn(report: dict[str, object], turn_id: str) -> dict[str, object]:
    turns = {str(item["turn_id"]): item for item in report["turns"]}  # type: ignore[index]
    return turns[turn_id]


def test_one_day_self_use_wall_records_full_day_product_loop(tmp_path: Path) -> None:
    report = build_one_day_self_use_scenario_wall_report(db_path=tmp_path / "one_day.sqlite3")

    assert report["scenario_wall_id"] == "accurate_intake_one_day_self_use_wall_v1"
    assert report["claim_scope"] == "local_deterministic_mvp_gate"
    assert report["status"] == "pass"
    assert report["runner_inferred_semantics"] is False
    assert report["live_llm_invoked"] is False
    assert report["production_db_used"] is False
    assert report["product_readiness_claimed"] is False
    assert report["summary"] == {
        "turn_count": 9,
        "mutation_turn_count": 7,
        "no_mutation_turn_count": 2,
        "final_consumed_kcal": 1670,
        "final_remaining_kcal": 130,
        "runner_inferred_semantics": False,
    }

    assert [turn["turn_id"] for turn in report["turns"]] == [
        "breakfast_tea_egg_latte",
        "lunch_chicken_bento",
        "lunch_rice_less_correction",
        "bubble_tea_first_value",
        "bubble_tea_half_sugar_large_refinement",
        "dinner_luwei_bare_draft",
        "dinner_luwei_listed_commit",
        "dinner_remove_gongwan",
        "today_consumed_remaining_query",
    ]
    assert report["state_before"]["today_summary"]["consumed_kcal"] == 0
    assert report["state_after"]["today_summary"]["consumed_kcal"] == 1670
    assert report["state_after"]["today_summary"]["remaining_kcal"] == 130
    assert report["final_debug_surface"]["model"]["same_truth"]["status"] == "pass"


def test_one_day_self_use_wall_uses_manager_fixtures_not_raw_text_routing(tmp_path: Path) -> None:
    report = build_one_day_self_use_scenario_wall_report(db_path=tmp_path / "one_day.sqlite3")

    for turn in report["turns"]:
        assert turn["runner_inferred_semantics"] is False
        assert turn["manager_decision"]["source"] == "deterministic_manager_structured_fixture"
        assert "raw_text_keyword_route" not in turn["runtime_validation"]["accepted_authorities"]
        assert turn["runtime_validation"]["forbidden_authorities"] == [
            "raw_text_keyword_route",
            "food_seed_disposition",
            "runner_fabricated_semantics",
        ]


def test_one_day_self_use_wall_records_evidence_packet_final_mapping_and_mutation_boundaries(
    tmp_path: Path,
) -> None:
    report = build_one_day_self_use_scenario_wall_report(db_path=tmp_path / "one_day.sqlite3")

    breakfast = _turn(report, "breakfast_tea_egg_latte")
    assert breakfast["evidence_packet"]["packet_status"] == "accepted"
    assert breakfast["final_mapping"]["owner"] == "b2_final_mapping"
    assert breakfast["commit_result"]["mutation_applied"] is True

    bare_luwei = _turn(report, "dinner_luwei_bare_draft")
    assert bare_luwei["manager_decision"]["workflow_effect"] == "draft_clarify_no_mutation"
    assert bare_luwei["evidence_packet"]["packet_status"] == "not_required"
    assert bare_luwei["final_mapping"]["final_action"] == "ask_items"
    assert bare_luwei["commit_result"] == {
        "mutation_applied": False,
        "no_mutation_reason": "composition_unknown_basket",
    }

    removal = _turn(report, "dinner_remove_gongwan")
    assert removal["manager_decision"]["workflow_effect"] == "correction_remove_item"
    assert removal["target_evidence"]["target_evidence_present"] is True
    assert removal["target_evidence"]["nutrition_evidence_present"] is False
    assert removal["commit_result"]["consumed_kcal"] == 160
    assert removal["state_after"]["today_summary"]["consumed_kcal"] == 1670

    query = _turn(report, "today_consumed_remaining_query")
    assert query["runtime_validation"]["deterministic_role"] == "read_canonical_state_only"
    assert query["commit_result"]["mutation_applied"] is False
    assert query["state_delta"] == {
        "mutation_applied": False,
        "ledger_event_count_before": 7,
        "ledger_event_count_after": 7,
    }
    assert query["answer_contract"]["consumed_kcal"] == 1670
    assert query["answer_contract"]["remaining_kcal"] == 130


def test_one_day_self_use_reopen_continuity_keeps_same_truth(tmp_path: Path) -> None:
    db_path = tmp_path / "one_day.sqlite3"
    build_one_day_self_use_scenario_wall_report(db_path=db_path)

    first = build_one_day_self_use_reopen_report(db_path=db_path)
    second = build_one_day_self_use_reopen_report(db_path=db_path)

    assert first["continuity_id"] == "accurate_intake_one_day_reopen_continuity_v1"
    assert first["status"] == "pass"
    assert first["read_only"] is True
    assert first["mutation_applied"] is False
    assert first["summary"] == {
        "final_consumed_kcal": 1670,
        "final_remaining_kcal": 130,
        "active_meal_count": 4,
        "ledger_event_count": 7,
        "same_truth_status": "pass",
    }
    assert second["summary"] == first["summary"]


def test_one_day_self_use_wall_register_is_repo_tracked_machine_truth() -> None:
    register_path = Path("docs/quality/accurate_intake_one_day_self_use_cases.json")

    assert register_path.exists()

    register = json.loads(register_path.read_text(encoding="utf-8"))
    assert register["register_id"] == "accurate_intake_one_day_self_use_cases"
    assert register["runner_inferred_semantics"] is False
    assert register["scenario_id"] == "one_day_v1"
    assert [turn["turn_id"] for turn in register["turns"]] == [
        "breakfast_tea_egg_latte",
        "lunch_chicken_bento",
        "lunch_rice_less_correction",
        "bubble_tea_first_value",
        "bubble_tea_half_sugar_large_refinement",
        "dinner_luwei_bare_draft",
        "dinner_luwei_listed_commit",
        "dinner_remove_gongwan",
        "today_consumed_remaining_query",
    ]
    for turn in register["turns"]:
        assert turn["manager_decision_fixture"]["source"] == "deterministic_manager_structured_fixture"
        assert turn["runner_inferred_semantics"] is False


def test_one_day_self_use_wall_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "one_day_cli.sqlite3"
    output_path = tmp_path / "one_day.json"

    assert main(["--one-day-scenario-wall", "--db-path", str(db_path), "--output", str(output_path)]) == 0
    capsys.readouterr()

    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["scenario_wall_id"] == "accurate_intake_one_day_self_use_wall_v1"
    assert artifact["status"] == "pass"
    assert artifact["summary"]["final_consumed_kcal"] == 1670
