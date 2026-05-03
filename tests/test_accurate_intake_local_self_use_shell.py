from __future__ import annotations

import json
from pathlib import Path

from scripts.run_accurate_intake_local_self_use_shell import build_local_self_use_shell_report, main


def test_local_self_use_shell_runs_one_day_fixture_and_exposes_operator_surface(tmp_path: Path) -> None:
    report = build_local_self_use_shell_report(
        scenario="one_day_v1",
        db_path=tmp_path / "self_use.sqlite",
        reset_db=True,
    )

    assert report["shell_id"] == "accurate_intake_local_self_use_shell_v1"
    assert report["status"] == "pass"
    assert report["scenario"] == "one_day_v1"
    assert report["manager_mode"] == "fixture"
    assert report["runner_inferred_semantics"] is False
    assert report["raw_text_input_supported"] is False
    assert report["product_readiness_claimed"] is False
    assert report["live_llm_invoked"] is False

    surface = report["operator_surface"]
    assert surface["read_only"] is True
    assert surface["today_summary"]["consumed_kcal"] == 1670
    assert surface["today_summary"]["remaining_kcal"] == 130
    assert surface["same_truth"]["status"] == "pass"
    assert [entry["turn_id"] for entry in surface["chat_style_transcript"]] == [
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
    assert surface["correction_history"][-1]["removed_item_names"] == ["貢丸"]


def test_local_self_use_shell_can_keep_db_for_reopen_continuity(tmp_path: Path) -> None:
    db_path = tmp_path / "self_use.sqlite"
    first = build_local_self_use_shell_report(scenario="one_day_v1", db_path=db_path, reset_db=True)
    second = build_local_self_use_shell_report(scenario="one_day_v1", db_path=db_path, reset_db=False)

    assert first["status"] == "pass"
    assert second["status"] == "pass"
    assert second["db_mode"] == "keep_existing_local_sqlite"
    assert second["operator_surface"]["today_summary"] == first["operator_surface"]["today_summary"]
    assert second["operator_surface"]["same_truth"]["status"] == "pass"


def test_local_self_use_shell_blocks_unknown_scenarios_without_raw_text_routing(tmp_path: Path) -> None:
    report = build_local_self_use_shell_report(
        scenario="free_text:今天吃牛肉麵",
        db_path=tmp_path / "self_use.sqlite",
        reset_db=True,
    )

    assert report["status"] == "blocked"
    assert report["blockers"] == ["manager_fixture_missing_for_scenario"]
    assert report["runner_inferred_semantics"] is False
    assert report["raw_text_routing_used"] is False
    assert report["mutation_applied"] is False


def test_local_self_use_shell_cli_writes_artifact_and_can_print_debug_surface(
    tmp_path: Path,
    capsys,
) -> None:
    output_path = tmp_path / "shell.json"
    db_path = tmp_path / "self_use.sqlite"

    exit_code = main(
        [
            "--scenario",
            "one_day_v1",
            "--db-path",
            str(db_path),
            "--reset-db",
            "--output",
            str(output_path),
            "--print-debug-surface",
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["operator_surface"]["today_summary"]["consumed_kcal"] == 1670
    assert artifact["operator_surface"]["meal_thread_count"] == 4
