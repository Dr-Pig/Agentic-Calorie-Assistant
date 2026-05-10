from __future__ import annotations

import json
import os
import asyncio
from pathlib import Path

import pytest

from scripts import run_accurate_intake_browser_realistic_web_dogfood_v2 as module


def _expected_turn_result(turn: dict[str, object]) -> dict[str, object]:
    return {
        "turn_id": turn["turn_id"],
        "raw_user_input": turn["raw_user_input"],
        "expected_manager_decision": {
            "intent_type": turn["intent_type"],
            "workflow_effect": turn["workflow_effect"],
            "final_action": turn["final_action"],
            "mutation_intent_candidate": turn["mutation_intent_candidate"],
            "target_attachment": turn["target_attachment"],
        },
        "last_payload_parseable": True,
        "runtime_error_present": False,
    }


def _turn_surface(turn_id: str) -> dict[str, object]:
    return {
        "turn_id": turn_id,
        "surface": {
            "today_summary_rendered": True,
            "debug_surface_rendered": True,
            "runtime_status_surface_rendered": True,
            "pending_followup_surface_rendered": turn_id == "dinner_draft_001",
            "meal_threads_rendered": turn_id != "dinner_draft_001",
            "backend_local_date_rendered": True,
            "observed_today_summary": {
                "budget_kcal": "1600",
                "consumed_kcal": "980",
                "remaining_kcal": "620",
            },
        },
    }


def _expected_manager_provider_calls() -> list[dict[str, object]]:
    return [
        {
            "turn_id": turn["turn_id"],
            "available_tools": ["budget.get_today_summary", "body.get_active_plan"],
            "round_index": 0,
        }
        for turn in module.TURN_FIXTURES
    ]


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
        "pending_followup_surface_rendered": False,
        "meal_threads_rendered": True,
        "backend_local_date_rendered": True,
        "observed_today_summary": {
            "budget_kcal": "1600",
            "consumed_kcal": "980",
            "remaining_kcal": "620",
        },
        "manager_context_status": "not_available",
        "evidence_gap_observed": True,
        "turn_results": [_expected_turn_result(turn) for turn in module.TURN_FIXTURES],
        "surfaces_after_turn": [_turn_surface(str(turn["turn_id"])) for turn in module.TURN_FIXTURES],
        "after_reload_surface": {
            "today_summary_rendered": True,
            "debug_surface_rendered": True,
            "runtime_status_surface_rendered": True,
            "meal_threads_rendered": True,
            "backend_local_date_rendered": True,
            "observed_today_summary": {
                "budget_kcal": "1600",
                "consumed_kcal": "980",
                "remaining_kcal": "620",
            },
        },
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


def test_browser_realistic_fixture_manager_advances_on_public_read_tool_surface() -> None:
    provider = module._BrowserRealisticManagerProvider()
    seen_turn_ids: list[str] = []

    for turn in module.TURN_FIXTURES:
        _decision, trace = asyncio.run(
            provider.complete_with_trace(
                user_payload={
                    "raw_user_input": turn["raw_user_input"],
                    "round_index": 0,
                    "available_tools": [
                        "budget.get_today_summary",
                        "body.get_active_plan",
                        "app.answer_usage_question",
                    ],
                }
            )
        )
        seen_turn_ids.append(str(trace["turn_id"]))

    assert seen_turn_ids == [str(turn["turn_id"]) for turn in module.TURN_FIXTURES]


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
    assert report["private_self_use_approved"] is False


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
    class PrecalledProvider(module._BrowserRealisticManagerProvider):
        def __init__(self) -> None:
            super().__init__()
            self.calls = _expected_manager_provider_calls()

    monkeypatch.setattr(module, "_load_sync_playwright", lambda: object())
    monkeypatch.setattr(module, "_run_browser_sequence", lambda **_: _passing_browser_result())
    monkeypatch.setattr(module, "_BrowserRealisticManagerProvider", PrecalledProvider)

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


def test_browser_realistic_v2_validator_requires_cdk_surfaces_and_reload_same_truth() -> None:
    report = module._base_report(db_path=Path("x.sqlite3"), browser_execution_required=True)
    report["browser_executed"] = True
    browser = {
        **_passing_browser_result(),
        "meal_threads_rendered": False,
        "backend_local_date_rendered": False,
    }
    browser["surfaces_after_turn"] = [
        {
            **dict(item),
            "surface": {
                **dict(item["surface"]),
                "pending_followup_surface_rendered": False,
            },
        }
        if item["turn_id"] == "dinner_draft_001"
        else item
        for item in list(browser["surfaces_after_turn"])
    ]
    browser["after_reload_surface"] = {
        **dict(browser["after_reload_surface"]),
        "meal_threads_rendered": False,
        "backend_local_date_rendered": False,
        "observed_today_summary": {
            "budget_kcal": "1600",
            "consumed_kcal": "999",
            "remaining_kcal": "601",
        },
    }
    report["browser"] = browser

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "surface_after_turn.pending_followup_not_rendered:dinner_draft_001" in blockers
    assert "meal_threads_not_rendered" in blockers
    assert "backend_local_date_not_rendered" in blockers
    assert "after_reload_surface.meal_threads_not_rendered" in blockers
    assert "after_reload_surface.backend_local_date_not_rendered" in blockers
    assert "after_reload_surface.today_summary_mismatch" in blockers


def test_browser_realistic_v2_validator_requires_structured_cdk_turn_results() -> None:
    report = module._base_report(db_path=Path("x.sqlite3"), browser_execution_required=True)
    report["browser_executed"] = True
    turn_results = [_expected_turn_result(turn) for turn in module.TURN_FIXTURES]
    turn_results = [turn for turn in turn_results if turn["turn_id"] != "dinner_draft_001"]
    for turn in turn_results:
        if turn["turn_id"] == "dinner_basket_001":
            turn["last_payload_parseable"] = False
        if turn["turn_id"] == "dinner_remove_001":
            turn["runtime_error_present"] = True
            turn["expected_manager_decision"] = {
                **dict(turn["expected_manager_decision"]),
                "workflow_effect": "answer_only",
            }
    report["browser"] = {
        **_passing_browser_result(),
        "turn_results": turn_results,
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "turn_result_missing:dinner_draft_001" in blockers
    assert "turn_result_unparseable:dinner_basket_001" in blockers
    assert "turn_result_runtime_error:dinner_remove_001" in blockers
    assert "turn_result_decision_mismatch:dinner_remove_001.workflow_effect" in blockers


def test_browser_realistic_v2_validator_requires_fixture_manager_turn_sequence() -> None:
    report = module._base_report(db_path=Path("x.sqlite3"), browser_execution_required=True)
    report["browser_executed"] = True
    report["browser"] = _passing_browser_result()
    report["manager_provider_calls"] = [
        {
            "turn_id": "breakfast_001",
            "available_tools": ["budget.get_today_summary", "body.get_active_plan"],
            "round_index": 0,
        }
        for _ in module.TURN_FIXTURES
    ]

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "fixture_manager_turn_sequence_mismatch" in blockers


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


def test_browser_realistic_v2_app_uses_request_scoped_db_sessions() -> None:
    provider = module._BrowserRealisticManagerProvider()
    created: list[FakeSession] = []

    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    def fake_session_factory() -> FakeSession:
        session = FakeSession()
        created.append(session)
        return session

    app = module._build_app(fake_session_factory, provider)  # type: ignore[arg-type]
    override_get_db = app.dependency_overrides[module.get_db]

    first_dependency = override_get_db()
    second_dependency = override_get_db()
    first_session = next(first_dependency)
    second_session = next(second_dependency)

    assert first_session is created[0]
    assert second_session is created[1]
    assert first_session is not second_session
    with pytest.raises(StopIteration):
        next(first_dependency)
    with pytest.raises(StopIteration):
        next(second_dependency)
    assert first_session.closed is True
    assert second_session.closed is True


def test_browser_realistic_v2_session_factory_uses_null_pool_for_threaded_browser_teardown(
    tmp_path: Path,
) -> None:
    engine, _SessionLocal = module._session_factory(tmp_path / "realistic.sqlite3")
    try:
        assert engine.pool.__class__.__name__ == "NullPool"
    finally:
        engine.dispose()


def test_browser_realistic_v2_restores_debug_token_on_setup_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", "operator-token")
    monkeypatch.setattr(module, "_load_sync_playwright", lambda: object())
    monkeypatch.setattr(module, "_seed_body_plan", lambda *_, **__: None)

    def broken_build_app(_db: object, _provider: object) -> object:
        raise RuntimeError("setup_boom")

    monkeypatch.setattr(module, "_build_app", broken_build_app)

    with pytest.raises(RuntimeError, match="setup_boom"):
        module.build_browser_realistic_web_dogfood_v2_report(db_path=tmp_path / "realistic.sqlite3")

    assert os.environ["LOCAL_DEBUG_API_TOKEN"] == "operator-token"


def test_browser_realistic_v2_script_stays_out_of_fooddb_live_and_app_knowledge_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_browser_realistic_web_dogfood_v2.py").read_text(encoding="utf-8")

    assert "fixture_must_not_update_app_knowledge" in source
    assert 'os.environ["LOCAL_DEBUG_API_TOKEN"]' in source
    assert 'document.querySelector("#local-debug-token")' in source
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
