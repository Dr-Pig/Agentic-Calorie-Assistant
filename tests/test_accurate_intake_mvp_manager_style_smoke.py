from __future__ import annotations

import asyncio
import json
from pathlib import Path

from scripts.run_accurate_intake_mvp_manager_style_smoke import (
    build_manager_style_smoke_report,
    main,
)


def test_manager_style_smoke_runs_active_manager_loop_without_live_provider(tmp_path: Path) -> None:
    report = asyncio.run(
        build_manager_style_smoke_report(
            db_path=tmp_path / "manager-style-smoke.sqlite3",
            user_external_id="manager-style-smoke-test",
            local_date="2026-05-02",
        )
    )

    assert report["smoke_id"] == "accurate_intake_mvp_manager_style_smoke_v1"
    assert report["status"] == "pass"
    assert report["blockers"] == []
    assert report["claim_scope"] == "local_deterministic_manager_style_smoke"
    assert report["active_entrypoint_verified"] is True
    assert report["live_llm_invoked"] is False
    assert report["web_tavily_invoked"] is False
    assert report["production_db_used"] is False
    assert report["user_facing_rollout"] is False
    assert {"product_ready", "live_llm_ready", "production_db_ready"} <= set(report["not_claiming"])

    turns = report["turns"]
    assert [turn["kind"] for turn in turns] == [
        "new_meal",
        "explicit_item_correction",
        "budget_query",
    ]
    assert turns[0]["state_delta"]["canonical_commit"] is True
    assert turns[0]["manager_round_count"] >= 2
    assert turns[1]["state_delta"]["canonical_commit"] is True
    assert turns[1]["state_delta"]["old_version_superseded"] is True
    assert turns[1]["manager_final_action"] == "correction_applied"
    assert turns[2]["state_delta"]["canonical_commit"] is False
    assert turns[2]["manager_intent"] == "answer_remaining_budget"

    debug_model = report["debug_surface"]["model"]
    assert debug_model["today_summary"]["consumed_kcal"] > 0
    assert debug_model["same_truth"]["status"] == "pass"
    assert report["manager_provider"]["provider"] == "deterministic_self_use_manager_fixture"
    assert len(report["manager_provider_calls"]) >= 5


def test_manager_style_smoke_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    output = tmp_path / "manager-style-smoke.json"
    db_path = tmp_path / "manager-style-smoke.sqlite3"

    exit_code = main(
        [
            "--output",
            str(output),
            "--db-path",
            str(db_path),
            "--user-id",
            "manager-style-smoke-cli",
            "--local-date",
            "2026-05-02",
        ]
    )

    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "pass"
    assert artifact["debug_surface"]["surface_id"] == "accurate_intake_debug_surface_v1"
