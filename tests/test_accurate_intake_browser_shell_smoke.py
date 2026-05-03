from __future__ import annotations

import json
from pathlib import Path

from scripts import run_accurate_intake_browser_shell_smoke as module


def test_browser_shell_smoke_missing_playwright_is_blocked_not_web_ready(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_browser_shell_smoke_report(db_path=tmp_path / "browser.sqlite3")

    assert report["smoke_id"] == "accurate_intake_browser_executed_shell_smoke_v1"
    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["browser_execution_required"] is False
    assert report["blockers"] == ["playwright_not_installed"]
    assert report["web_readiness_claimed"] is False
    assert report["product_readiness_claimed"] is False
    assert report["frontend_semantic_owner"] is False
    assert {
        "product_ready",
        "rollout_ready",
        "live_llm_ready",
        "web_ready",
        "production_db_ready",
    } <= set(report["not_claiming"])


def test_browser_shell_smoke_can_require_browser_execution(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_browser_shell_smoke_report(
        db_path=tmp_path / "browser.sqlite3",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["browser_execution_required"] is True
    assert report["browser_executed"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_browser_shell_smoke_validator_requires_fetch_sequence_and_cjk() -> None:
    report = {
        "browser_executed": True,
        "browser": {
            "shell_markers": {
                "frontendSemanticOwner": "false",
                "liveLlmRequired": "false",
                "productionReadinessClaimed": "false",
            },
            "initial_cjk_rendered": True,
            "user_cjk_message_rendered": True,
            "assistant_bubble_rendered": True,
            "last_payload_parseable": True,
            "fetch_sequence": [
                {"url": "/today/current-budget", "method": "GET"},
                {"url": "/body-plan/active", "method": "GET"},
                {"url": "/accurate-intake/debug", "method": "GET"},
                {"url": "/accurate-intake/chat-history", "method": "GET"},
                {"url": "/estimate", "method": "POST"},
            ],
            "storage": {
                "localStorageKeys": [],
                "sessionStorageKeys": [],
            },
        },
    }

    status, blockers = module._validate(report)

    assert status == "pass"
    assert blockers == []


def test_browser_shell_smoke_cli_writes_blocked_artifact_without_failing_optional_run(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)
    output_path = tmp_path / "browser-smoke.json"

    exit_code = module.main(["--output", str(output_path), "--db-path", str(tmp_path / "browser.sqlite3")])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "blocked"
    assert artifact["browser_executed"] is False


def test_browser_shell_smoke_cli_fails_when_browser_execution_is_required(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)
    output_path = tmp_path / "browser-smoke.json"

    exit_code = module.main(
        [
            "--require-browser-execution",
            "--output",
            str(output_path),
            "--db-path",
            str(tmp_path / "browser.sqlite3"),
        ]
    )
    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert printed["status"] == "fail"
    assert printed["browser_execution_required"] is True
