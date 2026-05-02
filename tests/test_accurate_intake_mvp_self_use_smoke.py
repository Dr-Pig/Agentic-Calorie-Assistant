from __future__ import annotations

import json
from pathlib import Path

from scripts.run_accurate_intake_mvp_self_use_smoke import build_self_use_smoke_report, main


def test_self_use_smoke_report_closes_local_product_loop_without_live_dependencies(tmp_path: Path) -> None:
    report = build_self_use_smoke_report(db_path=tmp_path / "self_use.sqlite3")

    assert report["smoke_id"] == "accurate_intake_mvp_self_use_smoke_v1"
    assert report["claim_scope"] == "local_deterministic_self_use_smoke"
    assert report["status"] == "pass"
    assert report["blockers"] == []
    assert report["live_llm_invoked"] is False
    assert report["web_tavily_invoked"] is False
    assert report["production_db_used"] is False
    assert report["user_facing_rollout"] is False
    assert set(report["not_claiming"]) >= {"product_ready", "live_llm_ready", "production_db_ready"}

    debug_surface = report["debug_surface"]
    model = debug_surface["model"]
    assert model["today_summary"]["consumed_kcal"] == 470
    assert model["today_summary"]["remaining_kcal"] == 1330
    assert model["meal_threads"][0]["active_version"]["total_kcal"] == 470
    assert model["correction_history"][0]["non_target_item_names_preserved"] == ["soup"]
    assert model["same_truth"]["status"] == "pass"


def test_self_use_smoke_cli_writes_machine_readable_artifact(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "self_use_smoke.json"
    db_path = tmp_path / "self_use_smoke.sqlite3"

    exit_code = main(["--output", str(output_path), "--db-path", str(db_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "pass"
    assert artifact["debug_surface"]["surface_id"] == "accurate_intake_debug_surface_v1"
