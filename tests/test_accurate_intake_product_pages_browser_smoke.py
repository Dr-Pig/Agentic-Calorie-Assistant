from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_accurate_intake_product_pages_browser_smoke as module


def _passing_report(*, local_date: str = "2026-05-05") -> dict[str, object]:
    previous_local_date = module._previous_local_date(local_date)
    return {
        "browser_executed": True,
        "local_date": local_date,
        "previous_local_date": previous_local_date,
        "chat_page_loaded": True,
        "chat_sent_cjk_message": True,
        "chat_assistant_bubble_rendered": True,
        "chat_history_reloaded": True,
        "chat_url_state_preserved_after_date_change": True,
        "chat_reload_preserved_selected_date": True,
        "chat_user_url_state_preserved_after_user_change": True,
        "chat_reload_preserved_user_id": True,
        "chat_enter_key_send_checked": True,
        "chat_shift_enter_multiline_checked": True,
        "chat_scrollable": True,
        "chat_scroll_behavior_checked": True,
        "chat_reload_scroll_behavior_checked": True,
        "chat_no_debug_trace": True,
        "today_page_loaded": True,
        "today_date_switch_checked": True,
        "today_previous_day_empty_checked": True,
        "today_current_day_restored_checked": True,
        "today_url_state_preserved_after_date_change": True,
        "today_reload_preserved_selected_date": True,
        "today_user_url_state_preserved_after_user_change": True,
        "today_reload_preserved_user_id": True,
        "today_summary_rendered": True,
        "today_meal_list_rendered": True,
        "today_no_debug_trace": True,
        "body_page_loaded": True,
        "body_query_user_id_honored": True,
        "body_url_state_preserved_after_date_change": True,
        "body_reload_preserved_selected_date": True,
        "body_user_url_state_preserved_after_user_change": True,
        "body_reload_preserved_user_id": True,
        "body_active_plan_rendered": True,
        "body_weight_checkin_saved": True,
        "body_plan_form_saved": True,
        "body_manual_target_saved": True,
        "body_plan_readback_checked": True,
        "today_manual_target_readback_checked": True,
        "body_no_debug_trace": True,
        "desktop_no_overflow": True,
        "mobile_no_overflow": True,
        "mobile_populated_state_checked": True,
        "mobile_no_debug_trace": True,
        "product_cjk_copy_rendered": True,
        "nav_session_query_preserved": True,
        "forbidden_storage_used": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "browser": {
            "fetch_sequence": [
                {"url": "/accurate-intake/chat-history?user_id=product-pages", "method": "GET"},
                {"url": "/estimate", "method": "POST", "body": '{"allow_search":false}'},
                {"url": "/today/current-budget?user_id=product-pages", "method": "GET"},
                {
                    "url": f"/today/current-budget?user_id=product-pages&local_date={previous_local_date}",
                    "method": "GET",
                },
                {"url": f"/today/current-budget?user_id=product-pages&local_date={local_date}", "method": "GET"},
                {"url": "/body-plan/active?user_id=product-pages", "method": "GET"},
                {"url": "/weight/observations?user_id=product-pages", "method": "GET"},
                {
                    "url": "/weight/observation",
                    "method": "POST",
                    "body": f'{{"user_id":"product-pages","local_date":"{local_date}"}}',
                },
                {
                    "url": "/onboarding/bootstrap",
                    "method": "POST",
                    "body": f'{{"user_id":"product-pages","local_date":"{local_date}"}}',
                },
                {
                    "url": "/body-plan/manual-daily-target",
                    "method": "POST",
                    "body": f'{{"user_id":"product-pages","local_date":"{local_date}","source":"user_ui"}}',
                },
            ],
            "storage": {"localStorageKeys": [], "sessionStorageKeys": []},
            "product_page_text": "Chat Today Body",
        },
    }


def test_product_pages_browser_smoke_missing_playwright_is_blocked_not_readiness(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_browser_smoke_report(db_path=tmp_path / "product-pages.sqlite3")

    assert report["smoke_id"] == "accurate_intake_product_pages_browser_smoke_v1"
    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["browser_execution_required"] is False
    assert report["blockers"] == ["playwright_not_installed"]
    assert report["web_readiness_claimed"] is False
    assert report["product_readiness_claimed"] is False
    assert report["private_self_use_approved"] is False
    assert report["live_llm_invoked"] is False
    assert report["web_tavily_used"] is False


def test_product_pages_browser_smoke_can_require_browser_execution(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_browser_smoke_report(
        db_path=tmp_path / "product-pages.sqlite3",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["browser_execution_required"] is True
    assert report["browser_executed"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_product_pages_browser_smoke_validator_requires_cross_page_evidence() -> None:
    status, blockers = module._validate(_passing_report(local_date="2026-05-05"))

    assert status == "pass"
    assert blockers == []


def test_product_pages_browser_smoke_validator_rejects_missing_reload_body_user_and_overflow() -> None:
    report = _passing_report()
    report["chat_history_reloaded"] = False
    report["chat_url_state_preserved_after_date_change"] = False
    report["chat_reload_preserved_selected_date"] = False
    report["chat_user_url_state_preserved_after_user_change"] = False
    report["chat_reload_preserved_user_id"] = False
    report["chat_enter_key_send_checked"] = False
    report["chat_shift_enter_multiline_checked"] = False
    report["chat_scroll_behavior_checked"] = False
    report["body_query_user_id_honored"] = False
    report["body_url_state_preserved_after_date_change"] = False
    report["body_reload_preserved_selected_date"] = False
    report["body_user_url_state_preserved_after_user_change"] = False
    report["body_reload_preserved_user_id"] = False
    report["mobile_no_overflow"] = False
    report["mobile_populated_state_checked"] = False
    report["nav_session_query_preserved"] = False

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "chat_history_not_reloaded" in blockers
    assert "chat_url_state_not_preserved_after_date_change" in blockers
    assert "chat_reload_did_not_preserve_selected_date" in blockers
    assert "chat_user_url_state_not_preserved_after_user_change" in blockers
    assert "chat_reload_did_not_preserve_user_id" in blockers
    assert "chat_enter_key_send_not_checked" in blockers
    assert "chat_shift_enter_multiline_not_checked" in blockers
    assert "chat_scroll_behavior_not_checked" in blockers
    assert "body_query_user_id_not_honored" in blockers
    assert "body_url_state_not_preserved_after_date_change" in blockers
    assert "body_reload_did_not_preserve_selected_date" in blockers
    assert "body_user_url_state_not_preserved_after_user_change" in blockers
    assert "body_reload_did_not_preserve_user_id" in blockers
    assert "mobile_overflow_detected" in blockers
    assert "mobile_populated_state_not_checked" in blockers
    assert "nav_session_query_not_preserved" in blockers


def test_product_pages_browser_smoke_validator_rejects_shallow_today_and_body_sync() -> None:
    report = _passing_report()
    report["today_previous_day_empty_checked"] = False
    report["today_current_day_restored_checked"] = False
    report["today_url_state_preserved_after_date_change"] = False
    report["today_reload_preserved_selected_date"] = False
    report["today_user_url_state_preserved_after_user_change"] = False
    report["today_reload_preserved_user_id"] = False
    report["body_plan_readback_checked"] = False
    report["today_manual_target_readback_checked"] = False

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "today_previous_day_empty_not_checked" in blockers
    assert "today_current_day_restored_not_checked" in blockers
    assert "today_url_state_not_preserved_after_date_change" in blockers
    assert "today_reload_did_not_preserve_selected_date" in blockers
    assert "today_user_url_state_not_preserved_after_user_change" in blockers
    assert "today_reload_did_not_preserve_user_id" in blockers
    assert "body_plan_readback_not_checked" in blockers
    assert "today_manual_target_readback_not_checked" in blockers


def test_product_pages_browser_smoke_validator_rejects_debug_trace_or_frontend_truth() -> None:
    report = _passing_report()
    report["today_no_debug_trace"] = False
    report["body_no_debug_trace"] = False
    report["frontend_semantic_owner"] = True
    report["product_cjk_copy_rendered"] = False
    report["browser"]["fetch_sequence"][1]["body"] = '{"allow_search":true}'
    previous_local_date = str(report["previous_local_date"])
    report["browser"]["fetch_sequence"] = [
        item for item in report["browser"]["fetch_sequence"] if previous_local_date not in str(item.get("url"))
    ]

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "today_debug_trace_leaked" in blockers
    assert "body_debug_trace_leaked" in blockers
    assert "frontend_semantic_owner" in blockers
    assert "product_cjk_copy_not_rendered" in blockers
    assert "estimate_allow_search_not_false" in blockers
    assert "today_previous_day_fetch_missing" in blockers


def test_body_page_honors_query_user_id_for_session_context() -> None:
    html = Path("static/accurate-intake-body.html").read_text(encoding="utf-8")

    assert 'params.get("user_id") || el("user-id").value' in html


def test_product_pages_browser_smoke_runs_real_browser_when_playwright_available(tmp_path: Path) -> None:
    try:
        module._load_sync_playwright()
    except module.BrowserSmokeDependencyMissing:
        pytest.skip("Playwright is not installed in this environment.")

    report = module.build_product_pages_browser_smoke_report(
        db_path=tmp_path / "product-pages-browser.sqlite3",
        require_browser_execution=True,
        timeout_ms=20000,
    )

    assert report["status"] == "pass"
    assert report["browser_executed"] is True
    assert report["chat_enter_key_send_checked"] is True
    assert report["chat_shift_enter_multiline_checked"] is True
    assert report["chat_url_state_preserved_after_date_change"] is True
    assert report["chat_reload_preserved_selected_date"] is True
    assert report["chat_user_url_state_preserved_after_user_change"] is True
    assert report["chat_reload_preserved_user_id"] is True
    assert report["chat_scroll_behavior_checked"] is True
    assert report["chat_reload_scroll_behavior_checked"] is True
    assert report["today_previous_day_empty_checked"] is True
    assert report["today_current_day_restored_checked"] is True
    assert report["today_url_state_preserved_after_date_change"] is True
    assert report["today_reload_preserved_selected_date"] is True
    assert report["today_user_url_state_preserved_after_user_change"] is True
    assert report["today_reload_preserved_user_id"] is True
    assert report["body_plan_readback_checked"] is True
    assert report["body_url_state_preserved_after_date_change"] is True
    assert report["body_reload_preserved_selected_date"] is True
    assert report["body_user_url_state_preserved_after_user_change"] is True
    assert report["body_reload_preserved_user_id"] is True
    assert report["today_manual_target_readback_checked"] is True
    assert report["nav_session_query_preserved"] is True


def test_ci_requires_product_pages_browser_execution() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "product-pages-browser-e2e" in workflow
    assert "python -m playwright install --with-deps chromium" in workflow
    assert "run_accurate_intake_product_pages_browser_smoke.py --require-browser-execution" in workflow
    assert "accurate_intake_product_pages_browser_smoke_ci.json" in workflow


def test_product_pages_browser_smoke_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_product_pages_browser_smoke.py").read_text(encoding="utf-8")

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
