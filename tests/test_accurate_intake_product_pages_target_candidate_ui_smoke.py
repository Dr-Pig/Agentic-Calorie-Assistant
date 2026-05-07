from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_accurate_intake_product_pages_target_candidate_ui_smoke as module


def _passing_report() -> dict[str, object]:
    return {
        "smoke_id": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "browser_reload_checked": True,
        "chat_page_loaded": True,
        "chat_history_reloaded": True,
        "target_candidate_surface_checked": True,
        "target_candidate_count_rendered": 2,
        "target_candidate_names_rendered": ["luwei", "milk tea"],
        "target_candidate_list_read_only": True,
        "context_strip_read_only": True,
        "product_pages_no_debug_trace": True,
        "manager_provider_call_count": 0,
        "browser": {
            "fetch_sequence": [
                {
                    "url": (
                        "/accurate-intake/chat-history"
                        "?user_id=product-pages-target-candidate-ui-user&local_date=2026-05-05"
                    ),
                    "method": "GET",
                }
            ],
            "storage": {"localStorageKeys": [], "sessionStorageKeys": []},
        },
    }


def test_target_candidate_ui_smoke_missing_playwright_is_blocked_not_readiness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_target_candidate_ui_smoke_report(
        db_path=tmp_path / "target-candidate-ui.sqlite3",
    )

    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["browser_execution_required"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_target_candidate_ui_smoke_can_require_browser_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_target_candidate_ui_smoke_report(
        db_path=tmp_path / "target-candidate-ui.sqlite3",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["browser_execution_required"] is True
    assert report["browser_executed"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_target_candidate_ui_validator_accepts_read_only_browser_evidence() -> None:
    status, blockers = module._validate(_passing_report())

    assert status == "pass"
    assert blockers == []


def test_target_candidate_ui_validator_requires_reload_and_target_names() -> None:
    report = _passing_report()
    report["browser_reload_checked"] = False
    report["chat_history_reloaded"] = False
    report["target_candidate_surface_checked"] = False
    report["target_candidate_count_rendered"] = 1
    report["target_candidate_names_rendered"] = ["luwei"]

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "browser_reload_not_checked" in blockers
    assert "chat_history_not_reloaded" in blockers
    assert "target_candidate_surface_not_checked" in blockers
    assert "target_candidate_count_rendered_mismatch" in blockers
    assert "target_candidate_names_rendered_mismatch" in blockers


def test_target_candidate_ui_validator_rejects_unexpected_manager_provider_calls() -> None:
    report = _passing_report()
    report["manager_provider_call_count"] = 1

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "manager_provider_called" in blockers


def test_target_candidate_ui_validator_rejects_storage_estimate_fetch_or_debug_leak() -> None:
    report = _passing_report()
    report["target_candidate_list_read_only"] = False
    report["context_strip_read_only"] = False
    report["product_pages_no_debug_trace"] = False
    report["browser"]["fetch_sequence"] = [  # type: ignore[index]
        {"url": "/estimate", "method": "POST"},
    ]
    report["browser"]["storage"] = {  # type: ignore[index]
        "localStorageKeys": ["debug-token"],
        "sessionStorageKeys": [],
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "target_candidate_list_not_read_only" in blockers
    assert "context_strip_not_read_only" in blockers
    assert "product_pages_debug_trace_leaked" in blockers
    assert "forbidden_storage_used" in blockers
    assert "required_fetch_missing:/accurate-intake/chat-history" in blockers
    assert "estimate_endpoint_called" in blockers


def test_target_candidate_ui_source_stays_out_of_forbidden_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_product_pages_target_candidate_ui_smoke.py").read_text(
        encoding="utf-8"
    )

    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "FoodDB",
        "Tavily",
        "Kimi",
        "GrokFast",
        "selected_target_id",
        "ManagerContextPacket",
    ]
    for fragment in forbidden:
        assert fragment not in source
