from __future__ import annotations

import json
from pathlib import Path

from scripts import run_accurate_intake_browser_realistic_web_dogfood_v2 as module


def _passing_browser_result() -> dict[str, object]:
    return {
        "browser_name": "chromium",
        "page_url": "http://127.0.0.1:1234/static/accurate-intake-local-shell.html",
        "target_update_rendered": True,
        "browser_reload_checked": True,
        "chat_history_reloaded": True,
        "cjk_messages_rendered": True,
        "assistant_bubbles_rendered": True,
        "today_summary_rendered": True,
        "debug_surface_rendered": True,
        "runtime_status_surface_rendered": True,
        "manager_context_status": "not_available",
        "evidence_gap_observed": True,
        "fetch_sequence": [
            {"url": "/today/current-budget?user_id=browser-realistic-v2", "method": "GET"},
            {"url": "/body-plan/active?user_id=browser-realistic-v2", "method": "GET"},
            {"url": "/body-plan/manual-daily-target", "method": "POST"},
            {"url": "/accurate-intake/debug?user_id=browser-realistic-v2&local_date=2026-05-04", "method": "GET"},
            {"url": "/accurate-intake/chat-history?user_id=browser-realistic-v2&local_date=2026-05-04", "method": "GET"},
            {"url": "/estimate", "method": "POST"},
        ],
        "storage": {"localStorageKeys": [], "sessionStorageKeys": []},
        "forbidden_storage_used": False,
    }


def test_browser_realistic_v2_combines_fetches_from_before_and_after_reload() -> None:
    before = [{"url": "/estimate", "method": "POST"}]
    after = [{"url": "/accurate-intake/chat-history?user_id=browser-realistic-v2", "method": "GET"}]

    assert module._combined_fetch_sequence(before_reload=before, after_reload=after) == before + after


def test_browser_realistic_v2_missing_playwright_is_blocked_not_pass(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_browser_realistic_web_dogfood_v2_report(db_path=tmp_path / "realistic.sqlite3")

    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["fixture_manager_used"] is True
    assert report["fixture_evidence_used"] is True
    assert report["fooddb_evidence_used"] is False
    assert report["real_fooddb_pass_claimed"] is False
    assert report["dogfood_pass"] is False
    assert report["web_readiness_claimed"] is False


def test_browser_realistic_v2_can_require_browser_execution(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_browser_realistic_web_dogfood_v2_report(
        db_path=tmp_path / "realistic.sqlite3",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["blockers"] == ["playwright_not_installed"]
    assert report["browser_execution_required"] is True


def test_browser_realistic_v2_uses_diagnostic_fixture_status_not_pass(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(module, "_load_sync_playwright", lambda: object())
    monkeypatch.setattr(module, "_run_browser_sequence", lambda **_: _passing_browser_result())

    report = module.build_browser_realistic_web_dogfood_v2_report(db_path=tmp_path / "realistic.sqlite3")

    assert report["status"] == "browser_diagnostic_pass_with_fixture_evidence_gap"
    assert report["status"] not in module.FORBIDDEN_SUCCESS_STATUSES
    assert report["dogfood_pass"] is False
    assert report["fixture_manager_used"] is True
    assert report["fixture_evidence_used"] is True
    assert report["fooddb_evidence_used"] is False
    assert report["real_fooddb_pass_claimed"] is False
    assert report["fixture_policy"]["fixture_must_not_become_fooddb_truth"] is True
    assert report["fixture_policy"]["fixture_must_not_update_app_knowledge"] is True


def test_browser_realistic_v2_validator_rejects_forbidden_success_status_and_overclaims() -> None:
    report = module._base_report(db_path=Path("x.sqlite3"), browser_execution_required=True)
    report["browser_executed"] = True
    report["browser"] = _passing_browser_result()
    report["status"] = "pass"
    report["dogfood_pass"] = True
    report["real_fooddb_pass_claimed"] = True

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "forbidden_success_status:pass" in blockers
    assert "real_dogfood_pass_overclaim" in blockers


def test_browser_realistic_v2_validator_requires_browser_reload_surfaces_and_storage_evidence() -> None:
    report = module._base_report(db_path=Path("x.sqlite3"), browser_execution_required=True)
    report["browser_executed"] = True
    report["browser"] = {
        **_passing_browser_result(),
        "browser_reload_checked": False,
        "chat_history_reloaded": False,
        "runtime_status_surface_rendered": False,
        "forbidden_storage_used": True,
        "storage": {"localStorageKeys": ["bad"], "sessionStorageKeys": []},
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "browser_reload_not_checked" in blockers
    assert "chat_history_not_reloaded" in blockers
    assert "runtime_status_surface_not_rendered" in blockers
    assert "forbidden_storage_used" in blockers


def test_browser_realistic_v2_cli_writes_blocked_artifact_without_optional_failure(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)
    output_path = tmp_path / "browser-realistic.json"

    exit_code = module.main(["--db-path", str(tmp_path / "realistic.sqlite3"), "--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "blocked"


def test_browser_realistic_v2_script_stays_out_of_fooddb_live_and_app_knowledge_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_browser_realistic_web_dogfood_v2.py").read_text(encoding="utf-8")

    assert "fixture_must_not_update_app_knowledge" in source
    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "packetizer",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "app.knowledge",
        "app/knowledge",
        "kimi",
        "grok",
    ):
        assert fragment not in source


def test_self_use_runbook_documents_browser_realistic_v2_diagnostic_command() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(encoding="utf-8-sig")

    assert "run_accurate_intake_browser_realistic_web_dogfood_v2.py" in runbook
    assert "--require-browser-execution" in runbook
    assert "browser_diagnostic_pass_with_fixture_evidence_gap" in runbook
