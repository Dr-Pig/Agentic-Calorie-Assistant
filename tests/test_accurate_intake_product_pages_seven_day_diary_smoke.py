from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_accurate_intake_product_pages_seven_day_diary_smoke as module


def _passing_report() -> dict[str, object]:
    return {
        "browser_executed": True,
        "seven_day_window_checked": True,
        "day_count_checked": 7,
        "per_day_diary_isolated": True,
        "per_day_budget_values_checked": True,
        "today_date_strip_checked": True,
        "today_nav_date_preserved": True,
        "today_chat_link_date_preserved": True,
        "desktop_no_overflow": True,
        "mobile_no_overflow": True,
        "forbidden_storage_used": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "manager_provider_call_count": 0,
        "checked_days": [
            {
                "local_date": f"2026-05-0{day}",
                "expected_meal_title": f"fixture day {day}",
                "expected_consumed_kcal": 300 + day,
                "expected_remaining_kcal": 1500 - (300 + day),
                "observed_consumed_kcal": 300 + day,
                "observed_remaining_kcal": 1500 - (300 + day),
                "other_day_meal_leaked": False,
            }
            for day in range(1, 8)
        ],
        "fetch_sequence": [
            {"url": f"/today/current-budget?user_id=seven-day&local_date=2026-05-0{day}", "method": "GET"}
            for day in range(1, 8)
        ],
    }


def test_seven_day_diary_smoke_missing_playwright_is_blocked_not_readiness(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_seven_day_diary_smoke_report(db_path=tmp_path / "seven-day.sqlite3")

    assert report["smoke_id"] == "accurate_intake_product_pages_seven_day_diary_smoke_v1"
    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["browser_execution_required"] is False
    assert report["blockers"] == ["playwright_not_installed"]
    assert report["web_readiness_claimed"] is False
    assert report["product_readiness_claimed"] is False
    assert report["private_self_use_approved"] is False
    assert report["live_llm_invoked"] is False
    assert report["web_tavily_used"] is False


def test_seven_day_diary_smoke_can_require_browser_execution(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_seven_day_diary_smoke_report(
        db_path=tmp_path / "seven-day.sqlite3",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["browser_execution_required"] is True
    assert report["browser_executed"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_seven_day_diary_smoke_validator_requires_full_window_evidence() -> None:
    status, blockers = module._validate(_passing_report())

    assert status == "pass"
    assert blockers == []


def test_seven_day_diary_smoke_validator_rejects_shallow_or_cross_day_evidence() -> None:
    report = _passing_report()
    report["day_count_checked"] = 6
    report["per_day_diary_isolated"] = False
    report["per_day_budget_values_checked"] = False
    report["today_date_strip_checked"] = False
    report["today_nav_date_preserved"] = False
    report["today_chat_link_date_preserved"] = False
    report["checked_days"] = list(report["checked_days"])[:6]

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "seven_day_window_incomplete" in blockers
    assert "per_day_diary_not_isolated" in blockers
    assert "per_day_budget_values_not_checked" in blockers
    assert "today_date_strip_not_checked" in blockers
    assert "today_nav_date_not_preserved" in blockers
    assert "today_chat_link_date_not_preserved" in blockers


def test_seven_day_diary_smoke_validator_rejects_readiness_or_live_claims() -> None:
    report = _passing_report()
    report["frontend_semantic_owner"] = True
    report["live_llm_invoked"] = True
    report["web_tavily_used"] = True
    report["production_db_used"] = True
    report["product_readiness_claimed"] = True
    report["private_self_use_approved"] = True

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "frontend_semantic_owner" in blockers
    assert "live_llm_invoked" in blockers
    assert "web_tavily_used" in blockers
    assert "production_db_used" in blockers
    assert "product_readiness_claimed" in blockers
    assert "private_self_use_approved" in blockers


def test_seven_day_diary_smoke_validator_rejects_manager_or_estimate_runtime_use() -> None:
    report = _passing_report()
    report["manager_provider_call_count"] = 1
    report["fetch_sequence"] = [
        *list(report["fetch_sequence"]),
        {"url": "/estimate", "method": "POST", "body": '{"allow_search":false}'},
    ]

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "manager_provider_called" in blockers
    assert "estimate_fetch_unexpected" in blockers


def test_seven_day_diary_smoke_runs_real_browser_when_playwright_available(tmp_path: Path) -> None:
    try:
        module._load_sync_playwright()
    except module.BrowserSmokeDependencyMissing:
        pytest.skip("Playwright is not installed in this environment.")

    report = module.build_seven_day_diary_smoke_report(
        db_path=tmp_path / "seven-day-browser.sqlite3",
        require_browser_execution=True,
        timeout_ms=20000,
    )

    assert report["status"] == "pass"
    assert report["browser_executed"] is True
    assert report["seven_day_window_checked"] is True
    assert report["day_count_checked"] == 7
    assert report["per_day_diary_isolated"] is True
    assert report["per_day_budget_values_checked"] is True
    assert report["today_nav_date_preserved"] is True
    assert report["today_chat_link_date_preserved"] is True
    assert report["product_readiness_claimed"] is False


def test_ci_keeps_seven_day_diary_browser_smoke_out_of_required_merge_path() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "product-pages-browser-e2e" in workflow
    assert "run_accurate_intake_product_pages_seven_day_diary_smoke.py --require-browser-execution" not in workflow
    assert "accurate_intake_product_pages_seven_day_diary_smoke_ci.json" not in workflow


def test_seven_day_diary_smoke_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_product_pages_seven_day_diary_smoke.py").read_text(encoding="utf-8")

    forbidden = [
        "app.providers",
        "tavily_adapter",
        "Tavily",
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "fooddb_evidence_used = True",
        "live_llm_invoked = True",
        "web_tavily_used = True",
    ]
    for fragment in forbidden:
        assert fragment not in source
