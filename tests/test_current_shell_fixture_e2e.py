from __future__ import annotations

import json
from pathlib import Path

from app.composition.current_shell_fixture_e2e import (
    build_current_shell_fixture_e2e_artifact,
)
from scripts import run_current_shell_fixture_e2e as module


def _one_day_wall() -> dict[str, object]:
    return {
        "scenario_wall_id": "accurate_intake_one_day_self_use_wall_v1",
        "status": "pass",
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "product_readiness_claimed": False,
        "summary": {
            "turn_count": 9,
            "mutation_turn_count": 7,
            "no_mutation_turn_count": 2,
            "final_consumed_kcal": 1670,
            "final_remaining_kcal": 130,
        },
        "turns": [
            {"turn_id": "breakfast_tea_egg_latte"},
            {"turn_id": "lunch_chicken_bento"},
            {"turn_id": "lunch_rice_less_correction"},
            {"turn_id": "bubble_tea_first_value"},
            {"turn_id": "bubble_tea_half_sugar_large_refinement"},
            {"turn_id": "dinner_luwei_bare_draft"},
            {"turn_id": "dinner_luwei_listed_commit"},
            {"turn_id": "dinner_remove_gongwan"},
            {"turn_id": "today_consumed_remaining_query"},
        ],
    }


def _reopen_continuity() -> dict[str, object]:
    return {
        "continuity_id": "accurate_intake_one_day_reopen_continuity_v1",
        "status": "pass",
        "read_only": True,
        "mutation_applied": False,
        "live_llm_invoked": False,
        "summary": {
            "final_consumed_kcal": 1670,
            "final_remaining_kcal": 130,
            "active_meal_count": 4,
            "ledger_event_count": 7,
            "same_truth_status": "pass",
        },
    }


def _browser_realistic() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_browser_realistic_web_dogfood_v2",
        "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
        "browser_executed": True,
        "fixture_manager_used": True,
        "fixture_evidence_used": True,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "browser": {
            "target_update_rendered": True,
            "chat_history_reloaded": True,
            "today_summary_rendered": True,
            "debug_surface_rendered": True,
        },
    }


def _context_replay() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_context_replay_pack",
        "status": "generated",
        "deterministic_supplies_candidates_and_pins_only": True,
        "deterministic_semantic_inference_used": False,
        "raw_text_intent_router_used": False,
        "mutation_authority": False,
        "scenario_count": 12,
        "summary": {
            "scenario_count": 12,
            "pending_pin_scenarios": 3,
            "manager_semantic_required_scenarios": 1,
            "outside_current_day_omitted_scenarios": 1,
        },
    }


def _fake_provider_smoke() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_fake_provider_context_smoke",
        "status": "pass",
        "final_semantic_decision_source": "fixture_manager_structured_decision",
        "deterministic_semantic_inference_used": False,
        "raw_text_intent_router_used": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "real_fooddb_pass_claimed": False,
    }


def test_current_shell_fixture_e2e_records_complete_fixture_product_chain() -> None:
    artifact = build_current_shell_fixture_e2e_artifact(
        one_day_wall=_one_day_wall(),
        reopen_continuity=_reopen_continuity(),
        browser_realistic=_browser_realistic(),
        context_replay=_context_replay(),
        fake_provider_context_smoke=_fake_provider_smoke(),
    )

    assert artifact["artifact_type"] == "accurate_intake_current_shell_fixture_e2e"
    assert artifact["status"] == "current_shell_fixture_e2e_diagnostic_pass"
    assert artifact["completed_current_shell_steps"] == [
        "target_update",
        "food_log",
        "listed_basket_commit",
        "correction",
        "removal",
        "remaining_query",
        "reload_continuity",
        "browser_render_same_truth",
        "context_replay",
        "fake_provider_context_smoke",
    ]
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["fixture_evidence_used"] is True
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["websearch_evidence_used"] is False
    assert artifact["real_fooddb_pass_claimed"] is False
    assert artifact["dogfood_pass"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False


def test_current_shell_fixture_e2e_blocks_when_browser_is_optional_missing() -> None:
    browser = {**_browser_realistic(), "status": "blocked", "browser_executed": False}

    artifact = build_current_shell_fixture_e2e_artifact(
        one_day_wall=_one_day_wall(),
        reopen_continuity=_reopen_continuity(),
        browser_realistic=browser,
        context_replay=_context_replay(),
        fake_provider_context_smoke=_fake_provider_smoke(),
    )

    assert artifact["status"] == "blocked_browser_execution_unavailable"
    assert artifact["browser_executed"] is False
    assert artifact["blockers"] == ["browser_realistic_not_executed"]
    assert artifact["dogfood_pass"] is False


def test_current_shell_fixture_e2e_rejects_real_fooddb_or_readiness_overclaims() -> None:
    browser = {
        **_browser_realistic(),
        "real_fooddb_pass_claimed": True,
        "dogfood_pass": True,
        "private_self_use_approved": True,
    }

    artifact = build_current_shell_fixture_e2e_artifact(
        one_day_wall=_one_day_wall(),
        reopen_continuity=_reopen_continuity(),
        browser_realistic=browser,
        context_replay=_context_replay(),
        fake_provider_context_smoke=_fake_provider_smoke(),
    )

    assert artifact["status"] == "fail"
    assert "browser_realistic.real_fooddb_pass_claimed" in artifact["blockers"]
    assert "browser_realistic.dogfood_pass" in artifact["blockers"]
    assert "browser_realistic.private_self_use_approved" in artifact["blockers"]


def test_current_shell_fixture_e2e_rejects_stale_context_replay_coverage() -> None:
    context_replay = {
        **_context_replay(),
        "scenario_count": 7,
        "summary": {
            "scenario_count": 7,
            "pending_pin_scenarios": 2,
            "manager_semantic_required_scenarios": 0,
            "outside_current_day_omitted_scenarios": 0,
        },
    }

    artifact = build_current_shell_fixture_e2e_artifact(
        one_day_wall=_one_day_wall(),
        reopen_continuity=_reopen_continuity(),
        browser_realistic=_browser_realistic(),
        context_replay=context_replay,
        fake_provider_context_smoke=_fake_provider_smoke(),
    )

    assert artifact["status"] == "fail"
    assert "context_replay_scenario_count_too_low" in artifact["blockers"]
    assert "context_replay_pending_pin_scenarios_too_low" in artifact["blockers"]
    assert "context_replay_manager_semantic_required_missing" in artifact["blockers"]
    assert "context_replay_outside_current_day_omitted_missing" in artifact["blockers"]


def test_current_shell_fixture_e2e_cli_writes_artifact(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(module, "build_one_day_self_use_scenario_wall_report", lambda **_: _one_day_wall())
    monkeypatch.setattr(module, "build_one_day_self_use_reopen_report", lambda **_: _reopen_continuity())
    monkeypatch.setattr(module, "build_browser_realistic_web_dogfood_v2_report", lambda **_: _browser_realistic())
    monkeypatch.setattr(module, "build_context_replay_pack_artifact", lambda: _context_replay())
    monkeypatch.setattr(module, "build_fake_provider_context_smoke_artifact", lambda: _fake_provider_smoke())
    output_path = tmp_path / "fixture-e2e.json"

    exit_code = module.main(["--db-path", str(tmp_path / "fixture.sqlite3"), "--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "current_shell_fixture_e2e_diagnostic_pass"


def test_current_shell_fixture_e2e_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source = Path("scripts/run_current_shell_fixture_e2e.py").read_text(encoding="utf-8")

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "tavily",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
    ):
        assert fragment not in source
