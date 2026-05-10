from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts import run_accurate_intake_browser_one_day_fixture_dogfood as module

EXPECTED_MANAGER_DOGFOOD_TODAY = {
    "budget_kcal": "1600",
    "consumed_kcal": "1775",
    "remaining_kcal": "-175",
}


def _passing_desktop_loop() -> dict[str, object]:
    return {
        "page_navigation": {
            "chat": True,
            "today": True,
            "body": True,
            "feedback": True,
            "review": True,
            "data": True,
        },
        "today_same_truth_checked": True,
        "feedback_submitted": True,
        "review_queue_artifact_written": True,
        "review_queue_ingested_feedback": True,
        "data_export_created": True,
        "data_export_sidecars_included": True,
        "feedback_record_count": 1,
        "review_feedback_count": 1,
        "local_debug_token_in_url": False,
        "forbidden_storage_used": False,
        "export_sidecar_evidence": {
            "feedback_jsonl_copied": True,
            "feedback_jsonl_record_count": 1,
            "review_queue_copied": True,
            "review_queue_feedback_triage_record_count": 1,
            "sidecar_evidence_can_create_product_truth": False,
            "sidecar_evidence_can_create_fooddb_truth": False,
            "sidecar_evidence_can_create_eval_truth": False,
        },
        "fetch_sequence": [
            {"url": "/accurate-intake/feedback", "method": "POST"},
            {"url": "/accurate-intake/review-queue", "method": "GET"},
            {"url": "/accurate-intake/local-data-hygiene/export", "method": "POST"},
        ],
    }


def _passing_browser_result() -> dict[str, object]:
    return {
        "browser_name": "chromium",
        "page_url": "http://127.0.0.1:1234/static/accurate-intake-local-shell.html",
        "desktop_entry": {
            "surface_loaded": True,
            "session_connected": True,
            "token_in_url": False,
            "storage_used": False,
            "links": {
                "desktop": "/static/accurate-intake-desktop.html?user_id=dogfood-user-v2-diagnostic",
                "chat": "/static/accurate-intake-chat.html?user_id=dogfood-user-v2-diagnostic",
                "today": "/static/accurate-intake-today.html?user_id=dogfood-user-v2-diagnostic",
                "body": "/static/accurate-intake-body.html?user_id=dogfood-user-v2-diagnostic",
                "feedback": "/static/accurate-intake-feedback.html?user_id=dogfood-user-v2-diagnostic",
                "review": "/static/accurate-intake-review.html?user_id=dogfood-user-v2-diagnostic",
                "data": "/static/accurate-intake-data.html?user_id=dogfood-user-v2-diagnostic",
            },
        },
        "today_summary_rendered": True,
        "meal_threads_rendered": True,
        "correction_history_rendered": True,
        "same_truth_rendered": True,
        "browser_reload_checked": True,
        "reload_state_rehydrated": True,
        "removed_item_rendered": True,
        "remaining_items_rendered": True,
        "fetch_sequence": [
            {"url": "/today/current-budget?user_id=dogfood-user-v2-diagnostic", "method": "GET"},
            {"url": "/body-plan/active?user_id=dogfood-user-v2-diagnostic", "method": "GET"},
            {
                "url": "/accurate-intake/debug?user_id=dogfood-user-v2-diagnostic&local_date=2026-05-03",
                "method": "GET",
            },
            {
                "url": "/accurate-intake/chat-history?user_id=dogfood-user-v2-diagnostic&local_date=2026-05-03",
                "method": "GET",
            },
            {"url": "/accurate-intake/feedback", "method": "POST"},
            {"url": "/accurate-intake/review-queue", "method": "GET"},
            {"url": "/accurate-intake/local-data-hygiene/export", "method": "POST"},
        ],
        "storage": {"localStorageKeys": [], "sessionStorageKeys": []},
        "forbidden_storage_used": False,
        "observed_today_summary": dict(EXPECTED_MANAGER_DOGFOOD_TODAY),
        "desktop_loop": _passing_desktop_loop(),
    }


def _passing_manager_dogfood_report() -> dict[str, object]:
    return {
        "one_day_realistic_web_dogfood": {
            "status": "pass",
            "browser_executed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "turns": [
                {
                    "turn_id": "query_001",
                    "state_after": {
                        "budget_kcal": 1600,
                        "consumed_kcal": 1775,
                        "remaining_kcal": -175,
                        "active_meal_count": 4,
                    },
                }
            ],
            "evidence": {
                "approved_fooddb_evidence_fixture_used": True,
                "fooddb_evidence_used": True,
                "macro_present_evidence_seen": True,
                "macro_missing_evidence_seen": True,
                "same_truth_verified": "manager_runtime_only",
            },
            "blockers": [],
        }
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


def test_browser_one_day_fixture_normalizes_relative_db_path_before_route_export(
    monkeypatch,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_browser_one_day_fixture_dogfood_report(
        db_path=Path("artifacts/relative_one_day.sqlite3"),
    )

    assert Path(report["db_path"]).is_absolute()


def test_browser_one_day_fixture_uses_browser_fixture_status_not_dogfood_pass(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(module, "_load_sync_playwright", lambda: object())
    monkeypatch.setattr(module, "_run_browser_sequence", lambda **_: _passing_browser_result())
    monkeypatch.setattr(module, "build_realistic_manager_dogfood_report", lambda **_: _passing_manager_dogfood_report())

    report = module.build_browser_one_day_fixture_dogfood_report(db_path=tmp_path / "one_day.sqlite3")

    assert report["status"] == "browser_fixture_pass"
    assert report["dogfood_pass"] is False
    assert report["fixture_evidence_used"] is True
    assert report["real_fooddb_pass_claimed"] is False
    assert report["fooddb_evidence_used"] is True
    assert report["scenario_wall_status"] == "pass"
    assert report["manager_dogfood_status"] == "pass"
    assert report["manager_runtime_source"] == "one_day_realistic_web_dogfood"
    assert report["expected_today_summary"] == EXPECTED_MANAGER_DOGFOOD_TODAY
    assert report["browser"]["observed_today_summary"] == EXPECTED_MANAGER_DOGFOOD_TODAY
    assert report["browser"]["desktop_entry"]["surface_loaded"] is True
    assert report["browser"]["desktop_loop"]["data_export_sidecars_included"] is True
    assert Path(report["review_queue_artifact_path"]).parent.name.startswith("data_")
    assert Path(report["feedback_store_path"]).parent.name.startswith("feedback_")


def test_browser_one_day_fixture_validator_requires_render_reload_data_export_and_no_storage() -> None:
    report = module._base_report(db_path=Path("x.sqlite3"), browser_execution_required=True)
    report["browser_executed"] = True
    report["browser"] = {
        **_passing_browser_result(),
        "meal_threads_rendered": False,
        "removed_item_rendered": False,
        "browser_reload_checked": False,
        "forbidden_storage_used": True,
        "storage": {"localStorageKeys": ["bad"], "sessionStorageKeys": []},
        "desktop_loop": {
            **_passing_desktop_loop(),
            "data_export_sidecars_included": False,
            "export_sidecar_evidence": {
                **_passing_desktop_loop()["export_sidecar_evidence"],
                "sidecar_evidence_can_create_eval_truth": True,
            },
        },
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "meal_threads_not_rendered" in blockers
    assert "removed_item_not_rendered" in blockers
    assert "browser_reload_not_checked" in blockers
    assert "forbidden_storage_used" in blockers
    assert "desktop_loop_export_sidecars_not_included" in blockers
    assert (
        "desktop_loop_export_sidecar_policy_violation:sidecar_evidence_can_create_eval_truth"
        in blockers
    )


def test_browser_one_day_fixture_writes_review_queue_artifact_from_feedback(
    tmp_path: Path,
) -> None:
    feedback_dir = tmp_path / "feedback"
    feedback_dir.mkdir()
    feedback_dir.joinpath("accurate_intake_dogfood_feedback.jsonl").write_text(
        json.dumps(
            {
                "artifact_type": "accurate_intake_dogfood_feedback_record",
                "feedback_id": "feedback-one-day",
                "category": "product_feedback",
                "feedback_text": "One-day desktop dogfood loop smoke feedback.",
                "linked_context": {"trace_id": "one-day-dogfood-trace"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = module._write_review_queue_artifact_from_feedback(
        feedback_dir=feedback_dir,
        review_queue_artifact_path=tmp_path / "review_queue.json",
    )

    artifact = json.loads((tmp_path / "review_queue.json").read_text(encoding="utf-8"))
    assert result["feedback_record_count"] == 1
    assert result["review_queue_artifact_written"] is True
    assert artifact["feedback_triage_record_count"] == 1
    assert artifact["desktop_feedback_records"][0]["linked_context"]["trace_id"] == "one-day-dogfood-trace"


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
        "build_realistic_manager_dogfood_report",
        lambda **_: _passing_manager_dogfood_report(),
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
    assert "build_one_day_self_use_scenario_wall_report" not in source
    assert "build_realistic_manager_dogfood_report" in source
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


def test_self_use_runbook_documents_browser_one_day_desktop_loop_closure() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(
        encoding="utf-8-sig"
    )

    assert "run_accurate_intake_browser_one_day_fixture_dogfood.py" in runbook
    assert "Chat, Today, Body, Feedback, Review, and Data" in runbook
    assert "local export sidecars for feedback/review evidence" in runbook
    assert "real FoodDB truth promotion" in runbook
