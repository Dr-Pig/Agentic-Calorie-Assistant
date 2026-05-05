from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts import run_accurate_intake_browser_one_day_fixture_dogfood as module


def _passing_browser_result() -> dict[str, object]:
    return {
        "browser_name": "chromium",
        "page_url": "http://127.0.0.1:1234/static/accurate-intake-local-shell.html",
        "today_summary_rendered": True,
        "meal_threads_rendered": True,
        "correction_history_rendered": True,
        "same_truth_rendered": True,
        "browser_reload_checked": True,
        "reload_state_rehydrated": True,
        "fetch_sequence": [
            {"url": "/today/current-budget?user_id=self-use-one-day-v1", "method": "GET"},
            {"url": "/body-plan/active?user_id=self-use-one-day-v1", "method": "GET"},
            {"url": "/accurate-intake/debug?user_id=self-use-one-day-v1&local_date=2026-05-03", "method": "GET"},
            {"url": "/accurate-intake/chat-history?user_id=self-use-one-day-v1&local_date=2026-05-03", "method": "GET"},
        ],
        "storage": {"localStorageKeys": [], "sessionStorageKeys": []},
        "forbidden_storage_used": False,
        "observed_today_summary": {
            "budget_kcal": "1800",
            "consumed_kcal": "1670",
            "remaining_kcal": "130",
        },
    }


def test_browser_one_day_fixture_missing_playwright_is_blocked_not_pass(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_browser_one_day_fixture_dogfood_report(db_path=tmp_path / "one_day.sqlite3")

    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["fixture_evidence_used"] is True
    assert report["real_fooddb_pass_claimed"] is False
    assert report["dogfood_pass"] is False
    assert report["web_readiness_claimed"] is False
    assert report["private_self_use_approved"] is False


def test_browser_one_day_fixture_can_require_browser_execution(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_browser_one_day_fixture_dogfood_report(
        db_path=tmp_path / "one_day.sqlite3",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["blockers"] == ["playwright_not_installed"]
    assert report["browser_execution_required"] is True


def test_browser_one_day_fixture_uses_browser_fixture_status_not_dogfood_pass(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(module, "_load_sync_playwright", lambda: object())
    monkeypatch.setattr(module, "_run_browser_sequence", lambda **_: _passing_browser_result())

    report = module.build_browser_one_day_fixture_dogfood_report(db_path=tmp_path / "one_day.sqlite3")

    assert report["status"] == "browser_fixture_pass"
    assert report["dogfood_pass"] is False
    assert report["fixture_evidence_used"] is True
    assert report["real_fooddb_pass_claimed"] is False
    assert report["fooddb_evidence_used"] is False
    assert report["scenario_wall_status"] == "pass"
    assert report["browser"]["observed_today_summary"]["consumed_kcal"] == "1670"


def test_browser_one_day_fixture_validator_requires_render_reload_and_no_storage() -> None:
    report = module._base_report(db_path=Path("x.sqlite3"), browser_execution_required=True)
    report["browser_executed"] = True
    report["browser"] = {
        **_passing_browser_result(),
        "meal_threads_rendered": False,
        "browser_reload_checked": False,
        "forbidden_storage_used": True,
        "storage": {"localStorageKeys": ["bad"], "sessionStorageKeys": []},
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "meal_threads_not_rendered" in blockers
    assert "browser_reload_not_checked" in blockers
    assert "forbidden_storage_used" in blockers


def test_browser_one_day_fixture_cli_writes_blocked_artifact_without_optional_failure(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)
    output_path = tmp_path / "browser-one-day.json"

    exit_code = module.main(["--db-path", str(tmp_path / "one_day.sqlite3"), "--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "blocked"


def test_browser_one_day_fixture_restores_debug_token_on_setup_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", "operator-token")
    monkeypatch.setattr(module, "_load_sync_playwright", lambda: object())
    monkeypatch.setattr(
        module,
        "build_one_day_self_use_scenario_wall_report",
        lambda **_: {"status": "pass", "summary": {}, "scenario_wall_id": "one_day"},
    )

    def broken_build_app(_db: object) -> object:
        raise RuntimeError("setup_boom")

    monkeypatch.setattr(module, "_build_app", broken_build_app)

    with pytest.raises(RuntimeError, match="setup_boom"):
        module.build_browser_one_day_fixture_dogfood_report(db_path=tmp_path / "one_day.sqlite3")

    assert os.environ["LOCAL_DEBUG_API_TOKEN"] == "operator-token"


def test_browser_one_day_fixture_script_stays_out_of_fooddb_and_live_provider_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_browser_one_day_fixture_dogfood.py").read_text(encoding="utf-8")

    assert "local_date=LOCAL_DATE" in source
    assert 'os.environ["LOCAL_DEBUG_API_TOKEN"]' in source
    assert 'document.querySelector("#local-debug-token")' in source
    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "packetizer",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
    ):
        assert fragment not in source
