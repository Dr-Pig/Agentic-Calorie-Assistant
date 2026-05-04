from __future__ import annotations

import json
from pathlib import Path

from scripts import run_accurate_intake_browser_shell_smoke as module


def test_browser_shell_smoke_detects_cjk_text_by_unicode_range() -> None:
    assert module._contains_cjk("\u4eca\u5929\u53ef\u4ee5\u8a18\u9304\u98f2\u98df") is True
    assert module._contains_cjk("Runtime result only") is False


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
        "browser_reload_checked": True,
        "chat_history_reloaded": True,
        "initial_cjk_rendered": True,
        "user_cjk_message_rendered": True,
        "assistant_bubble_rendered": True,
        "today_summary_rendered": True,
        "debug_surface_rendered": True,
        "trace_surface_rendered": True,
        "pending_followup_surface_rendered": True,
        "runtime_status_surface_rendered": True,
        "failure_signal_surface_rendered": True,
        "not_available_rendered": True,
        "forbidden_storage_used": False,
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


def test_browser_shell_smoke_validator_requires_expected_fetch_methods() -> None:
    report = {
        "browser_executed": True,
        "browser_reload_checked": True,
        "chat_history_reloaded": True,
        "initial_cjk_rendered": True,
        "user_cjk_message_rendered": True,
        "assistant_bubble_rendered": True,
        "today_summary_rendered": True,
        "debug_surface_rendered": True,
        "trace_surface_rendered": True,
        "pending_followup_surface_rendered": True,
        "runtime_status_surface_rendered": True,
        "failure_signal_surface_rendered": True,
        "not_available_rendered": True,
        "forbidden_storage_used": False,
        "browser": {
            "shell_markers": {
                "frontendSemanticOwner": "false",
                "liveLlmRequired": "false",
                "productionReadinessClaimed": "false",
            },
            "last_payload_parseable": True,
            "fetch_sequence": [
                {"url": "/today/current-budget", "method": "POST"},
                {"url": "/body-plan/active", "method": "POST"},
                {"url": "/accurate-intake/debug", "method": "POST"},
                {"url": "/accurate-intake/chat-history", "method": "POST"},
                {"url": "/estimate", "method": "GET"},
            ],
            "storage": {
                "localStorageKeys": [],
                "sessionStorageKeys": [],
            },
        },
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "fetch_missing:GET /today/current-budget" in blockers
    assert "fetch_missing:GET /body-plan/active" in blockers
    assert "fetch_missing:GET /accurate-intake/debug" in blockers
    assert "fetch_missing:GET /accurate-intake/chat-history" in blockers
    assert "fetch_missing:POST /estimate" in blockers


def test_browser_shell_smoke_validator_requires_reload_and_read_model_surfaces() -> None:
    report = {
        "browser_executed": True,
        "browser_reload_checked": False,
        "chat_history_reloaded": False,
        "initial_cjk_rendered": True,
        "user_cjk_message_rendered": True,
        "assistant_bubble_rendered": True,
        "today_summary_rendered": False,
        "debug_surface_rendered": False,
        "trace_surface_rendered": False,
        "pending_followup_surface_rendered": False,
        "runtime_status_surface_rendered": False,
        "failure_signal_surface_rendered": False,
        "not_available_rendered": False,
        "forbidden_storage_used": False,
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

    assert status == "fail"
    assert "browser_reload_not_checked" in blockers
    assert "chat_history_not_reloaded" in blockers
    assert "today_summary_not_rendered" in blockers
    assert "debug_surface_not_rendered" in blockers
    assert "trace_surface_not_rendered" in blockers
    assert "pending_followup_surface_not_rendered" in blockers
    assert "runtime_status_surface_not_rendered" in blockers
    assert "failure_signal_surface_not_rendered" in blockers
    assert "not_available_not_rendered" in blockers


def test_browser_shell_smoke_validator_requires_storage_evidence() -> None:
    report = {
        "browser_executed": True,
        "browser_reload_checked": True,
        "chat_history_reloaded": True,
        "initial_cjk_rendered": True,
        "user_cjk_message_rendered": True,
        "assistant_bubble_rendered": True,
        "today_summary_rendered": True,
        "debug_surface_rendered": True,
        "trace_surface_rendered": True,
        "pending_followup_surface_rendered": True,
        "runtime_status_surface_rendered": True,
        "failure_signal_surface_rendered": True,
        "not_available_rendered": True,
        "forbidden_storage_used": False,
        "browser": {
            "shell_markers": {
                "frontendSemanticOwner": "false",
                "liveLlmRequired": "false",
                "productionReadinessClaimed": "false",
            },
            "last_payload_parseable": True,
            "fetch_sequence": [
                {"url": "/today/current-budget", "method": "GET"},
                {"url": "/body-plan/active", "method": "GET"},
                {"url": "/accurate-intake/debug", "method": "GET"},
                {"url": "/accurate-intake/chat-history", "method": "GET"},
                {"url": "/estimate", "method": "POST"},
            ],
        },
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "storage_evidence_missing" in blockers


def test_browser_shell_smoke_validator_rejects_any_browser_storage_use() -> None:
    report = {
        "browser_executed": True,
        "browser_reload_checked": True,
        "chat_history_reloaded": True,
        "initial_cjk_rendered": True,
        "user_cjk_message_rendered": True,
        "assistant_bubble_rendered": True,
        "today_summary_rendered": True,
        "debug_surface_rendered": True,
        "trace_surface_rendered": True,
        "pending_followup_surface_rendered": True,
        "runtime_status_surface_rendered": True,
        "failure_signal_surface_rendered": True,
        "not_available_rendered": True,
        "forbidden_storage_used": True,
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
                "localStorageKeys": ["bad"],
                "sessionStorageKeys": [],
            },
        },
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "forbidden_storage_used" in blockers
    assert "local_storage_used" in blockers


def test_browser_shell_smoke_rejects_request_failed_as_assistant_bubble() -> None:
    payload = {"coach_message": "已記錄早餐。"}

    assert module._assistant_bubble_rendered("User\nAI\nRequest failed: HTTP 500", payload) is False
    assert module._assistant_bubble_rendered("User\nAI\n已記錄早餐。", payload) is True


def test_browser_shell_smoke_script_stays_out_of_fooddb_and_live_provider_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_browser_shell_smoke.py").read_text(encoding="utf-8")

    forbidden_fragments = [
        "NutritionEvidenceStorePort",
        "food_evidence_promotion_policy",
        "food_source_quality_policy",
        "fooddb_quality_plan",
        "packetizer",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "run_accurate_intake_mvp_live_diagnostic",
        "kimi",
        "grok",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in source


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


def test_browser_shell_smoke_cli_writes_fail_artifact_for_browser_sequence_error(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(module, "_load_sync_playwright", lambda: object())

    def broken_browser_sequence(**_: object) -> dict[str, object]:
        raise RuntimeError("chromium_not_installed")

    monkeypatch.setattr(module, "_run_browser_sequence", broken_browser_sequence)
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
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert artifact == printed
    assert artifact["status"] == "fail"
    assert artifact["browser_executed"] is False
    assert artifact["browser_sequence_error"].startswith("RuntimeError: chromium_not_installed")
    assert "browser_sequence_error:RuntimeError" in artifact["blockers"]
