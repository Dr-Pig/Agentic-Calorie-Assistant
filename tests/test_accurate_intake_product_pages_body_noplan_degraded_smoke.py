from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_accurate_intake_product_pages_body_noplan_degraded_smoke as module


def _passing_report() -> dict[str, object]:
    return {
        "smoke_id": "accurate_intake_product_pages_body_noplan_degraded_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "body_page_loaded": True,
        "today_page_loaded": True,
        "no_plan_body_status_rendered": True,
        "body_targets_hidden_for_no_plan": True,
        "body_budget_degraded_rendered": True,
        "today_no_plan_budget_rendered": True,
        "no_bootstrap_or_mutation_post": True,
        "product_pages_no_debug_trace": True,
        "body_values": {
            "status": "Set up your body plan to see targets.",
            "daily_target": "--",
            "tdee": "--",
            "active_target": "--",
            "remaining": "--",
        },
        "today_values": {
            "budget": "0",
            "consumed": "0",
            "remaining": "0",
        },
        "browser": {
            "fetch_sequence": [
                {"url": "/body-plan/active?user_id=no-plan", "method": "GET"},
                {"url": "/today/deficit-summary?user_id=no-plan", "method": "GET"},
                {"url": "/today/effective-budget?user_id=no-plan", "method": "GET"},
                {"url": "/today/weekly-progress?user_id=no-plan", "method": "GET"},
                {"url": "/today/current-budget?user_id=no-plan", "method": "GET"},
            ],
        },
    }


def test_body_noplan_degraded_smoke_missing_playwright_is_blocked_not_readiness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_body_noplan_degraded_smoke_report(
        db_path=tmp_path / "body-noplan.sqlite3"
    )

    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["browser_execution_required"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_body_noplan_degraded_smoke_can_require_browser_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_body_noplan_degraded_smoke_report(
        db_path=tmp_path / "body-noplan.sqlite3",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["browser_execution_required"] is True
    assert report["browser_executed"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_body_noplan_degraded_validator_accepts_degraded_browser_truth() -> None:
    status, blockers = module._validate(_passing_report())

    assert status == "pass"
    assert blockers == []


def test_body_noplan_degraded_validator_rejects_fake_target_or_mutation() -> None:
    report = _passing_report()
    report["body_targets_hidden_for_no_plan"] = False
    report["body_values"]["daily_target"] = "1550 kcal"  # type: ignore[index]
    report["browser"]["fetch_sequence"].append(  # type: ignore[index]
        {"url": "/onboarding/bootstrap", "method": "POST"}
    )

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "body_targets_not_hidden_for_no_plan" in blockers
    assert "body_no_plan_daily_target_not_hidden" in blockers
    assert "unexpected_no_plan_mutation_post:/onboarding/bootstrap" in blockers


def test_body_noplan_degraded_validator_requires_body_budget_and_today_fetches() -> None:
    report = _passing_report()
    report["browser"]["fetch_sequence"] = []  # type: ignore[index]

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "required_fetch_missing:/body-plan/active" in blockers
    assert "required_fetch_missing:/today/deficit-summary" in blockers
    assert "required_fetch_missing:/today/effective-budget" in blockers
    assert "required_fetch_missing:/today/weekly-progress" in blockers
    assert "required_fetch_missing:/today/current-budget" in blockers


def test_body_noplan_degraded_smoke_source_stays_out_of_fooddb_live_and_semantic_owners() -> None:
    source = Path("scripts/run_accurate_intake_product_pages_body_noplan_degraded_smoke.py").read_text(
        encoding="utf-8"
    )

    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "BuilderSpaceAdapter",
        "live_llm_invoked = True",
        "frontend_calculates_tdee = True",
    ]
    for fragment in forbidden:
        assert fragment not in source


def test_ci_runs_body_noplan_degraded_browser_smoke() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "run_accurate_intake_product_pages_body_noplan_degraded_smoke.py" in workflow
    assert "accurate_intake_product_pages_body_noplan_degraded_smoke_ci.json" in workflow
