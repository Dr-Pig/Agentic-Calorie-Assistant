from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_accurate_intake_persistent_desktop_dogfood_baseline as module
from scripts.run_accurate_intake_persistent_desktop_dogfood_baseline import (
    DEFAULT_DB_PATH,
    build_persistent_desktop_dogfood_baseline_report,
    main as persistent_baseline_main,
)


def test_persistent_desktop_dogfood_baseline_survives_restart_and_exports_sidecars(
    tmp_path: Path,
) -> None:
    report = build_persistent_desktop_dogfood_baseline_report(
        db_path=tmp_path / "fixture-dogfood.sqlite3",
        local_date="2026-05-10",
        user_external_id="persistent-dogfood-user",
        local_debug_token="persistent-token",
        reset_db=True,
        feedback_dir=tmp_path / "feedback",
        backup_dir=tmp_path / "backups",
        export_dir=tmp_path / "exports",
        review_queue_artifact_path=tmp_path / "review" / "queue.json",
    )

    assert report["status"] == "pass"
    assert report["persistent_local_sqlite"] is True
    assert report["runtime_truth_changed"] is False
    assert report["fooddb_truth_updated"] is False
    assert report["product_readiness_claimed"] is False
    assert report["private_self_use_approved"] is False
    assert report["approved_packet_turn"]["canonical_commit"] is True
    assert report["approved_packet_turn"]["macro_visibility_status"] == "visible"
    assert report["approved_packet_turn"]["macro_display_status"] == "show"
    assert report["approved_packet_turn"]["protein_g"] == 12
    assert report["approved_packet_turn"]["carbs_g"] == 48
    assert report["approved_packet_turn"]["fat_g"] == 6
    assert report["ambiguous_packet_turn"]["canonical_commit"] is False
    assert report["ambiguous_packet_turn"]["disambiguation_required"] is True
    assert report["ambiguous_packet_turn"]["macro_display_status"] == "hide"
    assert report["ambiguous_packet_turn"]["macro_guard_reason"] == "no_macro_data"
    assert report["ambiguous_packet_turn"]["protein_g"] in (0, None)
    assert report["ambiguous_packet_turn"]["carbs_g"] in (0, None)
    assert report["ambiguous_packet_turn"]["fat_g"] in (0, None)
    assert report["before_restart"]["today"]["consumed_kcal"] == 300
    assert report["before_restart"]["today"]["consumed_protein"] == 12
    assert report["before_restart"]["today"]["consumed_carbs"] == 48
    assert report["before_restart"]["today"]["consumed_fat"] == 6
    assert report["before_restart"]["today"]["show_macro"] is True
    assert report["before_restart"]["today"]["macro_guard_reason"] == "committed_and_aligned"
    assert report["after_restart"]["today"]["consumed_kcal"] == 300
    assert report["after_restart"]["today"]["active_meal_count"] == 1
    assert report["after_restart"]["today"]["consumed_protein"] == 12
    assert report["after_restart"]["today"]["consumed_carbs"] == 48
    assert report["after_restart"]["today"]["consumed_fat"] == 6
    assert report["after_restart"]["today"]["show_macro"] is True
    assert report["after_restart"]["today"]["macro_guard_reason"] == "committed_and_aligned"
    assert isinstance(report["after_restart"]["today"]["budget_kcal"], int)
    assert isinstance(report["after_restart"]["today"]["remaining_kcal"], int)
    assert report["after_restart"]["chat_history"]["message_count"] >= 4
    assert report["after_restart"]["chat_history"]["complete_trace_message_count"] >= 4
    assert report["after_restart"]["debug"]["same_truth_status"] == "pass"
    assert report["feedback"]["record_count"] == 1
    assert report["review_queue"]["feedback_triage_record_count"] == 1
    assert report["export"]["status"] == "pass"
    assert report["export"]["sidecar_evidence_included"] is True
    assert report["export"]["sidecar_evidence_can_create_product_truth"] is False
    assert report["export"]["sidecar_evidence_can_create_fooddb_truth"] is False
    assert report["export"]["sidecar_evidence_can_create_eval_truth"] is False


def test_persistent_desktop_dogfood_baseline_blocks_reset_of_real_default_db() -> None:
    report = build_persistent_desktop_dogfood_baseline_report(
        db_path=DEFAULT_DB_PATH,
        local_date="2026-05-10",
        user_external_id="persistent-dogfood-user",
        local_debug_token="persistent-token",
        reset_db=True,
    )

    assert report["status"] == "blocked"
    assert report["blockers"] == ["backup_required_before_reset"]
    assert report["db_path"] == "workspace_data/local_dogfood/accurate_intake.sqlite3"


def test_persistent_desktop_dogfood_cli_accepts_disposable_sidecar_paths(tmp_path: Path) -> None:
    output_path = tmp_path / "artifact.json"

    exit_code = persistent_baseline_main(
        [
            "--db-path",
            str(tmp_path / "fixture-dogfood.sqlite3"),
            "--local-date",
            "2026-05-10",
            "--user-id",
            "persistent-dogfood-user",
            "--local-debug-token",
            "persistent-token",
            "--reset-db",
            "--feedback-dir",
            str(tmp_path / "feedback"),
            "--backup-dir",
            str(tmp_path / "backups"),
            "--export-dir",
            str(tmp_path / "exports"),
            "--review-queue-artifact-path",
            str(tmp_path / "review" / "queue.json"),
            "--output",
            str(output_path),
        ]
    )

    report = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert '"status": "pass"' in report
    assert '"feedback_triage_record_count": 1' in report


def test_persistent_desktop_dogfood_cli_reports_required_browser_dependency_gap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    output_path = tmp_path / "artifact.json"
    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    exit_code = persistent_baseline_main(
        [
            "--db-path",
            str(tmp_path / "fixture-dogfood.sqlite3"),
            "--local-date",
            "2026-05-10",
            "--user-id",
            "persistent-dogfood-user",
            "--local-debug-token",
            "persistent-token",
            "--reset-db",
            "--require-browser-execution",
            "--feedback-dir",
            str(tmp_path / "feedback"),
            "--backup-dir",
            str(tmp_path / "backups"),
            "--export-dir",
            str(tmp_path / "exports"),
            "--review-queue-artifact-path",
            str(tmp_path / "review" / "queue.json"),
            "--output",
            str(output_path),
        ]
    )

    artifact = output_path.read_text(encoding="utf-8")

    assert exit_code == 1
    assert '"browser_execution_required": true' in artifact
    assert '"browser_executed": false' in artifact
    assert '"playwright_not_installed"' in artifact
    assert '"product_readiness_claimed": false' in artifact


def test_persistent_browser_execution_checks_arbitrary_next_day_is_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_browser_sequence(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "browser_name": "chromium",
            "desktop_entry": {
                "surface_loaded": True,
                "session_connected": True,
                "token_in_url": False,
                "storage_used": False,
            },
            "desktop_loop": {
                "page_navigation": {
                    "chat": True,
                    "today": True,
                    "body": True,
                    "feedback": True,
                    "review": True,
                    "data": True,
                },
                "today_same_truth_checked": True,
                "today_macro_panel_checked": True,
                "today_macro_panel": {
                    "checked": True,
                    "macro_state": "visible",
                    "protein_text": "12",
                    "carbs_text": "48",
                    "fat_text": "6",
                    "macro_guard_reason_hidden": True,
                },
                "feedback_submitted": True,
                "review_queue_ingested_feedback": True,
                "data_export_sidecars_included": True,
                "local_debug_token_in_url": False,
                "forbidden_storage_used": False,
            },
            "adjacent_date": {
                "local_date": "2026-05-11",
                "today_consumed_kcal": 0,
                "chat_history_message_count": 0,
            },
            "forbidden_storage_used": False,
        }

    monkeypatch.setattr(module, "_run_persistent_browser_sequence", fake_browser_sequence)
    report = persistent_baseline_main(
        [
            "--db-path",
            str(tmp_path / "fixture-dogfood.sqlite3"),
            "--local-date",
            "2026-05-10",
            "--user-id",
            "persistent-dogfood-user",
            "--local-debug-token",
            "persistent-token",
            "--reset-db",
            "--require-browser-execution",
            "--feedback-dir",
            str(tmp_path / "feedback"),
            "--backup-dir",
            str(tmp_path / "backups"),
            "--export-dir",
            str(tmp_path / "exports"),
            "--review-queue-artifact-path",
            str(tmp_path / "review" / "queue.json"),
            "--output",
            str(tmp_path / "artifact.json"),
        ]
    )

    assert report == 0
    assert captured["local_date"] == "2026-05-10"


def test_persistent_browser_execution_requires_adjacent_date_isolation() -> None:
    blockers = module._browser_blockers(
        {
            "desktop_entry": {
                "surface_loaded": True,
                "session_connected": True,
                "token_in_url": False,
            },
            "desktop_loop": {
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
                "review_queue_ingested_feedback": True,
                "data_export_sidecars_included": True,
                "local_debug_token_in_url": False,
                "forbidden_storage_used": False,
            },
            "forbidden_storage_used": False,
        }
    )

    assert "adjacent_date_not_checked" in blockers


def test_persistent_browser_execution_requires_macro_visible_today_panel() -> None:
    blockers = module._browser_blockers(
        {
            "desktop_entry": {
                "surface_loaded": True,
                "session_connected": True,
                "token_in_url": False,
            },
            "desktop_loop": {
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
                "review_queue_ingested_feedback": True,
                "data_export_sidecars_included": True,
                "local_debug_token_in_url": False,
                "forbidden_storage_used": False,
                "today_macro_panel_checked": False,
            },
            "adjacent_date": {
                "local_date": "2026-05-11",
                "today_consumed_kcal": 0,
                "chat_history_message_count": 0,
            },
            "forbidden_storage_used": False,
        }
    )

    assert "today_macro_panel_not_checked" in blockers


def test_self_use_runbook_documents_persistent_desktop_baseline() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(
        encoding="utf-8-sig"
    )

    assert "run_accurate_intake_persistent_desktop_dogfood_baseline.py" in runbook
    assert "macro-present approved exact FoodDB packet commit plus ambiguous no-commit" in runbook
    assert "Add `--require-browser-execution`" in runbook
    assert "Today macro panel" in runbook
    assert "adjacent-date isolation" in runbook
    assert "backup_required_before_reset" in runbook
