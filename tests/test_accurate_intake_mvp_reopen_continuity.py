from __future__ import annotations

import json
from pathlib import Path

from scripts.run_accurate_intake_mvp_self_use_smoke import (
    build_self_use_reopen_continuity_report,
    build_self_use_scenario_wall_report,
    main,
)


def test_reopen_continuity_reads_existing_scenario_wall_state_without_mutation(tmp_path: Path) -> None:
    db_path = tmp_path / "self_use_reopen.sqlite3"
    build_self_use_scenario_wall_report(db_path=db_path)

    first = build_self_use_reopen_continuity_report(db_path=db_path)
    second = build_self_use_reopen_continuity_report(db_path=db_path)

    assert first["continuity_id"] == "accurate_intake_mvp_reopen_continuity_v1"
    assert first["claim_scope"] == "local_deterministic_mvp_gate"
    assert first["status"] == "pass"
    assert first["read_only"] is True
    assert first["mutation_applied"] is False
    assert first["live_llm_invoked"] is False
    assert first["production_db_used"] is False
    assert first["summary"] == {
        "scenario_count": 5,
        "pass_count": 5,
        "fail_count": 0,
        "ledger_event_count_total": 8,
    }
    assert second["summary"]["ledger_event_count_total"] == first["summary"]["ledger_event_count_total"]

    scenarios = {item["scenario_id"]: item for item in first["scenarios"]}
    chicken = scenarios["chinese_chicken_rice_correction_removal_debug"]
    assert chicken["state_after_reopen"]["today_summary"]["consumed_kcal"] == 320
    assert chicken["state_after_reopen"]["today_summary"]["remaining_kcal"] == 1480
    assert chicken["active_item_names_after_reopen"] == ["雞肉飯"]
    assert chicken["removed_item_names_after_reopen"] == ["湯"]
    assert chicken["ledger_event_count_after_reopen"] == 3

    no_plan = scenarios["no_plan_consumed_without_target_or_remaining"]
    assert no_plan["state_after_reopen"]["today_summary"]["status"] == "onboarding_required"
    assert no_plan["state_after_reopen"]["today_summary"]["consumed_kcal"] == 420
    assert no_plan["state_after_reopen"]["today_summary"]["remaining_kcal"] is None


def test_reopen_continuity_cli_writes_read_only_artifact(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "self_use_reopen_cli.sqlite3"
    seed_output = tmp_path / "seed.json"
    reopen_output = tmp_path / "reopen.json"

    assert main(["--scenario-wall-v2", "--db-path", str(db_path), "--output", str(seed_output)]) == 0
    assert main(["--reopen-continuity", "--db-path", str(db_path), "--output", str(reopen_output)]) == 0
    capsys.readouterr()

    artifact = json.loads(reopen_output.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["read_only"] is True
    assert artifact["mutation_applied"] is False
    assert artifact["summary"]["ledger_event_count_total"] == 8

